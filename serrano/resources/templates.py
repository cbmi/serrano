Category = {
    'fields': [':pk', 'name', 'order', 'parent_id'],
    'allow_missing': True,
}

BriefField = {
    'fields': [':pk', 'name', 'description'],
    'allow_missing': True,
}

Field = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'app_name', 'model_name', 'field_name',
        'modified', 'published', 'archived', 'operators',
        'simple_type', 'internal_type', 'data_modified', 'enumerable',
        'searchable', 'unit', 'plural_unit', 'nullable'
    ],
    'aliases': {
        'plural_name': 'get_plural_name',
        'plural_unit': 'get_plural_unit',
    },
    'allow_missing': True,
}

BriefConcept = {
    'fields': [':pk', 'name', 'description'],
    'allow_missing': True,
}

Concept = {
    'fields': [
        ':pk', 'name', 'plural_name', 'description', 'keywords',
        'category_id', 'order', 'modified', 'published', 'archived',
        'formatter_name', 'queryview', 'sortable'
    ],
    'aliases': {
        'plural_name': 'get_plural_name',
    },
    'allow_missing': True,
}

ConceptField = {
    'fields': ['alt_name', 'alt_plural_name'],
    'aliases': {
        'alt_name': 'name',
        'alt_plural_name': 'get_plural_name',
    },
    'allow_missing': True,
}


Context = {
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}


View = {
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}

Query = {
    'exclude': ['user', 'session_key'],
    'allow_missing': True,
}
