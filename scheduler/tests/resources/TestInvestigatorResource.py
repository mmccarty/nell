from django.test.client  import Client

from test_utils               import BenchTestCase, timeIt
from scheduler.httpadapters   import *
from scheduler.models         import *
from scheduler.tests.utils    import create_users

class TestInvestigatorResource(BenchTestCase):

    def setUp(self):
        super(TestInvestigatorResource, self).setUp()
        self.client = Client()
        p_fdata = {'semester'   : '09C'
                 , 'type'       : 'science'
                 , 'pcode'      : 'mike'
                 , 'name'       : 'mikes awesome project!'
                 , 'PSC_time'   : '100.0'
                 , 'total_time' : '100.0'
                 , 'sem_time'   : '50.0'
                   }
        self.p = Project()
        p_adapter = ProjectHttpAdapter(self.p)
        p_adapter.init_from_post(p_fdata)
        self.p.save()

        self.users = create_users()
        self.ins = []
        self.ins.append(Investigator(project                = self.p
                                   , user                   = self.users[0]
                                   , observer               = True
                                   , principal_contact      = False
                                   , principal_investigator = False
                                   , priority               = 2
                                   ))
        self.ins[-1].save()
        self.ins.append(Investigator(project                = self.p
                                   , user                   = self.users[1]
                                   , observer               = True
                                   , principal_contact      = True
                                   , principal_investigator = True
                                   , priority               = 1
                                   ))
        self.ins[-1].save()
        self.fdata = {'name'       : self.users[-1].last_name
                    , 'pi'         : 'False'
                    , 'contact'    : 'False'
                    , 'remote'     : 'False'
                    , 'project_id' : self.p.id
                    , 'user_id'    : self.users[-1].id
                    , 'observer'   : 'true'
                    , 'priority'   : 1
                     }

    @timeIt
    def test_create(self):
        response = self.client.post('/scheduler/investigators'
                                  , self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    @timeIt
    def test_create_empty(self):
        response = self.client.post('/scheduler/investigators'
                                  , {'project_id' : self.p.id
                                   , 'user_id': self.users[-1].id})
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/scheduler/investigators'
                                 , {'project_id' : self.p.id})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 2' in response.content)

    def test_read_with_filter(self):
        response = self.client.get(
              '/scheduler/investigators'
            , {'project_id' : self.p.id
            ,  'filterText' : 'Mike'
            })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 1' in response.content)
        self.assertTrue('McCarty' in response.content)

    @timeIt
    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"
                    , "remote"  : "True"
                    })
        response = self.client.post('/scheduler/investigators/%s' % self.ins[-1].id
                                  , fdata)
        self.failUnlessEqual(response.status_code, 200)

        fdata2 = {u'pi': [u'false'], u'user_id': [u'494.0']
                , u'name': [u'McCarty, Michael'], u'observer': [u'true']
                , u'priority': [u'1.0'], u'contact': [u'false']
                , u'remote': [u'true'], u'project_id': [u'5.0']
                , u'id': [u'995.0'], u'_method': [u'put']}
        response = self.client.post('/scheduler/investigators/%s' % self.ins[-1].id
                                  , fdata2)
        self.failUnlessEqual(response.status_code, 200)

    @timeIt
    def test_delete(self):
        response = self.client.post('/scheduler/investigators/%s' % self.ins[-1].id
                                  , {"_method" : "delete"})
        self.failUnlessEqual(response.status_code, 200)

