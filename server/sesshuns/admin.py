from server.sesshuns.models import * 
from django.contrib import admin

class Receiver_GroupInline(admin.TabularInline):
    model = Receiver_Group
    extra = 1

class SesshunAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'frequency', 'allotment', 'receiver_list']
    list_filter = ['name',  'project']
    search_fields = ['name']
    #date_hierarchy = 'pub_date'
    inlines = [Receiver_GroupInline]

class SesshunInline(admin.TabularInline):
    model = Sesshun
    extra = 1

class SemesterAdmin(admin.ModelAdmin):
    list_display = ['semester']

class Project_TypeAdmin(admin.ModelAdmin):
    list_display = ['type']
    display = 'type'

class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'pcode', 'semester', 'project_type']
    inlines = [SesshunInline]

class ProjectInline(admin.TabularInline):
    model = Project
    extra = 1

class AllotmentAdmin(admin.ModelAdmin):
    list_display = ['psc_time', 'total_time', 'max_semester_time']
    inlines = [SesshunInline]

class Session_TypeAdmin(admin.ModelAdmin):
    list_display = ['type']

class Observing_TypeAdmin(admin.ModelAdmin):
    list_display = ['type']

class ReceiverAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'freq_low', 'freq_hi']

class ParameterAdmin(admin.ModelAdmin):
    list_display = ['name', 'type']

class CadenceAdmin(admin.ModelAdmin):
    pass

class Receiver_GroupAdmin(admin.ModelAdmin):
    pass

class Receiver_Group_ReceiverAdmin(admin.ModelAdmin):
    pass

class Observing_ParameterAdmin(admin.ModelAdmin):
    pass

class StatusAdmin(admin.ModelAdmin):
    pass

class WindowAdmin(admin.ModelAdmin):
    pass

class OpportunityAdmin(admin.ModelAdmin):
    pass

class SystemAdmin(admin.ModelAdmin):
    pass

class TargetAdmin(admin.ModelAdmin):
    pass

admin.site.register(Sesshun, SesshunAdmin)
admin.site.register(Semester, SemesterAdmin)
admin.site.register(Project_Type, Project_TypeAdmin)
admin.site.register(Allotment, AllotmentAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Session_Type, Session_TypeAdmin)
admin.site.register(Observing_Type, Observing_TypeAdmin)
admin.site.register(Receiver, ReceiverAdmin)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(Cadence, CadenceAdmin)
admin.site.register(Receiver_Group, Receiver_GroupAdmin)
admin.site.register(Receiver_Group_Receiver, Receiver_Group_ReceiverAdmin)
admin.site.register(Observing_Parameter, Observing_ParameterAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(Window, WindowAdmin)
admin.site.register(Opportunity, OpportunityAdmin)
admin.site.register(System, SystemAdmin)
admin.site.register(Target, TargetAdmin)
