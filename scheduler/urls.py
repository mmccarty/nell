from django.conf.urls.defaults import *

from scheduler.views     import *
from scheduler.resources import *

urlpatterns = patterns(''
   , url(r'^configurations/explorer/columnConfigs$',       column_configurations_explorer)
   , url(r'^configurations/explorer/columnConfigs/(\d+)$', column_configurations_explorer)
   , url(r'^configurations/explorer/filterCombos$',        filter_combinations_explorer)
   , url(r'^configurations/explorer/filterCombos/(\d+)$',  filter_combinations_explorer)
   , url(r'^projects/email$',                              projects_email)
   , url(r'^projects/time_accounting/([^/]+)$',            time_accounting)
   , url(r'^sessions/options$',                            get_options)
   , url(r'^sessions/time_accounting/([^/]+)$',            session_time_accounting)
   , url(r'^schedule/change_schedule$',                    change_schedule)
   , url(r'^schedule/shift_period_boundaries$',            shift_period_boundaries)
   , url(r'^schedule/email$',                              scheduling_email)
   , url(r'^receivers/schedule$',                          receivers_schedule)
   , url(r'^receivers/shift_date$',                        rcvr_schedule_shift_date)
   , url(r'^receivers/add_date$',                          rcvr_schedule_add_date)
   , url(r'^receivers/toggle_rcvr$',                       rcvr_schedule_toggle_rcvr)
   , url(r'^receivers/delete_date$',                       rcvr_schedule_delete_date)
   , url(r'^reservations$',                                reservations)
   , url(r'^period/([^/]+)/time_accounting$',              period_time_accounting)
   , url(r'^periods/publish$',                             publish_periods)
   , url(r'^periods/publish/(\d+)$',                       publish_periods)
   , url(r'^periods/delete_pending',                       delete_pending)
   , url(r'^projects$',               ProjectResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^projects/(\d+)$',         ProjectResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^sessions$',               SessionResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^sessions/(\d+)$',         SessionResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^periods/(UTC)$',          PeriodResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^periods/(ET)$',           PeriodResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^periods/(UTC)/(\d+)$',    PeriodResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^periods/(ET)/(\d+)$',     PeriodResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^windows$',                WindowResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^windows/(\d+)$',          WindowResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^windowRanges$',           WindowRangeResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^windowRanges/(\d+)$',     WindowRangeResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^users$',                  UserResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^users/(\d+)$',            UserResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^investigators$',          InvestigatorResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^investigators/([^/]+)$',  InvestigatorResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^friends$',                FriendResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^friends/([^/]+)$',        FriendResource(permitted_methods=('PUT', 'GET', 'POST')))
   , url(r'^electives$',              ElectiveResource(permitted_methods=('GET', 'PUT', 'POST')))
   , url(r'^electives/(\d+)$',        ElectiveResource(permitted_methods=('PUT', 'GET', 'POST')))
)