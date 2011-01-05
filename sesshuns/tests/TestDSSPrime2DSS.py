import MySQLdb as mysql

from nell.utilities.database import DSSPrime2DSS
from sesshuns.models         import *
from test_utils              import NellTestCase

class TestDSSPrime2DSS(NellTestCase):

    def assert_DB_empty(self):
        # make sure our DB is almost blank
        projects = Project.objects.all()
        self.assertEquals(1, len(projects))
        ss = Sesshun.objects.all()
        self.assertEquals(0, len(ss))
        users = User.objects.all()
        self.assertEquals(0, len(users))

    def compare_users(self, dbname):

        old = []
        new = []
        fold, fnew = self.compare_users_worker(dbname, "friends", old, new)
        pold, pnew = self.compare_users_worker(dbname, "authors", fold, fnew)
        return (pold, pnew)

    def compare_users_worker(self, dbname, table, old_users, new_users):

        db = mysql.connect(host   = "trent.gb.nrao.edu"
                     , user   = "dss"
                     , passwd = "asdf5!"
                     , db     = dbname
                            )
        cursor = db.cursor()

        query = "SELECT * FROM %s" % table
        cursor.execute(query)

        for row in cursor.fetchall():
            idcol = 3 if table == "friends" else 4
            id = int(row[idcol])
            user = first(User.objects.filter(original_id = id).all())
            if user is None:
                if id not in new_users:
                    new_users.append(id)
            else:
                if id not in old_users:
                    old_users.append(id)

        return (old_users, new_users)

    def test_transfer(self):

        self.assert_DB_empty()

        t = DSSPrime2DSS(database = 'dss_prime_unit_tests')
        t.quiet = True
        t.transfer()

        # now test what we've got to make sure the transfer worked:

        # check out the projects
        projects = Project.objects.all()
        # len(93) == 92 + 1 prexisting project in models
        self.assertEquals(93, len(projects))

        # spot check project table
        projects = Project.objects.filter(semester__id = 15).all()
        self.assertEquals(1, len(projects))
        p = projects[0]
        self.assertEquals("GBT05C-027", p.pcode)
        self.assertEquals(False, p.thesis)
        self.assertEquals("Balser", p.friend.last_name)
        allots = p.allotments.all()
        self.assertEquals(1, len(allots))
        a = allots[0]
        self.assertEquals(5.0, a.total_time)
        self.assertEquals(4.0, a.grade)
        invs = p.investigator_set.all().order_by('id')
        self.assertEquals(2, len(invs))
        self.assertEquals("Mangum", invs[0].user.last_name)
        self.assertEquals("Wootten", invs[1].user.last_name)


        ss = p.sesshun_set.all()
        self.assertEquals(1, len(ss))
        s = ss[0]
        self.assertEquals("GBT05C-027-01", s.name)
        self.assertEquals(32.75, s.frequency)
        self.assertEquals(0, len(s.observing_parameter_set.all()))
        self.assertEquals(False, s.status.complete)
        self.assertEquals(5.0, s.allotment.total_time)
        self.assertEquals(4.0, s.allotment.grade)
        tgs = s.target_set.all()
        self.assertEquals(1, len(tgs))
        target = tgs[0]
        self.assertEqual("G34.3,S68N,DR21OH", target.source)
        self.assertAlmostEqual(0.022, target.vertical, 3)
        self.assertAlmostEqual(4.84, target.horizontal, 2)

        ss = Sesshun.objects.all()
        self.assertEquals(247, len(ss))

        users = User.objects.all()
        self.assertEquals(287, len(users))

    def test_transfer_only_new_1(self):

        self.assert_DB_empty()

        # populate into an empty DB: not much of a test, really!
        t = DSSPrime2DSS(database = 'dss_prime_unit_tests_2')
        t.quiet = True
        t.transfer_only_new()

        self.assertEquals( 53, len(t.new_projects))
        self.assertEquals(  0, len(t.old_projects))
        self.assertEquals(121, len(t.new_sessions))
        self.assertEquals(  0, len(t.old_sessions))
        self.assertEquals(199, len(t.new_users))
        self.assertEquals(  0, len(t.old_users))

    def test_transfer_only_new_2(self):

        self.assert_DB_empty()

        # populate the DB w/ 09C and earlier stuff
        t = DSSPrime2DSS(database = 'dss_prime_unit_tests')
        t.quiet = True
        t.transfer()

        # now that our model DB is initialized, predict how many new and
        # old users reside in our new source DB.
        old_users, new_users = self.compare_users('dss_prime_unit_tests_2')

        # now make sure we transfer only the new 10A stuff
        t = DSSPrime2DSS(database = 'dss_prime_unit_tests_2')
        t.quiet = True
        t.transfer_only_new()

        self.assertEquals( 53, len(t.new_projects))
        self.assertEquals(  0, len(t.old_projects))
        self.assertEquals(121, len(t.new_sessions))
        self.assertEquals(  0, len(t.old_sessions))
        self.assertEquals(len(new_users), len(t.new_users))
        self.assertEquals(len(old_users), len(t.old_users))

