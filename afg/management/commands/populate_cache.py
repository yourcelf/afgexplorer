from __future__ import print_function
import time
import sys
import urllib
from django.core.management.base import BaseCommand

from afg.models import DiaryEntry

class StatusPrinter(object):
    def __init__(self, c=0, n=0):
        self.c = c
        self.n = n
        self.previous = ""

    def inc(self):
        self.c += 1

    def print(self):
        print("\b" * len(self.previous), end="")
        self.previous = "{0} / {1}".format(self.c, self.n)
        print(self.previous, end="")

    def end(self):
        print()

class Command(BaseCommand):
    args = '<base url> [delay=0]'
    help = """Initialize the cache of the given server with all diary entries."""

    def handle(self, *args, **kwargs):
        try:
            base_url = args[0].rstrip('/')
            try:
                delay = int(args[1])
            except IndexError:
                delay = 0
        except IndexError:
            print(args)
            print(help)
            sys.exit()

        sp = StatusPrinter(0, DiaryEntry.objects.count())

        for entry in DiaryEntry.objects.all().values('report_key'):
            urllib.urlopen("%s/id/%s/" % (base_url, entry['report_key']))
            time.sleep(delay)
            sp.inc()
            sp.print()
        sp.end()
