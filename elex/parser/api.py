# -*- coding: utf-8 -*-

import datetime
import json
import os

from dateutil import parser

import elex
from elex.parser import utils


STATE_ABBR = { 'AL': 'Alabama', 'AK': 'Alaska', 'AS': 'America Samoa', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FM': 'Micronesia1', 'FL': 'Florida', 'GA': 'Georgia', 'GU': 'Guam', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MH': 'Islands1', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PW': 'Palau', 'PA': 'Pennsylvania', 'PR': 'Puerto Rico', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VI': 'Virgin Island', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}


class BaseObject(object):
    """
    Base class for most objects.
    Handy container for methods for first level
    transformation of data and AP connections.
    """

    def aggregate_vote_count(self, field_from, field_to):
        """
        Simple function for aggregating vote counts.
        Accepts a field_from and a field_to.
        field_from = where to aggregate votes from.
        field_to = where to add the aggregated votes to.
        """

        # Sometimes we need to aggregate votes up from candidates arrays.
        if hasattr(self, 'candidates') and len(getattr(self, 'candidates')) > 0:
            setattr(
                self,
                field_to,
                getattr(self, field_to) + sum([getattr(c, field_from) for c in getattr(self, 'candidates')]))

        # Sometimes we need to aggregate votes up from the reportingunits arrays.
        if hasattr(self, 'reportingunits') and len(getattr(self, 'reportingunits')) > 0:
            setattr(
                self,
                field_to,
                getattr(self, field_to) + sum([getattr(r, field_from) for r in getattr(self, 'reportingunits')]))

    def set_state_fields_from_reportingunits(self):
        if len(self.reportingunits) > 0:
            setattr(self, 'statepostal', self.reportingunits[0].statepostal)
            for ru in self.reportingunits:
                if ru.statename:
                    setattr(self, 'statename', ru.statename)

    def set_winner(self):
        """
        Translates winner: "X" into a boolean.
        """
        if self.winner == u"X":
            setattr(self, 'winner', True)
        else:
            setattr(self, 'winner', False)

    def set_reportingunits(self):
        """
        If this race has reportingunits,
        serialize them into objects.
        """
        reportingunits_obj = []
        for r in self.reportingunits:
            reportingunit_dict = dict(r)

            # Denormalize some data.
            for attr in ['raceid','seatname','description','racetype','officeid','uncontested','officename']:
                if hasattr(self, attr):
                    reportingunit_dict[attr] = getattr(self, attr)

            reportingunits_obj.append(ReportingUnit(**reportingunit_dict))
        setattr(self, 'reportingunits', reportingunits_obj)

    def set_reportingunitids(self):
        """
        Per Tracy / AP developers, if the level is
        "state", the reportingunitid is always 1.
        """
        if not self.reportingunitid:
            if self.level == "state":
                setattr(self, 'reportingunitid', "1")

    def set_candidates(self):
        """
        If this thing (race, reportingunit) has candidates,
        serialize them into objects.
        """
        candidate_objs = []
        for c in self.candidates:
            candidate_dict = dict(c)

            # Decide if this is a ballot position or a _real_ candidate.
            if hasattr(self, 'racetype'):
                if getattr(self, 'racetype') == u"Ballot Issue":
                    candidate_dict['is_ballot_position'] = True

            if hasattr(self, 'officeid'):
                if getattr(self, 'officeid') == u'I':
                    candidate_dict['is_ballot_position'] = True

            # Denormalize some data.
            for attr in ['raceid','statepostal','reportingunitid','reportingunitname','fipscode','seatname','description','racetype','officeid','uncontested','officename']:
                if hasattr(self, attr):
                    candidate_dict[attr] = getattr(self, attr)

            candidate_dict['statename'] = STATE_ABBR[getattr(self, 'statepostal')]

            candidate_objs.append(CandidateResult(**candidate_dict))
        setattr(self, 'candidates', sorted(candidate_objs, key=lambda x: x.ballotorder))

    def set_dates(self, date_fields):
        for field in date_fields:
            try:
                setattr(self, field + '_parsed', parser.parse(getattr(self, field)))
            except AttributeError:
                pass

    def set_fields(self, **kwargs):
        fieldnames = self.__dict__.keys()
        for k,v in kwargs.items():
            k = k.lower().strip()
            try:
                v = unicode(v.decode('utf-8'))
            except AttributeError:
                pass
            if k in fieldnames:
                setattr(self, k, v)

    def __repr__(self):
        return self.__unicode__()

    def __str__(self):
        return self.__unicode__()

    def get(self, path, **params):
        """
        Farms out request to api_request.
        Could possibly handle choosing which
        parser backend to use -- API-only right now.
        Also the entry point for recording, which
        is set via environment variable.
        """
        return utils.api_request(path, **params)


