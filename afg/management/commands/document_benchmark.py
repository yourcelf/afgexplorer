#
# This command builds a set of document URLs to use for stress testing the full
# stack.  Invoke with a base URL and number of document URLs to generate.
#
# An example using `palb` as a benchmarker with this management command.  This
# will run a benchmark with 10 concurrent users making 1000 requests, each to a
# distinct random but valid search URL, so as to miss the cache often:
#
#   python manage.py document_benchmark http://example.com 1000 | xargs palb -c 10 -n 1000
#
import sys
from django.core.management.base import BaseCommand

from afg.models import DiaryEntry

class Command(BaseCommand):
    args = '<base url> <number of urls>'
    help = """Construct a list of random URLs to use for benchmarking the server."""

    def handle(self, *args, **kwargs):
        try:
            base_url = args[0].rstrip('/')
            number_of_urls = int(args[1])
        except IndexError:
            print self.args
            print self.help
            sys.exit()

        report_keys = [v['report_key'] for v in DiaryEntry.objects.values('report_key').order_by('?')[0:number_of_urls]]

        for key in report_keys:
            print "%s/id/%s/" % (base_url, key)
