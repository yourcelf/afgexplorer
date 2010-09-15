import re
import json
import datetime

from django.db import models

def clean_summary(text):
    # Fix ampersand mess
    while text.find("&amp;") != -1:
        text = text.replace("&amp;", "&")
    text = re.sub('&(?!(#[a-z\d]+|\w+);)/gi', "&amp;", text)
    return text

def force_int(a):
    return int(a or 0)

def float_or_null(f):
    if f:
        return float(f)
    return "NULL"

import_fields = [
    ("report_key",),       # 0
    ("date",),             # 1
    ("type",),             # 2
    ("category",),         # 3
    ("tracking_number",),  # 4
    ("title",),            # 5 
    ("summary", clean_summary),          # 6
    ("region",),           # 7 
    ("attack_on",),        # 8
    ("complex_attack", lambda f: bool(f)),   # 9 
    ("reporting_unit",),   # 10
    ("unit_name",),        # 11
    ("type_of_unit",),     # 12 
    ("friendly_wia", force_int),     # 13
    ("friendly_kia", force_int),     # 14
    ("host_nation_wia", force_int),  # 15
    ("host_nation_kia", force_int),  # 16
    ("civilian_wia", force_int),     # 17
    ("civilian_kia", force_int),     # 18
    ("enemy_wia", force_int),        # 19
    ("enemy_kia", force_int),        # 20
    ("enemy_detained", force_int),   # 21
    ("mgrs",),             # 22
    ("latitude", float_or_null),         # 23
    ("longitude", float_or_null),        # 24
    ("originator_group",), # 25
    ("updated_by_group",), # 26
    ("ccir", lambda f: f or ""),             # 27
    ("sigact",),           # 28
    ("affiliation",),      # 29
    ("dcolor",),           # 30
    ("classification",),   # 31
]
# No DB indexes because we're kicking all that to SOLR.
class DiaryEntry(models.Model):
    release = models.CharField(max_length=255)
    report_key = models.CharField(max_length=255, primary_key=True)
    date = models.DateTimeField()
    type = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    tracking_number = models.CharField(max_length=255)
    title = models.TextField()
    summary = models.TextField()
    region = models.CharField(max_length=255)
    attack_on = models.CharField(max_length=255)
    complex_attack = models.BooleanField()
    reporting_unit = models.CharField(max_length=255)
    unit_name = models.CharField(max_length=255)
    type_of_unit = models.CharField(max_length=255)
    friendly_wia = models.IntegerField()
    friendly_kia = models.IntegerField()
    host_nation_wia = models.IntegerField()
    host_nation_kia = models.IntegerField()
    civilian_wia = models.IntegerField()
    civilian_kia = models.IntegerField()
    enemy_wia = models.IntegerField()
    enemy_kia = models.IntegerField()
    enemy_detained = models.IntegerField()
    mgrs = models.CharField(max_length=255)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    originator_group = models.CharField(max_length=255)
    updated_by_group = models.CharField(max_length=255)
    ccir = models.CharField(max_length=255, default="")
    sigact = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=255)
    dcolor = models.CharField(max_length=255)
    classification = models.CharField(max_length=255)

    phrase_links = models.TextField(blank=True, default="")

    def total_casualties(self):
        return self.friendly_wia + self.friendly_kia + self.host_nation_wia + self.host_nation_kia + self.civilian_wia + self.civilian_kia + self.enemy_wia + self.enemy_kia

    def __unicode__(self):
        return self.title

    def to_dict(self):
        obj = {}
        for field in self._meta.fields:
            obj[field.name] = unicode(getattr(self, field.name))
        obj['phrase_links'] = json.loads(self.phrase_links)
        return obj

    class Meta:
        ordering = ['date']
        verbose_name_plural = 'Diary entries'
