from django.db import models

# No DB indexes because we're kicking all that to SOLR.
class DiaryEntry(models.Model):
    report_key = models.CharField(max_length=255, unique=True)
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
    ccir = models.CharField(max_length=255)
    sigact = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=255)
    dcolor = models.CharField(max_length=255)
    classification = models.CharField(max_length=255)

    # denormalization for sorting
    def total_casualties(self):
        return self.friendly_wia + self.friendly_kia + self.host_nation_wia + self.host_nation_kia + self.civilian_wia + self.civilian_kia + self.enemy_wia + self.enemy_kia

    def __unicode__(self):
        return self.title

    def to_dict(self):
        obj = {}
        for field in self._meta.fields:
            obj[field.name] = unicode(getattr(self, field.name))
        return obj

    class Meta:
        ordering = ['date']
        verbose_name_plural = 'Diary entries'

    def casualty_summary(self):
        parts = []
        for attr in ('civilian', 'host_nation', 'friendly', 'enemy'):
            k = getattr(self, attr + '_kia')
            w = getattr(self, attr + '_wia')
            if k or w:
                counts = []
                if k:
                    counts.append("%i killed" % k)
                if w:
                    counts.append("%i wounded" % w)
                parts.append("%s: %s" % (attr.title().replace("_", " "), ", ".join(counts)))
            return "; ".join(parts)

class Phrase(models.Model):
    phrase = models.CharField(max_length=255, unique=True, db_index=True)
    entries = models.ManyToManyField(DiaryEntry)

    # denormalization for performance
    entry_count = models.IntegerField(default=0, db_index=True)

    def __unicode__(self):
        return self.phrase
