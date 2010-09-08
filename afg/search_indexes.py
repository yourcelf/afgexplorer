import datetime
from haystack import indexes
from haystack import site
from afg.models import DiaryEntry

class DiaryEntryIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    report_key = indexes.CharField(model_attr='report_key')
    date = indexes.DateTimeField(model_attr='date', faceted=True)
    type_ = indexes.CharField(model_attr='type', faceted=True)
    category = indexes.CharField(model_attr='category', faceted=True)
    tracking_number = indexes.CharField(model_attr='tracking_number')
    title = indexes.CharField(model_attr='title')
    summary = indexes.CharField(model_attr='summary')
    region = indexes.CharField(model_attr='region', faceted=True)
    attack_on = indexes.CharField(model_attr='attack_on', faceted=True)
    complex_attack = indexes.BooleanField(model_attr='complex_attack', faceted=True)
    reporting_unit = indexes.CharField(model_attr='reporting_unit', faceted=True)
    unit_name = indexes.CharField(model_attr='unit_name', faceted=True)
    type_of_unit = indexes.CharField(model_attr='type_of_unit', faceted=True)
    friendly_wia = indexes.IntegerField(model_attr='friendly_wia', faceted=True)
    friendly_kia = indexes.IntegerField(model_attr='friendly_kia', faceted=True)
    host_nation_wia = indexes.IntegerField(model_attr='host_nation_wia', faceted=True)
    host_nation_kia = indexes.IntegerField(model_attr='host_nation_kia', faceted=True)
    civilian_wia = indexes.IntegerField(model_attr='civilian_wia', faceted=True)
    civilian_kia = indexes.IntegerField(model_attr='civilian_kia', faceted=True)
    enemy_wia = indexes.IntegerField(model_attr='enemy_wia', faceted=True)
    enemy_kia = indexes.IntegerField(model_attr='enemy_kia', faceted=True)
    enemy_detained = indexes.IntegerField(model_attr='enemy_detained', faceted=True)
    mgrs = indexes.CharField(model_attr='mgrs', faceted=True)
    latitude = indexes.FloatField(model_attr='latitude', null=True)
    longitude = indexes.FloatField(model_attr='longitude', null=True)
    originator_group = indexes.CharField(model_attr='originator_group', faceted=True)
    updated_by_group = indexes.CharField(model_attr='updated_by_group', faceted=True)
    ccir = indexes.CharField(model_attr='ccir', faceted=True)
    sigact = indexes.CharField(model_attr='sigact', faceted=True)
    affiliation = indexes.CharField(model_attr='affiliation', faceted=True)
    dcolor = indexes.CharField(model_attr='dcolor', faceted=True)
    classification = indexes.CharField(model_attr='classification', faceted=True)
    total_casualties = indexes.IntegerField(model_attr='total_casualties', faceted=True)

    def get_queryset(self):
        return DiaryEntry.objects.all()

site.register(DiaryEntry, DiaryEntryIndex)



