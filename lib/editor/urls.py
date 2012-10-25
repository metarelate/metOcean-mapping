from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', 'editor.app.views.home', name='home'),
    url(r'^searchparam/$', 'editor.app.views.search_param', name='search_param'),
    url(r'^searchparam/(?P<format>[^/]+)/$', 'editor.app.views.format_param', name='format_param'),
    # url(r'^showsearchparams/$', 'editor.app.views.showsearchparams', name='showsearchparams'),
    url(r'^mapping/$', 'editor.app.views.mapping', name='mapping'),
    url(r'^search/$', 'editor.app.views.search', name='search'),
    # url(r'^editor/', include('editor.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
