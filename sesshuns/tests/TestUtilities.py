from django.test.client  import Client

from test_utils              import BenchTestCase, timeIt
from sesshuns.models         import *
from sesshuns.utilities      import *
from utils                   import create_sesshun

class TestUtilities(BenchTestCase):

    def setupInvestigators(self, invs, proj):
        "Creates investigators, and returns expected emails."

        emails = []
        obs = Role.objects.get(role = "Observer")
        for fn, ln, pi, pc, ob, id in invs:
            u = User(first_name = fn
                   , last_name  = ln
                   , role = obs
                   , pst_id = id # give them sombody's email
                    )
            u.save()
            inv = Investigator(user = u
                             , project = proj
                             , principal_investigator = pi
                             , principal_contact = pc
                             , observer = ob
                              )
            inv.save() 
            emails.append(sorted(u.getEmails()))
        return emails  
       

    def test_getInvestigators(self):

        # get the project we assume is already in the DB
        proj = first(Project.objects.all())

        # create a bunch of investigators for it:
        invs = [("PI", "PI", True, False, False, 821) # Paul
              , ("PC", "PC", False, True, False, 554) # Amy
              , ("obs1", "obs1", False, False, True, 3253) # Mark
              , ("obs2", "obs2", False, False, True, 3680) # Ray
                ]

                
        emails = self.setupInvestigators(invs, proj)
          
        pi, pc, ci, ob, fs = getInvestigatorEmails([proj.pcode])
        
        self.assertEqual(emails[0], pi)
        self.assertEqual(emails[1], pc)
        self.assertEqual([emails[2][0], emails[3][0]], ci)
        self.assertEqual([emails[2][0], emails[3][0]], ob)
        self.assertEqual([], fs)

        # try it again, overlapping roles
        for u in User.objects.all():
            u.delete()
        for i in Investigator.objects.all():
            i.delete()
        invs = [("PI", "PI", True, True, False, 821) # Paul
              , ("PC", "PC", False, True, True, 554) # Amy
              , ("obs1", "obs1", False, False, True, 3253) # Mark
              , ("obs2", "obs2", False, False, False, 3680) # Ray
                ]        
                
        emails = self.setupInvestigators(invs, proj)
          
        pi, pc, ci, ob, fs = getInvestigatorEmails([proj.pcode])
        
        self.assertEqual(emails[0], pi)
        pc_emails = list(emails[1])
        pc_emails.extend(emails[0])
        self.assertEqual(pc_emails, pc)
        self.assertEqual([emails[2][0], emails[3][0]], ci)
        self.assertEqual([emails[1][0], emails[2][0]], ob)
        self.assertEqual([], fs)

        # now make some friends
        obs = Role.objects.get(role = "Observer")
        u = User(pst_id = 554, role = obs)
        u.save()
        f = Friend(user = u, project = proj)
        f.save()

        pi, pc, ci, ob, fs = getInvestigatorEmails([proj.pcode])
        
        self.assertEqual(emails[0], pi)
        self.assertEqual(pc_emails, pc)
        self.assertEqual([emails[2][0], emails[3][0]], ci)
        self.assertEqual([emails[1][0], emails[2][0]], ob)
        self.assertEqual(emails[1], fs)

    def test_project_search(self):

        # create some projects
        pt = first(Project_Type.objects.all())
        sem10a = Semester.objects.get(semester = "10A")
        p1 = Project(pcode = "GBT10A-001"
                   , semester = sem10a
                   , name = "Greatest Project Ever"
                   , project_type = pt
                    )
        p1.save()            
        p2 = Project(pcode = "GBT10A-002"
                   , semester = sem10a
                   , name = "Suckiest Project Ever"
                   , project_type = pt
                    )
        p2.save()            
        allProjs = Project.objects.all()

        # look for them
        projs = project_search("")
        self.assertEqual(len(allProjs), len(projs))
        projs = project_search("GBT10A-001")
        self.assertEqual(1,  len(projs))
        self.assertEqual(p1, projs[0])
        projs = project_search("GBT10A-002")
        self.assertEqual(1,  len(projs))
        self.assertEqual(p2, projs[0])
        projs = project_search("10A")
        self.assertEqual(2,  len(projs))
        projs = project_search("Suck")
        self.assertEqual(1,  len(projs))
        self.assertEqual(p2, projs[0])
        projs = project_search("10A02")
        self.assertEqual(1,  len(projs))
        self.assertEqual(p2, projs[0])
