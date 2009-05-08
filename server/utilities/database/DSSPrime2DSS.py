from sesshuns.models import *
from datetime        import datetime, timedelta
import math
import MySQLdb as m

class DSSPrime2DSS(object):
    """
    This class is reponsible for fetching data from the 'stepping stone'
    database, which is where the proposal information is stored after the
    export from Carl's database, and importing this data into the DSS database.
    """

    def __init__(self, host = "trent.gb.nrao.edu"
                     , user = "dss"
                     , passwd = "asdf5!"
                     , database = "dss_prime"
                     , silent   = True
                 ):
        self.db = m.connect(host   = host
                          , user   = user
                          , passwd = passwd
                          , db     = database
                            )
        self.cursor = self.db.cursor()
        self.silent = silent

    def __del__(self):
        self.cursor.close()

    def transfer(self):
        self.transfer_friends()
        self.transfer_projects()
        self.transfer_authors()
        self.transfer_sessions()
        self.transfer_project_blackouts_09B()

    def transfer_sessions(self):
        query = """
                SELECT sessions.*
                     , projects.pcode
                     , allotment.*
                     , status.*
                     , observing_types.type
                     , session_types.type
                FROM sessions
                INNER JOIN (projects
                          , allotment
                          , status
                          , observing_types
                          , session_types)
                ON sessions.project_id = projects.id AND
                   sessions.allotment_id = allotment.id AND
                   sessions.status_id = status.id AND
                   sessions.observing_type_id = observing_types.id AND
                   sessions.session_type_id = session_types.id
                ORDER BY sessions.id
                """
        self.cursor.execute(query)
        
        rows = self.cursor.fetchall()

        # Just run a quick query to check that we got all the sessions
        self.cursor.execute("SELECT id FROM sessions")
        results = self.cursor.fetchall()
        assert len(results) == len(rows)

        for row in rows:
            otype = first(Observing_Type.objects.filter(type = row[23]))
            stype = first(Session_Type.objects.filter(type = row[24]))
            project = first(Project.objects.filter(pcode = row[12]))

            allot = Allotment(psc_time          = float(row[14])
                            , total_time        = float(row[15])
                            , max_semester_time = float(row[16])
                            , grade             = float(row[17])
                              )
            allot.save()

            status = Status(enabled    = row[19] == 1
                          , authorized = row[20] == 1
                          , complete   = row[21] == 1
                          , backup     = row[22] == 1
                            )
            status.save()

            s = Sesshun(project        = project
                      , session_type   = stype
                      , observing_type = otype
                      , allotment      = allot
                      , status         = status
                      , original_id    = row[6] 
                      , name           = row[7]
                      , frequency      = float(row[8]) if row[8] is not None else None
                      , max_duration   = float(row[9]) if row[9] is not None else None
                      , min_duration   = float(row[10]) if row[10] is not None else None
                      , time_between   = float(row[11]) if row[11] is not None else None
                        )
            s.save()

            # now get the sources
            s_id_prime = row[0]
            query = """
                    SELECT *
                    FROM targets
                    WHERE session_id = %s
                    """ % s_id_prime
            self.cursor.execute(query)

            # All Systems J2000!
            system = first(System.objects.filter(name = "J2000"))

            for t in self.cursor.fetchall():
                try:
                    vertical = float(t[4])
                except:
                    vertical = None
                    #print "Exception with row: ", t, s
                try:
                    horizontal = float(t[5])
                except:
                    horizontal = None
                    #print "Exception with row: ", t, s
                if vertical is not None and horizontal is not None:    
                    target = Target(session    = s
                              , system     = system
                              , source     = t[3]
                              , vertical   = float(t[4]) * (math.pi / 180)
                              , horizontal = float(t[5]) * (math.pi / 12)
                                )
                    target.save()

            # now get the cadences
            query = "SELECT * FROM cadences WHERE session_id = %s" % s_id_prime
            self.cursor.execute(query)

            for c in self.cursor.fetchall():
                cad = Cadence(session = s
                            , start_date = c[2]
                            , end_date   = c[3]
                            , repeats    = c[4]
                            , full_size  = c[5]
                            , intervals  = c[6]
                              )
                cad.save()

            # now get the windows & opportunities
            # TBF: initially, we thought there would be none of these, and
            # they'd all be determined via the Cadences!
            query = "SELECT * FROM windows WHERE session_id = %s" % s_id_prime
            self.cursor.execute(query)
            for w in self.cursor.fetchall():
                win = Window(session = s, required = w[2])
                win.save()
  
                query = "SELECT * FROM opportunities WHERE window_id = %s" % w[0]
                self.cursor.execute(query)
                for o in self.cursor.fetchall():
                    op = Opportunity(window = win
                                   , start_time = o[2]
                                   , duration = float(o[3])
                                   )
                    op.save()

            # now get the rcvrs
            query = "SELECT id FROM receiver_groups WHERE session_id = %s" % s_id_prime
            self.cursor.execute(query)

            for id in self.cursor.fetchall():
                rg = Receiver_Group(session = s)
                rg.save()

                query = """SELECT receivers.name
                           FROM rg_receiver
                           INNER JOIN receivers ON rg_receiver.receiver_id = receivers.id
                           WHERE group_id = %s
                        """ % id
                self.cursor.execute(query)

                for r_name in self.cursor.fetchall():
                    rcvr = first(Receiver.objects.filter(name = r_name[0]))
                    rg.receivers.add(rcvr)
                rg.save()
                
            # now get the observing parameters
            query = """SELECT * 
                       FROM observing_parameters 
                       WHERE session_id = %s
                    """ % s_id_prime
            self.cursor.execute(query)

            for o in self.cursor.fetchall():
                p  = first(Parameter.objects.filter(id = o[2]))
                if p.name == 'Instruments' and o[3] == "None":
                    pass
                    #print "Not passing over Observing Parameter = Instruments(None)"
                else:    
                    op = Observing_Parameter(
                    session        = s
                  , parameter      = p
                  , string_value   = o[3] if o[3] is not None else None
                  , integer_value  = o[4] if o[4] is not None else None 
                  , float_value    = float(o[5]) if o[5] is not None else None
                  , boolean_value  = o[6] == 1 if o[6] is not None else None
                  , datetime_value = o[7] if o[7] is not None else None
                )
                    op.save()

        #self.populate_windows()

    def transfer_authors(self):

        query = "SELECT * FROM authors"
        self.cursor.execute(query)

        for row in self.cursor.fetchall():
            row  = list(row)
            p_id = row.pop(1)
            u    = self.create_user(row)
            
            query = "SELECT pcode FROM projects WHERE id = %s" % p_id
            self.cursor.execute(query)
            pcode = self.cursor.fetchone()[0]
            p     = first(Project.objects.filter(pcode = pcode).all())

            i = Investigators(project = p
                            , user    = u
                            , principal_contact      = row[6] == 1
                            , principal_investigator = row[5] == 1
                              )
            i.save()

    def transfer_project_blackouts_09B(self):
        "Only needed for scheduling 09B: project blackouts will then go away."

        query = "SELECT * from blackouts"
        self.cursor.execute(query)
        blackoutRows = self.cursor.fetchall()

        for row in blackoutRows:
            start       = row[1]
            end         = row[2]
            description = row[3]
            pkey        = row[5]
            pcodes      = row[6]

            # the people key and the pcodes must be matched to the right
            # people and projects
            query = "SELECT * FROM authors WHERE peoplekey = %d" % pkey
            self.cursor.execute(query)
            authors = self.cursor.fetchall()
            if len(authors) > 0:
                authorRow = list(authors[0])
                # we need to pop off the project id in order to be able to
                # use the create_user method
                p_id = authorRow.pop(1) 
                u = self.create_user(authorRow)
            else:
                # TBF: the fact that this is happening seems like a big
                # bug to me, but Carl just left us for a month. WTF
                print "WARNING: peoplekey in blackouts ~ in authors: ", pkey
                u = None

            # now what different projects is this for?
            pcodeList = pcodes.split(",")
            for pcode in pcodes.split(","):
                # each project gets its own project blackout!
                p = first(Project.objects.filter(pcode = pcode.strip()))
                if p is not None:
                    pb = Project_Blackout_09B(
                        project     = p
                      , requester   = u
                      , start       = start
                      , end         = end
                      , description = description
                    )
                    pb.save()

    def transfer_projects(self):
        query = """
                SELECT *
                FROM projects
                INNER JOIN (semesters, project_types)
                ON projects.semester_id = semesters.id AND
                   projects.project_type_id = project_types.id
                """
        self.cursor.execute(query)
        
        rows = self.cursor.fetchall()
        for row in rows:
            semester = first(Semester.objects.filter(semester = row[12]))
            ptype    = first(Project_Type.objects.filter(type = row[14]))

            p = Project(semester     = semester
                      , project_type = ptype
                      , pcode        = row[4]
                      , name         = self.filter_bad_char(row[5])
                      , thesis       = row[6] == 1
                      , complete     = row[7] == 1
                      , ignore_grade = row[8] == 1
                      , start_date   = row[9]
                      , end_date     = row[10]
                        )
            p.save()

            f_id = row[3]
            if f_id != 0:
                query = "select peoplekey from friends where id = %s" % f_id
                self.cursor.execute(query)

                o_id   = int(self.cursor.fetchone()[0])
                friend = first(User.objects.filter(original_id = o_id))
                query = "select * from friends where id = %s" % f_id
                self.cursor.execute(query)

                if friend is not None:
                    i = Investigators(project = p
                                    , user    = friend
                                    , friend  = True
                                      )
                    i.save()

            query = """
                    SELECT projects.pcode, allotment.*
                    FROM `projects`
                    LEFT JOIN (projects_allotments, allotment)
                    ON (projects.id = projects_allotments.project_id AND
                        projects_allotments.allotment_id = allotment.id)
                    WHERE projects.pcode = '%s'
                    """ % p.pcode
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            for row in rows:
                try:
                    psc, total, max_sem, grade = map(float, row[2:])
                except TypeError:
                    if not self.silent:
                        print "No alloment for project", p.pcode
                else:
                    a = Allotment(psc_time          = psc
                                , total_time        = total
                                , max_semester_time = max_sem
                                , grade             = grade
                                  )
                    a.save()
                    p.allotments.add(a)

    def transfer_friends(self):

        query = "SELECT * FROM friends"
        self.cursor.execute(query)
        
        for row in self.cursor.fetchall():
            _   = self.create_user(row)

    def create_user(self, row):

        # Check to see if the user is already in the system
        user = first(User.objects.filter(original_id = int(row[3])).all())

        # Skip to the next user if this one has been found
        if user is not None:
            row = self.cursor.fetchone()
            return user
            
        # TBF: we must support outrageous accents
        try:
            firstName = unicode(row[1])
        except:
            #print "exception with name: ", row[1]
            firstName = "exception"

        try:
            lastName = unicode(row[2])
        except:
            #print "exception with name: ", row[2]
            lastName = "exception"

        u = User(original_id = int(row[3])
               , sancioned   = False
               , first_name  = firstName #row[1]
               , last_name   = lastName #row[2]
                 )
        u.save()

        for e in row[4].split(','):
            # Check to see if the email address already exists.
            email = first(Email.objects.filter(email = e).all())

            # Create a new email record if email not found.
            if email is None:
                new_email = Email(user = u, email = e)
                new_email.save()

        return u
            
    def filter_bad_char(self, bad):
        good = bad.replace('\xad', '')
        return good
    
    def create_summer_maintanence(self):
        """
        Creates the maintanence session and dates needed for 09B.
        These aren't being transferred by Carl, so we must create them:
        June 1 - Sep. 30: Mon - Thr, starting at 7 AM for 10.5 Hrs
        Holiday Weekends: Mon - Thr, starting at 8 AM for 8.5  Hrs
        NRAO Holidays 09: July 3, Sep 7
        There will be some fixed sessions (VLBI, Radar) that will conflict
        with these - they should be managed by hand.
        """

        # clean up!
        ps = Project.objects.filter(pcode = "Maintenance")
        empty = [p.delete() for p in ps]
        ss = Sesshun.objects.filter(name = "Fixed Summer Maintenance")
        empty = [s.delete() for s in ss]

        # first, just set up the project and single session
        semesterName = "09B" 
        semesterStart = datetime(2009, 6, 1)
        semesterEnd = datetime(2009, 9, 30)

        semester = first(Semester.objects.filter(semester = "09B"))
        ptype    = first(Project_Type.objects.filter(type = "non-science"))

        p = Project(semester     = semester
                  , project_type = ptype
                  , pcode        = "Maintenance"
                  , name         = "Maintenance"
                  , thesis       = False 
                  , complete     = False
                  , ignore_grade = False
                  , start_date   = semesterStart 
                  , end_date     = semesterEnd
                    )
        p.save()

        # max hours should be some generous estimate of the time needed
        maxHrs = (16 * 10.5)
        allot = Allotment(psc_time          = maxHrs
                        , total_time        = maxHrs
                        , max_semester_time = maxHrs
                        , grade             = 4.0 
                          )
        allot.save()
        p.allotments.add(allot)
        status = Status(enabled    = True 
                      , authorized = True
                      , complete   = False 
                      , backup     = False
                        )
        status.save()
        otype    = first(Observing_Type.objects.filter(type = "maintenance"))
        stype    = first(Session_Type.objects.filter(type = "fixed"))
        s = Sesshun(project        = p
                  , session_type   = stype
                  , observing_type = otype
                  , allotment      = allot
                  , status         = status
                  , original_id    = 666 # TBF? 
                  , name           = "Fixed Summer Maintenance" 
                  , frequency      = 0.0 #None
                  , max_duration   = 12.0 #None
                  , min_duration   = 0.0 #None
                  , time_between   = 0.0 #None
                    )
        s.save()
        print s

        # TBF: put in a dummy target so that Antioch can pick it up!
        system = first(System.objects.filter(name = "J2000"))
        target = Target(session    = s
                      , system     = system
                      , source     = "maintanence" 
                      , vertical   = 0.0
                      , horizontal = 0.0
                    )
        target.save()
        
        # now create entries in Windows and Opportunities that can be
        # translated into Periods for this fixed session

        # what weeks have NRAO holidays in them?
        # July 3, Friday!
        holidayWeek1 = [datetime(2009, 6, 29) + timedelta(days=i) for i in range(4)]
        holidayWeek2 = [datetime(2009, 9,  7) + timedelta(days=i) for i in range(4)]
        holidayWeeks = holidayWeek1
        holidayWeeks.extend(holidayWeek2)

        # first, loop through weeks
        for week in range(18):
            # then loop through Mon - Thrs
            for day in range(4): 
                # TBF: what time zone are we using?  See what happens to these
                # times when we load them up in Antioch ...
                dt = semesterStart + timedelta(days = (week*7) + day)
                # do we need to adjust for NRAO holiday?
                if dt in holidayWeeks:
                    # holiday week
                    # watch for that pesky labor day - it falls on a Monday
                    start = dt + timedelta(seconds = 4 * 60 * 60) #4 == 8 AM
                    if start == datetime(2009, 9, 7):
                        # schedule monday's on friday!
                        start = datetime(2009, 9, 11)
                    dur = 8.5 # hrs
                else:
                    # normal week
                    start = dt + timedelta(seconds = 3 * 60 * 60) #3 == 7 AM
                    dur = 10.5 # hrs

                # create the table entries
                # don't do this past Sep 30!
                if start <= semesterEnd:
                    w = Window( session = s, required = True)
                    w.save()
                    o = Opportunity( window     = w
                                   , start_time = start
                                   , duration   = dur
                                   )
                    o.save()               