class CandidateResult(BaseObject):
    """
    Canonical reporesentation of an
    AP candidate. Note: A candidate can 
    be a person OR a ballot position.
    """
    def __init__(self, **kwargs):
        self.racetype = None
        self.seatname = None
        self.officename = None
        self.description = None
        self.raceid = None
        self.officeid = None
        self.statepostal = None
        self.statename = None
        self.reportingunitid = None
        self.reportingunitname = None
        self.first = None
        self.last = None
        self.party = None
        self.candidateid = None
        self.polid = None
        self.ballotorder = None
        self.polnum = None
        self.votecount = 0
        self.winner = False
        self.is_ballot_position = False
        self.reportingunit_votecount = 0
        self.reportingunit_votepct = 0.0
        self.race_votecount = 0
        self.race_votepct = 0.0
        self.uncontested = False

        self.set_fields(**kwargs)
        self.set_winner()

    def aggregate_pcts(self, race_votecount, reportingunit_votecount):
        """
        Method for handling CandidateResult pcts.
        """
        if not self.uncontested:
            self.race_votecount = race_votecount
            self.reportingunit_votecount = reportingunit_votecount

            if self.race_votecount > 0:
                self.race_votepct = float(self.votecount) / float(self.race_votecount)

            if self.reportingunit_votecount > 0:
                self.reportingunit_votepct = float(self.votecount) / float(self.reportingunit_votecount)

    def __unicode__(self):
        if self.is_ballot_position:
            payload = "%s" % self.party
        else:
            payload = "%s %s (%s)" % (self.first, self.last, self.party)
        if self.winner:
            payload += '✓'.decode('utf-8')
        return payload


class ReportingUnit(BaseObject):
    """
    Canonical representation of a single
    level of reporting. Can be 
    """
    def __init__(self, **kwargs):
        self.seatname = None
        self.description = None
        self.raceid = None
        self.officeid = None
        self.officename = None
        self.racetype = None
        self.statepostal = None
        self.statename = None
        self.level = None
        self.reportingunitname = None
        self.reportingunitid = None
        self.fipscode = None
        self.lastupdated = None
        self.precinctsreporting = 0
        self.precinctsyotal = 0
        self.precinctsreportingpct = 0.0
        self.candidates = []
        self.reportingunit_votecount = 0
        self.race_votecount = 0
        self.race_votepct = 0.0
        self.uncontested = False

        self.set_fields(**kwargs)
        self.set_dates(['lastupdated'])
        self.set_reportingunitids()
        self.set_candidates()

    def aggregate_pcts(self, race_votecount):
        """
        Method for handling ReportingUnit pcts.
        """
        if not self.uncontested:
            self.race_votecount = race_votecount

            if self.race_votecount > 0:
                self.race_votepct = float(self.reportingunit_votecount) / float(self.race_votecount)

    def __unicode__(self):
        if self.reportingunitname:
            return "%s %s (%s %% reporting)" % (self.statepostal, self.reportingunitname, self.precinctsreportingpct)
        return "%s %s (%s %% reporting)" % (self.statepostal, self.level, self.precinctsreportingpct)


class Race(BaseObject):
    """
    Canonical representation of a single
    race, which is a seat in a political geography
    within a certain election.
    """
    def __init__(self, **kwargs):
        self.test = False
        self.raceid = None
        self.statepostal = None
        self.statename = None
        self.racetype = None
        self.racetypeid = None
        self.officeid = None
        self.officename = None
        self.party = None
        self.seatname = None
        self.description = None
        self.seatnum = None
        self.uncontested = False
        self.lastupdated = None
        self.candidates = []
        self.reportingunits = []
        self.race_votecount = 0

        self.initialization_data = False

        self.set_fields(**kwargs)
        self.set_dates(['lastupdated'])

        if self.initialization_data:
            self.set_candidates()
        else:
            self.set_reportingunits()
            self.set_state_fields_from_reportingunits()

    def __unicode__(self):
        name = self.officename
        if self.statepostal:
            name = "%s %s" % (self.statepostal, self.officename)
            if self.seatname:
                name += " %s" % self.seatname
        return name


class Election(BaseObject):
    """
    Canonical representation of an election on
    a single date.
    """
    def __init__(self, **kwargs):
        self.testresults = False
        self.liveresults = False
        self.electiondate = None
        self.is_test = False

        self.parsed_json = None
        self.next_request = None

        self.set_fields(**kwargs)
        self.set_dates(['electiondate'])

    def __unicode__(self):
        if self.is_test:
            return "TEST: %s" % self.electiondate
        else:
            return self.electiondate

    @classmethod
    def get_elections(cls):
        return [Election(**election) for election in list(Election.get('/')['elections'])]

    @classmethod
    def get_next_election(cls):
        today = datetime.datetime.now()
        next_election = None
        lowest_diff = None
        for e in Election.get_elections():
            diff = (e.electiondate_parsed - today).days
            if diff > 0:
                if not lowest_diff and not next_election:
                    next_election = e
                    lowest_diff = diff
                elif lowest_diff and next_election:
                    if diff < lowest_diff:
                        next_election = e
                        lowest_diff = diff
        return next_election

    def get_races(self, **kwargs):
        """
        Convenience method for fetching races by election date.
        Accepts an AP formatting date string, e.g., YYYY-MM-DD.
        Accepts any number of URL params as kwargs.
        """
        self.parsed_json = self.get('/%s' % self.electiondate, **kwargs)
        self.next_request = self.parsed_json['nextrequest']

        # With `omitResults=True`, the API will return initialization data.
        if kwargs.get('omitResults', None):
            payload = []
            for r in self.parsed_json['races']:
                r['initialization_data'] = True
                payload.append(Race(**r))
            return payload
        return [Race(**r) for r in self.parsed_json['races']]
