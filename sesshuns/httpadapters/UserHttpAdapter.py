from django.contrib.auth.models import User

from sesshuns.models        import Role
from sesshuns.models.common import first

class UserHttpAdapter(object):

    def __init__(self, user):
        self.user = user

    def load(self, user):
        self.user = user

    def update_from_post(self, fdata):
        username = fdata.get('username')

        role  = first(Role.objects.filter(role = fdata.get('role')))
        self.user.role        = role
        self.user.username    = username
        sanctioned            = fdata.get('sanctioned')
        self.user.sanctioned  = sanctioned.lower() == 'true' if sanctioned is not None else sanctioned
        self.user.first_name  = fdata.get('first_name')
        self.user.last_name   = fdata.get('last_name')
        self.user.contact_instructions   = fdata.get('contact_instructions')
        self.user.save()

        auth_user          = first(User.objects.filter(username = username))
        if auth_user is not None:
            staff              = fdata.get('staff')
            auth_user.is_staff = staff.lower() == 'true' if staff is not None else staff
            auth_user.save()

    def jsondict(self):
        auth_user       = first(User.objects.filter(username = self.user.username))
        projects = ','.join([i.project.pcode for i in self.user.investigator_set.all()])
        return {'id' : self.user.id
              , 'username'   : self.user.username
              , 'first_name' : self.user.first_name
              , 'last_name'  : self.user.last_name
              , 'sanctioned' : self.user.sanctioned
              , 'staff'      : auth_user.is_staff if auth_user is not None else False
              , 'projects'   : projects
              , 'role'       : self.user.role.role
                }

