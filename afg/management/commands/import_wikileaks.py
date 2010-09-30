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

def clean_summary(text):
    # Fix ampersand mess
    while text.find("&amp;") != -1:
        text = text.replace("&amp;", "&")
    text = re.sub('&(?!(#[a-z\d]+|\w+);)/gi', "&amp;", text)
    return text

class Command(BaseCommand):
    args = '<csv_file> <release_name>'
    help = """Import the wikileaks Afghan War Diary CSV file(s)."""

    def handle(self, *args, **kwargs):
        print args
        if len(args) < 2:
            print """Requires two arguments: the path to the wikileaks Afghan War Diary CSV file, and a string identifying this release (e.g. "2010 July 25").  The CSV file can be downloaded here:

http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

"""
            return

        fields = [a[0] for a in import_fields]
        thru = lambda f: f
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

            with open(filename) as fh:
                reader = csv.reader(fh)
                for c, row in enumerate(reader):
                    print "Loading", filename, c
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
                    for i in range(3, 1, -1):
                        for j in range(i, len(words)):
                            phrases[" ".join(words[j-i:j])].add(kwargs['report_key'])

        print "Calcuting phrase links..."
        phrase_links = defaultdict(dict)
        n = len(phrases)
        for c, (phrase, report_keys) in enumerate(phrases.iteritems()):
            print "Phrases:", c, n
            if len(report_keys) > 2 and len(report_keys) < 10:
                key_list = list(report_keys)
                for report_key in report_keys:
                    phrase_links[report_key][phrase] = key_list
        phrases = None

        print "Writing CSV"
        # Write to CSV and bulk import.
        fields = rows[0].keys()
        fields.append('phrase_links')
        temp = tempfile.NamedTemporaryFile(delete=False)
        writer = csv.writer(temp)
        name = temp.name
        n = len(rows)
        c = 0
        # Pop rows to preserve memory (adding the json in phrase_links grows
        # too fast).
        while len(rows) > 0:
            row = rows.pop(0)
            print "CSV", c, len(rows), n
            row['phrase_links'] = json.dumps(phrase_links[row['report_key']])
            writer.writerow([row[f] for f in fields])
            c += 1
        temp.close()

        print "Loading into postgres"
        cmd = '''psql -U %(user)s -c "\copy %(table)s (%(fields)s) FROM '%(filename)s' WITH CSV NULL AS 'NULL' "''' % {
            'user': connection.settings_dict['USER'],
            'table': DiaryEntry._meta.db_table,
            'fields': ",".join('"%s"' % f for f in fields),
            'filename': name,
        }
        print cmd
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        os.remove(name)
