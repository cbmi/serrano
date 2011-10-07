from datetime import datetime
from django.utils.timesince import timesince
from django.core.urlresolvers import reverse
from avocado.store.forms import ReportForm, SessionReportForm
from restlib import http, resources
from serrano.http import ExcelResponse

__all__ = ('ReportResource', 'SessionReportResource', 'ReportResourceCollection')

class ReportResource(resources.ModelResource):
    model = 'avocado.Report'

    fields = (':pk', 'name', 'description', 'modified', 'timesince',
        'has_changed', 'unique_count')

    default_for_related = False

    middleware = (
        'serrano.api.middleware.NeverCache',
    ) + resources.Resource.middleware

    @classmethod
    def unique_count(self, obj):
        return obj.scope.count

    @classmethod
    def timesince(self, obj):
        if obj.modified:
            return '%s ago' % timesince(obj.modified)

    @classmethod
    def queryset(self, request):
        return self.model._default_manager.filter(user=request.user,
            session=False).order_by('-modified')

    def _export_csv(self, request, inst):
        context = {'user': request.user}

        # fetch the report cache from the session, default to a new dict with
        # a few defaults. if a new dict is used, this implies that this a
        # report has not been resolved yet this session.
        cache = request.session.get(inst.REPORT_CACHE_KEY, {
            'timestamp': None,
            'page_num': 1,
            'per_page': 10,
            'offset': 0,
            'unique': None,
            'count': None,
            'datakey': inst.get_datakey(request)
        })

        # test if the cache is still valid, then attempt to fetch the requested
        # page from cache
        timestamp = cache['timestamp']
        queryset, unique, count = inst.get_queryset(timestamp, **context)

        rows = inst._execute_raw_query(queryset)
        iterator = inst.perspective.format(rows, 'csv')
        header = inst.perspective.get_columns_as_fields()
        name = 'report-' + datetime.now().strftime('%Y-%m-%d-%H,%M,%S')

        return ExcelResponse(list(iterator), name, header)

    def _GET(self, request, inst):
        "The interface for resolving a report, i.e. running a query."
        user = request.user

        if not inst.has_permission(user):
            return http.FORBIDDEN

        format_type = request.GET.get('f', None)

        # XXX: hack
        if format_type == 'csv':
            return self._export_csv(request, inst)

        page_num = request.GET.get('p', None)
        per_page = request.GET.get('n', None)

        count = unique = None

        # define the default context for use by ``get_queryset``
        # TODO can this be defined elsewhere? only scope depends on this, but
        # the user object has to propagate down from the view
        context = {'user': user}

        # fetch the report cache from the session, default to a new dict with
        # a few defaults. if a new dict is used, this implies that this a
        # report has not been resolved yet this session.
        cache = request.session.get(inst.REPORT_CACHE_KEY, {
            'timestamp': None,
            'page_num': 1,
            'per_page': 10,
            'offset': 0,
            'unique': None,
            'count': None,
            'datakey': inst.get_datakey(request)
        })

        # acts as reference to compare to so the resp can be determined
        old_cache = cache.copy()


        # test if the cache is still valid, then attempt to fetch the requested
        # page from cache
        timestamp = cache['timestamp']

        if inst.cache_is_valid(timestamp):
            # only update the cache if there are values specified for either arg
            if page_num:
                cache['page_num'] = int(page_num)
            if per_page:
                cache['per_page'] = int(per_page)

            rows = inst.get_page_from_cache(cache)

            # ``rows`` will only be None if no cache was found. attempt to
            # update the cache by running a partial query
            if rows is None:
                # since the cache is not invalid, the counts do not have to be run
                queryset, unique, count = inst.get_queryset(timestamp, **context)
                cache['timestamp'] = datetime.now()

                rows = inst.update_cache(cache, queryset);

        # when the cache becomes invalid, the cache must be refreshed
        else:
            queryset, unique, count = inst.get_queryset(timestamp, **context)

            cache.update({
                'timestamp': datetime.now(),
                'page_num': 1,
                'offset': 0,
            })

            if count is not None:
                cache['count'] = count
                if unique is not None:
                    cache['unique'] = unique

            rows = inst.refresh_cache(cache, queryset)


        request.session[inst.REPORT_CACHE_KEY] = cache

        # the response is composed of a few different data that is dependent on
        # various conditions. the only required data is the ``rows`` which will
        # always be needed since all other components act on determing the rows
        # to be returned
        resp = {
            'rows': list(inst.perspective.format(rows, 'html')),
        }

        if inst.name:
            resp['name'] = inst.name

        if inst.description:
            resp['description'] = inst.description

        # a *no change* requests implies the page has been requested statically
        # and the whole response object must be provided
        resp.update({
            'per_page': cache['per_page'],
            'count': cache['count'],
            'unique': cache['unique'],
        })

        paginator, page = inst.paginator_and_page(cache)

        if paginator.num_pages > 1:
            resp.update({
                'pages': {
                    'page': page.number,
                    'pages': page.page_links(),
                    'num_pages': paginator.num_pages,
                }
            })

        return resp

    def DELETE(self, request, pk):
        instance = request.session['report']

        # ensure to deference the session
        if instance.references(pk):
            instance.deference(delete=True)
        else:
            reference = self.queryset(request).filter(pk=pk)
            reference.delete()

        return http.NO_CONTENT

    def GET(self, request, pk):
        instance = request.session['report']
        # if this object is already referenced by the session, simple return
        if not instance.references(pk):
            # attempt to fetch the requested object
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

            reference.reset(instance)
        else:
            reference = instance.reference

        # XXX: hackity hack..
        if request.GET.has_key('data'):
            return self._GET(request, reference)

        return reference

    def PUT(self, request, pk):
        "Explicitly updates an existing object given the request data."
        instance = request.session['report']

        if instance.references(pk):
            referenced = True
            reference = instance.reference
        else:
            referenced = False
            reference = self.get(request, pk=pk)
            if not reference:
                return http.NOT_FOUND

        form = ReportForm(request.data, instance=reference)

        if form.is_valid():
            form.save()
            # if this is referenced by the session, update the session
            # instance to reflect this change. this only needs to be a
            # shallow reset since a PUT only updates local attributes
            if referenced:
                reference.reset(instance)
            return reference

        return form.errors


class SessionReportResource(ReportResource):
    "Handles making requests to and from the session's report object."

    fields = (':pk', 'name', 'description', 'modified', 'timesince',
        'has_changed', 'unique_count', 'scope', 'perspective')

    def GET(self, request):
        instance = request.session['report']
        if request.GET.has_key('data'):
            return self._GET(request, instance)
        return instance

    def PUT(self, request):
        instance = request.session['report']
        form = SessionReportForm(request.data, instance=instance)

        if form.is_valid():
            form.save()
            return instance
        return form.errors


class SimpleReportResource(ReportResource):
    default_for_related = True


class ReportResourceCollection(resources.ModelResourceCollection):
    resource = SimpleReportResource

    def GET(self, request):
        return self.queryset(request)

