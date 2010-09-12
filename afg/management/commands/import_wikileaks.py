import re
import csv
import datetime
import itertools
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from afg.models import DiaryEntry, Phrase, import_fields

def clean_summary(text):
    # Fix ampersand mess
    while text.find("&amp;") != -1:
        text = text.replace("&amp;", "&")
    text = re.sub('&(?!(#[a-z\d]+|\w+);)/gi', "&amp;", text)
    return text

class Command(BaseCommand):
    args = '<csv_file> <release_name>'
    help = """Import the wikileaks Afghan War Diary CSV file."""

    def handle(self, *args, **kwargs):
        if len(args) < 2:
            print """Requires two arguments: the path to the wikileaks Afghan War Diary CSV file, and a string identifying this release (e.g. "2010 July 25").  The CSV file can be downloaded here:

http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

"""
            return

        release = args[1]
        fields = [a[0] for a in import_fields]
        thru = lambda f: f
        conversions = []
        for f in import_fields:
            if len(f) > 1:
                conversions.append(f[1])
            else:
                conversions.append(thru)


        phrases = defaultdict(set)
        with open(args[0]) as fh:
            reader = csv.reader(fh)
            for c, row in enumerate(reader):
                if c % 1000 == 0:
                    print c
                values = map(lambda t: conversions[t[0]](t[1]), enumerate(row))
                kwargs = dict(zip(fields, values))
                kwargs['release'] = release
                entry = DiaryEntry.objects.create(**kwargs)

                # Get words for phrases
                summary = re.sub(r'<[^>]*?>', '', kwargs['summary'])
                summary = re.sub(r'&[^;\s]+;', ' ', summary)
                summary = re.sub(r'[^A-Z ]', ' ', summary.upper())
                summary = re.sub(r'\s+', ' ', summary).strip()
                words = summary.split(' ')
                for i in range(3, 1, -1):
                    for j in range(i, len(words)):
                        print entry.id
                        phrases[" ".join(words[j-i:j])].add(entry.id)

        n = len(phrases)
        cursor = connection.cursor()
        transaction.commit_unless_managed()
        # Drop the join reference constraint for efficiency.  We're confident
        # that the 4 million rows we're about to add all satisfy the
        # constraint, and it saves about 5 hours of computation time.
        cursor.execute('''ALTER TABLE "afg_phrase_entries" DROP CONSTRAINT "phrase_id_refs_id_48aa97f2"''')
        for c, (phrase, entry_ids) in enumerate(phrases.iteritems()):
            if c % 10000 == 0:
                transaction.commit_unless_managed()
                print c, n
            if len(entry_ids) > 1 and len(entry_ids) <= 10:
                cursor.execute("INSERT INTO afg_phrase (phrase, entry_count) VALUES (%s, %s) RETURNING id", (phrase, len(entry_ids)))
                phrase_id = cursor.fetchone()[0]
                phrase_entries = []
                for entry_id in entry_ids:
                    phrase_entries.append((phrase_id, entry_id))
                cursor.executemany("""INSERT INTO afg_phrase_entries (phrase_id, diaryentry_id) VALUES (%s, %s)""", phrase_entries)

        cursor.execute('''ALTER TABLE "afg_phrase_entries" ADD CONSTRAINT "phrase_id_refs_id_48aa97f2" FOREIGN KEY ("phrase_id") REFERENCES "afg_phrase" ("id") DEFERRABLE INITIALLY DEFERRED;''')
        transaction.commit_unless_managed()

