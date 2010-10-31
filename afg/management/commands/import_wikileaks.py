from __future__ import print_function
import re
import os
import csv
import json
import tempfile
import itertools
import subprocess
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from afg.models import DiaryEntry, import_fields

# How many words may constitute a phrase?
PHRASE_LENGTHS = [2]
# Phrases will only be linked if they match between these values
# (non-inclusive).
PHRASE_LINK_LIMITS = [1, 10]
OUTPUT_NAME = "data/processed.csv"

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

def thru(string):
    if string.strip() == '<null value>':
        return ""
    else:
        return string

class Command(BaseCommand):
    args = '<csv_file> <release_name>'
    help = """Import the wikileaks Afghan War Diary CSV file(s)."""

    def handle(self, *args, **kwargs):
        if len(args) < 2:
            print("""Requires two arguments: the path to the wikileaks Afghan War Diary CSV file, and a string identifying this release (e.g. "2010 July 25").  The CSV file can be downloaded here:

http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

""")
            return

        fields = [a[0] for a in import_fields]
        conversions = []
        for f in import_fields:
            if len(f) > 1:
                conversions.append(f[1])
            else:
                conversions.append(thru)

        rows = []
        phrases = defaultdict(set)

        for i in range(0, len(args), 2):
            filename = args[i]
            release = args[i + 1]

            print("Loading", filename)
            sp = StatusPrinter()

            with open(filename) as fh:
                reader = csv.reader(fh, delimiter=",", quotechar='"')
                for c, row in enumerate(reader):
                    if len(row) == 0:
                        continue
                    sp.print()
                    sp.inc()
                    values = map(lambda t: conversions[t[0]](t[1]), enumerate(row))
                    kwargs = dict(zip(fields, values))
                    kwargs['release'] = release
                    rows.append(kwargs)
                     
                    # get phrases
                    summary = re.sub(r'<[^>]*?>', '', kwargs['summary'])
                    summary = re.sub(r'&[^;\s]+;', ' ', summary)
                    summary = re.sub(r'[^A-Z ]', ' ', summary.upper())
                    summary = re.sub(r'\s+', ' ', summary).strip()
                    words = summary.split(' ')
                    for i in PHRASE_LENGTHS:
                        for j in range(i, len(words)):
                            phrase = " ".join(words[j-i:j])
                            if len(phrases[phrase]) <= PHRASE_LINK_LIMITS[1]:
                                phrases[phrase].add(kwargs['report_key'])
            sp.end()

        print("Calcuting phrase links...")
        phrase_links = defaultdict(dict)
        n = len(phrases)
        sp = StatusPrinter(0, n)
        for phrase, report_keys in phrases.iteritems():
            sp.print()
            sp.inc()
            if len(report_keys) > PHRASE_LINK_LIMITS[0] and \
                    len(report_keys) < PHRASE_LINK_LIMITS[1]:
                key_list = list(report_keys)
                for report_key in report_keys:
                    phrase_links[report_key][phrase] = key_list
        phrases = None
        sp.end()

        print("Writing CSV")
        # Write to CSV and bulk import.
        fields = rows[0].keys()
        fields.append('phrase_links')
        with open(OUTPUT_NAME, 'w') as fh:
            writer = csv.writer(fh)
            n = len(rows)
            c = 0
            # Pop rows to preserve memory (adding the json in phrase_links grows
            # too fast).
            sp = StatusPrinter(c, n)
            while len(rows) > 0:
                row = rows.pop(0)
                sp.print()
                sp.inc()
                row['phrase_links'] = json.dumps(phrase_links[row['report_key']])
                writer.writerow([row[f] for f in fields])
                c += 1
        sp.end()

        print("Loading into postgres")
        cmd = '''psql -U %(user)s -c "\copy %(table)s (%(fields)s) FROM '%(filename)s' WITH CSV NULL AS '<null value>' "''' % {
            'user': connection.settings_dict['USER'],
            'table': DiaryEntry._meta.db_table,
            'fields': ",".join('"%s"' % f for f in fields),
            'filename': OUTPUT_NAME,
        }
        print(cmd)
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
