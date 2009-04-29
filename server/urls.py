from django.conf.urls.defaults     import *
from server.sesshuns.views import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
   # ...
     url(r'^cadences$',        CadenceResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^cadences/(\d+)$',  CadenceResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^selected$',                get_selected)
   , url(r'^sessions/options$',        get_options)
   , url(r'^sessions$',       SessionResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^sessions/(\d+)$', SessionResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^windows$',        WindowResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^windows/(\d+)$',  WindowResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^gen_opportunities$',        gen_opportunities)
   , url(r'^gen_opportunities/(\d+)$',  gen_opportunities)
   , (r'^admin/(.*)', admin.site.root)
)
