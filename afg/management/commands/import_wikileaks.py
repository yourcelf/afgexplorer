import re
import csv
import datetime
import itertools
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from afg.models import DiaryEntry, Phrase

fields = ["report_key", # 0
    "date",             # 1
    "type",             # 2
    "category",         # 3
    "tracking_number",  # 4
    "title",            # 5 
    "summary",          # 6
    "region",           # 7 
    "attack_on",        # 8
    "complex_attack",   # 9 
    "reporting_unit",   # 10
    "unit_name",        # 11
    "type_of_unit",     # 12 
    "friendly_wia",     # 13
    "friendly_kia",     # 14
    "host_nation_wia",  # 15
    "host_nation_kia",  # 16
    "civilian_wia",     # 17
    "civilian_kia",     # 18
    "enemy_wia",        # 19
    "enemy_kia",        # 20
    "enemy_detained",   # 21
    "mgrs",             # 22
    "latitude",         # 23
    "longitude",        # 24
    "originator_group", # 25
    "updated_by_group", # 26
    "ccir",             # 27
    "sigact",           # 28
    "affiliation",      # 29
    "dcolor",           # 30
    "classification",   # 31
]

def clean_summary(text):
    # Fix ampersand mess
    while text.find("&amp;") != -1:
        text = text.replace("&amp;", "&")
    text = re.sub('&(?!(#[a-z\d]+|\w+);)/gi', "&amp;", text)

    # Linebreaks
    text = text.replace("\n", "<br />")
    return text

class Command(BaseCommand):
    args = '<csv_file>'
    help = """Import the wikileaks Afghan War Diary CSV file."""

    def handle(self, *args, **kwargs):
        if len(args) < 1:
            print """Requires one argument: the path to the wikileaks Afghan War Diary CSV file.  It can be downloaded here:

http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

"""
            return

        phrases = defaultdict(set)
        with open(args[0]) as fh:
            reader = csv.reader(fh)
            for c, row in enumerate(reader):
                print c
                for i in range(13, 22):
                    row[i] = int(row[i] or 0)
                kwargs = dict(zip(fields, row))
                kwargs['summary'] = clean_summary(kwargs['summary'])
                kwargs['latitude'] = float(kwargs['latitude']) if kwargs['latitude'] else None
                kwargs['longitude'] = float(kwargs['longitude']) if kwargs['longitude'] else None
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
        phrase_mappings = []
        phrase_counts = []
        for c, (phrase, entry_ids) in enumerate(phrases.iteritems()):
            if len(entry_ids) > 1:
                print c, n
                phrase = Phrase.objects.create(phrase=phrase)
                phrase_id = phrase.id
                phrase_counts.append((len(entry_ids), phrase_id))
                for entry_id in entry_ids:
                    phrase_mappings.append((phrase_id, entry_id))

        # Quickly as possible, update phrase mappings.
        cursor = connection.cursor()
        print 'phrase_entries...'
        cursor.executemany("INSERT INTO afg_phrase_entries (phrase_id, diaryentry_id) VALUES (%s, %s)", phrase_mappings)
        print 'phrase entry counts...'
        cursor.executemany("""UPDATE afg_phrase SET entry_count=%s WHERE id=%s""", phrase_counts)
        transaction.commit_unless_managed()
