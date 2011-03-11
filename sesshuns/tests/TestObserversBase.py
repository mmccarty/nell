from copy                      import copy
from django.test.client        import Client
from django.conf               import settings
from django.contrib.auth       import models as m

from test_utils                import BenchTestCase, timeIt
from sesshuns.models           import *
from sesshuns.httpadapters     import *
from sesshuns.utilities        import create_user
from utils                     import create_sesshun, fdata
from sesshuns.GBTCalendarEvent import CalEventPeriod

class TestObserversBase(BenchTestCase):

    def setUp(self):
        super(TestObserversBase, self).setUp()

        # Don't use CAS for authentication during unit tests
        if 'django_cas.backends.CASBackend' in settings.AUTHENTICATION_BACKENDS:
            settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS[:-1]
        if 'django_cas.middleware.CASMiddleware' in settings.MIDDLEWARE_CLASSES:
            settings.MIDDLEWARE_CLASSES      = settings.MIDDLEWARE_CLASSES[:-1]

        self.client = Client()

        self.auth_user = m.User.objects.create_user('dss', 'dss@nrao.edu', 'asdf5!')
        self.auth_user.is_staff = True
        self.auth_user.save()

        # create the user
        self.u = User(first_name = "dss" #"Test"
                    , last_name  = "account" #"User"
                    , pst_id     = 3251
                    , role       = first(Role.objects.all())
                    #, username   = self.auth_user.username
                      )
        self.u.save()
        self.client.login(username = "dss", password = "asdf5!")

        # create a user to act as friend
        self.uFriend = User(first_name = "Best"
                          , last_name = "Friend"
                          , pst_id = None
                          , role = first(Role.objects.all())
                           )
        self.uFriend.save()

        # create a project
        self.p = Project()
        adapter = ProjectHttpAdapter(self.p)
        adapter.init_from_post({'semester'   : '09C'
                             , 'type'       : 'science'
                             , 'pcode'      : 'mike'
                             , 'name'       : 'mikes awesome project!'
                             , 'PSC_time'   : '100.0'
                             , 'total_time' : '100.0'
                             , 'sem_time'   : '50.0'
                               })

        # make the first user an investigator on this project
        i =  Investigator(project = self.p
                        , user    = self.u
                         )
        i.save()

        # assign the friend user to theis project
        self.friend = Friend(project = self.p
                 , user = self.uFriend)
        self.friend.save()

        # create a session for the project
        fdata2 = copy(fdata)
        fdata2.update({'source_v' : 1.0
                     , 'source_h' : 1.0
                     , 'source'   : 'testing'
                       })
        self.s = Sesshun()
        SessionHttpAdapter(self.s).init_from_post(fdata2)
        self.s.project = self.p
        self.s.save()

    def tearDown(self):
        super(TestObserversBase, self).tearDown()

    def get(self, url, data = {}):
        """
        Sets the USER extra kwar
        """
        return self.client.get(url, data, USER = self.auth_user.username)

    def post(self, url, data = {}):
        """
        Sets the USER extra kwar
        """
        return self.client.post(url, data, USER = self.auth_user.username)