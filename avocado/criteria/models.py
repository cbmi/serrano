from django import forms
from django.db import models

from avocado.concepts.models import Concept, ConceptField
from avocado.fields.models import Field
from avocado.criteria.viewset import library
from avocado.criteria.managers import CriterionManager

__all__ = ('Criterion', 'CriterionField')

class Criterion(Concept):
    fields = models.ManyToManyField(Field, through='CriterionField')
    viewset = models.CharField(max_length=100, choices=library.choices())

    objects = CriterionManager()

    class Meta(Concept.Meta):
        verbose_name_plural = 'criteria'

    def _get_form(self):
        if not hasattr(self, '_form'):
            from avocado.criteria.cache import cache
            form_fields = {}
            fields = cache.get_fields(self.id)

            for f in fields:
                form_fields[f.field_name] = f.formfield()

            class CriterionForm(forms.Form):
                def __init__(self, *args, **kwargs):
                    super(CriterionForm, self).__init__(*args, **kwargs)
                    self.fields.update(form_fields)

            self._form = CriterionForm
        return self._form
    form = property(_get_form)

    def view_responses(self):
        resps = library.get(self.viewset, self)
        return resps


class CriterionField(ConceptField):
    concept = models.ForeignKey(Criterion, related_name='conceptfields')
    field = models.ForeignKey(Field, limit_choices_to={'is_public': True})
    required = models.BooleanField(default=True)

    class Meta(ConceptField.Meta):
        pass

    def get_name(self):
        return self.name or self.field.name
