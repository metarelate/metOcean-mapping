from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', 'editor.app.views.home', name='home'),
    url(r'^searchparam/$', 'editor.app.views.search_param', name='search_param'),
    url(r'^searchparam/(?P<fformat>[^/]+)/$', 'editor.app.views.format_param', name='format_param'),
    url(r'^mappings/$', 'editor.app.views.mappings', name='mappings'),
    url(r'^edit_mappings/$', 'editor.app.views.edit_mappings', name='edit_mappings'),
    url(r'^fsearch/$', 'editor.app.views.fsearch', name='fsearch'),
    url(r'^search/(?P<fformat>[^/]+)/$', 'editor.app.views.search', name='search'),
    url(r'^new_mapping/$', 'editor.app.views.new_mapping', name='new_mapping'),
    url(r'^concepts/(?P<fformat>[^/]+)/$', 'editor.app.views.concepts', name='concepts'),
    url(r'^concept/(?P<fformat>[^/]+)/$', 'editor.app.views.concept', name='concept'),
    # url(r'^editor/', include('editor.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
