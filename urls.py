from django.conf.urls.defaults     import *
from sesshuns.views                import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(''
   , url(r'^projects$',           ProjectResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^projects/(\d+)$',     ProjectResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^sessions/options$',   get_options)
   , url(r'^schedule$',           get_schedule)
   , url(r'^sessions$',           SessionResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^sessions/(\d+)$',     SessionResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^receivers/schedule$', receivers_schedule)
   , url(r'^period/form$',        period_form)
   , url(r'^period/form/(\d+)$',  period_form)
   , url(r'^period$',             PeriodResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^period/(\d+)$',       PeriodResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^periodJSON$',             PeriodJSONResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^periodJSON/(\d+)$',       PeriodJSONResource(permitted_methods=('PUT', 'GET', 'POST')))
   , (r'^admin/',                 include(admin.site.urls))
)
