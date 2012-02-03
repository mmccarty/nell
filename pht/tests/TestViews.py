# Copyright (C) 2011 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning GBT software should be addressed as follows:
#       GBT Operations
#       National Radio Astronomy Observatory
#       P. O. Box 2
#       Green Bank, WV 24944-0002 USA

import simplejson as json
from django.test.client import Client
from django.test        import TestCase
from pht.models         import *
from pht.utilities      import *
import math

class TestViews(TestCase):
    # must use django.test.TestCase if we want fixtures
    fixtures = ['proposal_GBT12A-002.json']

    def setUp(self):
        # load the single proposal from the fixture
        self.proposal = Proposal.objects.get(pcode = "GBT12A-002")
        self.client   = Client()
        self.dtfmt    = "%m/%d/%Y"

        sess = self.proposal.session_set.all()[0]
        self.session = sess
        self.s_data  = {
                    'pst_session_id'   : sess.pst_session_id
                  , 'pcode' : sess.proposal.pcode
                  , 'name' : sess.name
                  , 'semester' : sess.semester.semester
                  , 'requested_time' : sess.allotment.requested_time
                  , 'session_type' : sess.session_type.type
                  , 'weather_type' : sess.weather_type.type
                  , 'repeats' : sess.allotment.repeats
                  , 'separation' : sess.separation
                  , 'interval_time' : sess.interval_time
                  , 'constraint_field' : sess.constraint_field
                  , 'comments' : sess.comments
                  , 'min_lst' : rad2sexHrs(sess.target.min_lst)
                  , 'max_lst' : rad2sexHrs(sess.target.max_lst)
                  , 'elevation_min' : rad2sexDeg(sess.target.elevation_min)
                  , 'session_time_calculated' : sess.session_time_calculated
                  }

        src = self.proposal.source_set.all()[0]
        self.src_data = {
                'pcode'                   : src.proposal.pcode
              , 'target_name'             : src.target_name
              , 'coordinate_system'       : src.coordinate_system
              , 'ra'                      : rad2sexHrs(src.ra)
              , 'dec'                     : rad2sexDeg(src.dec)
              , 'ra_range'                : rad2sexHrs(src.ra_range)
              , 'dec_range'               : rad2sexDeg(src.dec_range)
              , 'velocity_units'          : src.velocity_units
              , 'velocity_redshift'       : src.velocity_redshift
              , 'convention'              : src.convention
              , 'reference_frame'         : src.reference_frame
              , 'observed'                : src.observed
              , 'allowed'                 : src.allowed
               }
        
               
    def tearDown(self):
        for p in Proposal.objects.all():
            p.delete()

    def eval_response(self, response_content):
        "Makes sure we can turn the json string returned into a python dict"
        return eval(response_content.replace('false', 'False').replace('true', 'True').replace('null', 'None'))

    # Proposal CRUD
    def test_proposals(self):
        self.client   = Client()
        response = self.client.get("/proposals")
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(self.proposal.pcode, results['proposals'][0]['pcode'])
        self.assertEqual(self.proposal.title, results['proposals'][0]['title'])
        self.assertEqual(self.proposal.proposal_type.type, results['proposals'][0]['proposal_type'])

    def test_proposal_get(self):
        self.client   = Client()
        response = self.client.get("/proposals/%s" % self.proposal.pcode)
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(self.proposal.pcode, results['pcode'])
        self.assertEqual(self.proposal.title, results['title'])
        self.assertEqual(self.proposal.proposal_type.type, results['proposal_type'])

    def test_proposal_post(self):
        self.client   = Client()
        data     = {'pi_id'           : self.proposal.pi.id
                  , 'proposal_type'   : self.proposal.proposal_type.type
                  , 'status'          : self.proposal.status.name
                  , 'semester'        : self.proposal.semester.semester
                  , 'pst_proposal_id' : self.proposal.pst_proposal_id
                  , 'pcode'           : self.proposal.pcode.replace('-002', '-003')
                  , 'submit_date'     : self.proposal.submit_date.strftime(self.dtfmt)
                  , 'total_time'      : self.proposal.total_time
                  , 'title'           : self.proposal.title
                  , 'abstract'        : self.proposal.abstract
                  , 'observing_types' : [o.type for o in self.proposal.observing_types.all()]
                  , 'joint_proposal'  : str(not self.proposal.joint_proposal)
                   }
        response = self.client.post("/proposals", json.dumps(data)
                                  , content_type='application/json')
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(results.get('pcode'), data.get('pcode'))
        self.assertEqual(results.get('observing_types')
                       , data.get('observing_types'))

    def test_proposal_post_empty(self):
        self.client   = Client()
        data     = {'pi_id'           : self.proposal.pi.id
                  , 'proposal_type'   : self.proposal.proposal_type.type
                  , 'status'          : self.proposal.status.name
                  , 'semester'        : self.proposal.semester.semester
                  , 'pst_proposal_id' : ''
                  , 'pcode'           : self.proposal.pcode.replace('-002', '-003')
                  , 'submit_date'     : self.proposal.submit_date.strftime(self.dtfmt)
                  , 'total_time'      : ''
                  , 'title'           : self.proposal.title
                  , 'abstract'        : self.proposal.abstract
                  , 'joint_proposal'  : str(not self.proposal.joint_proposal)
                   }
        response = self.client.post("/proposals", json.dumps(data)
                                  , content_type='application/json')
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(results.get('pcode'), data.get('pcode'))

    def test_proposal_put(self):
        self.client   = Client()
        data     = {'pi_id'           : self.proposal.pi.id
                  , 'proposal_type'   : self.proposal.proposal_type.type
                  , 'status'          : self.proposal.status.name
                  , 'semester'        : self.proposal.semester.semester
                  , 'pst_proposal_id' : self.proposal.pst_proposal_id
                  , 'pcode'           : self.proposal.pcode.replace('-002', '-001')
                  , 'submit_date'     : self.proposal.submit_date.strftime(self.dtfmt)
                  , 'total_time'      : self.proposal.total_time
                  , 'title'           : self.proposal.title
                  , 'abstract'        : self.proposal.abstract
                  , 'joint_proposal'  : str(not self.proposal.joint_proposal)
                   }

        before   = len(Proposal.objects.all())
        response = self.client.put("/proposals/%s" % self.proposal.pcode, json.dumps(data)
                                 , content_type='application/json')
        after    = len(Proposal.objects.all())
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        proposal = Proposal.objects.get(id = self.proposal.id) # Get fresh instance from db
        self.assertEqual(proposal.pcode, data.get('pcode'))
        self.assertEqual(before - after, 0)

    def test_proposal_delete(self):
        before   = len(Proposal.objects.all())
        response = self.client.delete("/proposals/%s" % self.proposal.pcode)
        after    = len(Proposal.objects.all())
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(before - after, 1)

    # Session CRUD
    def test_sessions(self):
        sess = self.proposal.session_set.all()[0]
        self.client   = Client()
        response = self.client.get("/sessions")
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(self.proposal.pcode, results['sessions'][0]['pcode'])
        self.assertEqual(sess.name, results['sessions'][0]['name'])

    def test_session_get(self):
        self.client   = Client()
        sess = self.proposal.session_set.all()[0]
        response = self.client.get("/sessions/%s" % sess.id)
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(sess.id, results['id'])
        self.assertEqual(sess.name, results['name'])
        self.assertEqual(self.proposal.pcode, results['pcode'])

    def test_session_delete(self):
        before   = len(Session.objects.all())
        sess = self.proposal.session_set.all()[0]
        response = self.client.delete("/sessions/%s" % sess.id)
        after    = len(Session.objects.all())
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(before - after, 1)

    def test_session_post(self):
                   
        before   = len(Session.objects.all())
        response = self.client.post("/sessions/%s" % self.session.id
                                  , json.dumps(self.s_data)
                                  , content_type='application/json')
        after    = len(Session.objects.all().order_by('id'))
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(after - before, 1)
        self.assertEqual(results.get('name'), self.s_data.get('name'))
        # look at the new one in the DB
        s = Session.objects.all().order_by('id')[after-1]
        self.assertTrue(s.allotment is not None)

    def test_session_put(self):
        before   = len(Session.objects.all())
        response = self.client.put("/sessions/%s" % self.session.id
                                 , json.dumps(self.s_data)
                                 , content_type='application/json')
        after    = len(Session.objects.all())
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        sessAgain = Session.objects.get(id = self.session.id) # Get fresh instance from db
        self.assertEqual(sessAgain.name, self.s_data.get('name'))
        self.assertEqual(before - after, 0)

    def test_session_put_lst(self):
        
        include, exclude = self.session.get_lst_string()
        self.assertEqual('', exclude)
        self.assertEqual('', include)
        lst_ex = '2.00-4.00'
        lst_in = '3.50-5.00, 22.00-23.75'
        self.s_data['lst_ex'] = lst_ex 
        self.s_data['lst_in'] = lst_in 

        response = self.client.put("/sessions/%s" % self.session.id
                                 , json.dumps(self.s_data)
                                 , content_type='application/json')
        after    = len(Session.objects.all())
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)

        sessAgain = Session.objects.get(id = self.session.id) # Get fresh instance from db
        include, exclude = self.session.get_lst_string()
        self.assertEqual(lst_ex, exclude)
        self.assertEqual(lst_in, include)
         
    def test_session_put_resources(self):
        "by resources we mean rcvrs & backends"

        self.assertEqual('gbtSpec', self.session.get_backends())
        self.assertEqual('C', self.session.get_receivers())
        self.assertEqual('', self.session.get_receivers_granted())
        self.s_data['backends'] = 'gbtSpec,gbtSpecP'
        self.s_data['receivers'] = 'L,S,X'
        self.s_data['receivers_granted'] = 'L,X'
        response = self.client.put("/sessions/%s" % self.session.id
                                 , json.dumps(self.s_data)
                                 , content_type='application/json')
        after    = len(Session.objects.all())
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        sessAgain = Session.objects.get(id = self.session.id) # Get fresh instance from db
        self.assertEqual('gbtSpec,gbtSpecP', sessAgain.get_backends())
        self.assertEqual('L,S,X', sessAgain.get_receivers())
        self.assertEqual('L,X', sessAgain.get_receivers_granted())

    """
    def test_session_post_source(self):
        print Source.objects.all()
    """
        
    # Session CRUD
    def test_proposal_sources(self):
        self.client   = Client()
        url = "/proposals/%s/sources" % self.proposal.pcode
        response = self.client.get(url)
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(self.proposal.pcode, results['sources'][0]['pcode'])
        self.assertEqual('J2000', results['sources'][0]['coordinate_system'])

    def test_source_get(self):
        self.client   = Client()
        src = self.proposal.source_set.all()[0]
        response = self.client.get("/sources/%s" % src.id)
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(src.target_name, results['target_name'])
        self.assertEqual(self.proposal.pcode, results['pcode'])

    def test_source_delete(self):
        src = self.proposal.source_set.all()[0]
        before   = len(Source.objects.all())
        response = self.client.delete("/sources/%s" % src.id)
        after    = len(Source.objects.all())
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(before - after, 1)

    def test_source_post(self):
                   
        src = self.proposal.source_set.all()[0]
        response = self.client.post("/sources/%s" % src.id
                                  , json.dumps(self.src_data)
                                  , content_type='application/json')
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(results.get('target_name'), self.src_data.get('target_name'))

    def test_source_put(self):
        before   = len(Source.objects.all())
        src = self.proposal.source_set.all()[0]
        response = self.client.put("/sources/%s" % src.id
                                 , json.dumps(self.src_data)
                                 , content_type='application/json')
        after    = len(Source.objects.all())
        results = self.eval_response(response.content)

        self.failUnlessEqual(response.status_code, 200)
        srcAgain = Source.objects.get(id = src.id) # Get fresh instance from db
        self.assertEqual(srcAgain.target_name, self.src_data.get('target_name'))
        self.assertEqual(before - after, 0)

    def test_session_sources_get(self):
        session  = Session.objects.all()[0] # get a session

        # Get me all the sources on this session
        response = self.client.get('/sessions/%s/sources' % session.id)
        results  = self.eval_response(response.content)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(len(results['sources']), 0)

        # Add some sources to the session
        for source in session.proposal.source_set.all():
            session.sources.add(source)

        # Get me all the sources on this session again.  New ones
        # should be there.
        response = self.client.get('/sessions/%s/sources' % session.id)
        results  = self.eval_response(response.content)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(len(results['sources']), 3)

        # Clean up
        for source in session.sources.all():
            session.sources.remove(source)

    def test_session_sources_post(self):
        session   = Session.objects.all()[0] # get as session
        source_id = session.proposal.source_set.all()[0].id

        # Add a source to this session
        response = self.client.post('/sessions/%s/sources/%s' % (session.id, source_id))
        results  = self.eval_response(response.content)
        self.failUnlessEqual(response.status_code, 200)

        # Is the new source there?
        session = Session.objects.get(id = session.id)
        self.assertTrue(len(session.sources.all()) > 0)

        # Clean up
        for source in session.sources.all():
            session.sources.remove(source)

    def test_session_sources_delete(self):
        session   = Session.objects.all()[0] # get as session

        # Add some sources to the session
        for source in session.proposal.source_set.all():
            session.sources.add(source)

        # Pick a source to remove
        source_id = session.sources.all()[0].id

        # Add some sources to the session
        for source in session.proposal.source_set.all():
            session.sources.add(source)

        # Remove a source from this session
        response = self.client.delete('/sessions/%s/sources/%s' % (session.id, source_id))

        # Has the source been removed?
        session = Session.objects.get(id = session.id)
        sources = [s.id for s in session.sources.all()]
        self.assertTrue(source_id not in sources)

    def test_session_average_ra_dec(self):
        session   = Session.objects.all()[0] # get as session

        # Get request should return a 404
        response = self.client.get('/sessions/%s/averageradec' % session.id)
        self.failUnlessEqual(response.status_code, 404)


        sources = []
        # Add some sources to the session
        for source in session.proposal.source_set.all():
            session.sources.add(source)
            sources.append(source.id)

        data     = {'sources': sources}
        response = self.client.post('/sessions/%s/averageradec' % session.id, data)
        results  = self.eval_response(response.content)
        self.failUnlessEqual(response.status_code, 200)

        self.assertAlmostEqual(results['data']['ra'], 4.7902, 4)
        self.assertAlmostEqual(results['data']['dec'], -0.2146, 4)

        positions = [(0.2, 3), (0.1, 3), (2 * math.pi - .2, 3)]
        #positions = [(0.2, 3), (2 * math.pi - .2, 3)]
        sources   = [self.addSource(session, ra, dec).id for ra, dec in positions]

        data     = {'sources': sources}
        response = self.client.post('/sessions/%s/averageradec' % session.id, data)
        results  = self.eval_response(response.content)
        self.failUnlessEqual(response.status_code, 200)

        self.assertAlmostEqual(results['data']['ra'], 6.2582, 4)
        self.assertAlmostEqual(results['data']['dec'], 3.0, 4)

    def addSource(self, session, ra, dec):
        source = Source(pst_source_id = 0
                      , proposal_id = session.proposal_id
                      , target_name = 'test target'
                      , coordinate_system = 'J2000'
                      , ra = ra
                      , ra_range = ra
                      , dec = dec
                      , dec_range = dec
                      , velocity_units = 'km/s'
                      , velocity_redshift = '1'
                      , convention = 'star trek'
                      , reference_frame = 'rest'
                      )

        source.save()
        return source
