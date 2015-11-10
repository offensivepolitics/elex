import csv
import json
import sys

from cement.core.foundation import CementApp
from cement.core.controller import CementBaseController, expose
from clint.textui import puts
from dateutil import parser
from elex.parser import api


def _parse_date(datestring, app):
    """
    Parse many date formats into an AP friendly format.
    """
    dateobj = parser.parse(datestring)
    return dateobj.strftime('%Y-%m-%d')


def process_date_hook(app):
    """
    Pre-parse date argument.
    """
    if len(app.argv):
        try:
            app.argv[-1] = _parse_date(app.argv[-1], app)
        except ValueError:
            puts('"{0}" could not be recognized as a date.\n'.format(app.argv[-1]))
            app.args.print_help()
            app.close()
    else:
        puts('Please specify an election date and optional command (e.g. `elex init-races 2015-11-03`)\n')
        app.args.print_help()
        app.close()


def add_races_hook(app):
    """
    Cache data after parsing args.
    """
    print app.pargs
    app.election = api.Election(
        electiondate=app.pargs.date[0],
        testresults=app.pargs.test,
        liveresults=not app.pargs.not_live,
        is_test=False
    )


class ElexBaseController(CementBaseController):
    class Meta:
        label = 'base'
        description = "Get and process AP elections data"
        arguments = [
            (['-t', '--test'], dict(
                action='store_true',
            )),
            (['-n', '--not-live'], dict(
                action='store_true',
            )),
            (['date'], dict(
                nargs=1,
                action='store',
                help='Election date (e.g. "2015-11-03"; most common date formats accepted).'
            )),
        ]

    @expose(help="Initialize races")
    def init_races(self):
        race_data = self.app.election.get_races(
            omitResults=False,
            level="ru",
            test=self.app.pargs.test
        )
        races, reporting_units, candidate_reporting_units = self.app.election.get_units(race_data)

        writer = csv.writer(sys.stdout)
        writer.writerow([field for field in races[0].fields if (field != 'reportingunits' and field != 'candidates')])
        for race in races:
            writer.writerow([getattr(race, field) for field in race.fields if (field != 'reportingunits' and field != 'candidates')])


class ElexApp(CementApp):
    class Meta:
        label = 'elex'
        base_controller = ElexBaseController
        hooks = [
            ('pre_argument_parsing', process_date_hook),
            ('post_argument_parsing', add_races_hook)
        ]


def main():
    with ElexApp() as app:
        app.run()
