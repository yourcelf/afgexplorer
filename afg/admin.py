from django.contrib import admin

from afg import models

class DiaryAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'category', 'host_nation_wia', 'host_nation_kia', 'civilian_wia', 'civilian_kia', 'enemy_wia', 'enemy_kia', 'friendly_wia', 'friendly_kia')
    list_filter = ('type', 'region', 'attack_on', 'category', 'complex_attack')
    search_fields = ('title', 'summary')
    date_hierarchy = 'date'
admin.site.register(models.DiaryEntry, DiaryAdmin)

class PhraseAdmin(admin.ModelAdmin):
    filter_horizontal = ('entries',)
admin.site.register(models.Phrase, PhraseAdmin)
