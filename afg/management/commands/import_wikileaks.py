import csv
import datetime
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection

from afg import models

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


class Command(BaseCommand):
    args = '<csv_file>'
    help = """Import the wikileaks Afghan war diaries csv file."""

    def handle(self, *args, **kwargs):
        if len(args) < 1:
            print """Requires one argument: the path to the wikileaks Afghan war
diaries csv file."""
            return

        with open(args[0]) as fh:
            reader = csv.reader(fh)
            for row in reader:
                # Create model
                for i in range(13, 22):
                    row[i] = int(row[i] or 0)

                entry = models.DiaryEntry.objects.create(
                    **dict(zip(fields, row))
                )
                    
                summary = row[6]
                words = summary.upper().split()
                for i in range(3, 1, -1):
                    for j in range(i, len(words)):
                        phrase = models.Phrase.objects.get_or_create(
                                phrase=" ".join(words[j-i:j])[:255]
                        )[0]
                        entry.phrase_set.add(phrase)

        # denormalize entry counts.
        cursor = connection.cursor()
        cursor.execute("""
UPDATE afg_phrase SET entry_count = (SELECT COUNT(pe.*) FROM afg_phrase_entries pe WHERE pe.phrase_id = afg_phrase.id)
        """)

        # Postgresql full text search index
        cursor.execute("""
BEGIN;
ALTER TABLE afg_diaryentry ADD COLUMN summary_tsv tsvector;
CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON afg_diaryentry
    FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(summary_tsv, 'pg_catalog.english', summary);
CREATE INDEX summary_tsv_index ON afg_diaryentry USING gin(summary_tsv);
UPDATE afg_diaryentry SET summary_tsv=to_tsvector(summary);
COMMIT;
        """)

