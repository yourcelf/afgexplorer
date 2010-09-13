from django.contrib import admin

from afg.models import DiaryEntry

class DiaryAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'category', 'host_nation_wia', 'host_nation_kia', 'civilian_wia', 'civilian_kia', 'enemy_wia', 'enemy_kia', 'friendly_wia', 'friendly_kia')
    list_filter = ('type', 'region', 'attack_on', 'category', 'complex_attack')
    search_fields = ('title', 'summary')
    date_hierarchy = 'date'
admin.site.register(DiaryEntry, DiaryAdmin)
