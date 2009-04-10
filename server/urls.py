from django.conf.urls.defaults     import *
from server.sesshuns.views import SessionResource, WindowResource, gen_opportunities

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
   # ...
     url(r'^sessions$',       SessionResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^sessions/(\d+)$', SessionResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^windows$',        WindowResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^windows/(\d+)$',  WindowResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^gen_opportunities$',        gen_opportunities)
   , url(r'^gen_opportunities/(\d+)$',  gen_opportunities)
   , (r'^admin/(.*)', admin.site.root)
)
