from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', 'editor.app.views.home', name='home'),
    url(r'^searchparam/$', 'editor.app.views.search_param',
        name='search_param'),
    url(r'^searchparam/(?P<fformat>[^/]+)/$', 'editor.app.views.format_param',
        name='format_param'),
    url(r'^invalid_mappings/$', 'editor.app.views.invalid_mappings',
        name='invalid_mappings'),
    url(r'^fsearch/$', 'editor.app.views.fsearch', name='fsearch'),
    url(r'^search/(?P<fformat>[^/]+)/$', 'editor.app.views.search',
        name='search'),
    url(r'^concepts/(?P<fformat>[^/]+)/$', 'editor.app.views.concepts',
        name='concepts'),
    url(r'^concept/(?P<fformat>[^/]+)/$', 'editor.app.views.concept',
        name='concept'),
    url(r'^mappingformats/$', 'editor.app.views.mapping_formats',
        name='mapping_formats'),
    url(r'^definemediator/(?P<mediator>[^/]+)/(?P<fformat>[^/]+)/$',
        'editor.app.views.define_mediator', name='define_mediator'),
    url(r'^mappingconcepts/$', 'editor.app.views.mapping_concepts',
        name='mapping_concepts'),
    url(r'^definevalue/(?P<fformat>[^/]+)/$', 'editor.app.views.define_value',
        name='define_value'),
    url(r'^defineconcept/(?P<fformat>[^/]+)/$',
        'editor.app.views.define_concept', name='define_concept'),
    url(r'^valuemap/$', 'editor.app.views.value_maps', name='value_maps'),
    url(r'^definevaluemap', 'editor.app.views.define_valuemap',
        name='define_valuemaps'),
    url(r'^mappingedit', 'editor.app.views.mapping_edit', name='mapping_edit'),

)
