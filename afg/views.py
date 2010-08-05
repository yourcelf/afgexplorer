import re
import urllib
import random
from collections import defaultdict

from django.http import Http404
from django.utils.safestring import mark_safe
from django.db import connection
from django.core import paginator
from django.core.urlresolvers import reverse
from jimmypage.cache import cache_page

from afg.models import DiaryEntry, Phrase
from afg import utils

@cache_page
def about(request):
    return utils.render_request(request, "about.html")

@cache_page
def show_entry(request, rid, template='afg/entry_page.html', api=False):
    try:
        entry = DiaryEntry.objects.get(report_key=rid)
    except DiaryEntry.DoesNotExist:
        try:
            entry = DiaryEntry.objects.get(id=int(rid))
        except (ValueError, DiaryEntry.DoesNotExist):
            raise Http404

    phrases = Phrase.objects.filter(entry_count__gt=1, 
            entry_count__lt=10, entries=entry)
# Equivalent query pre-de-normalization:
#    phrases = list(Phrase.objects.raw("""
#            SELECT sub.* FROM
#                (SELECT p.id, p.phrase, COUNT(pe2.diaryentry_id) AS entry_count FROM 
#                afg_phrase_entries pe2, afg_phrase p 
#                INNER JOIN afg_phrase_entries pe1 ON pe1.phrase_id = p.id  
#                WHERE pe1.diaryentry_id=%s AND p.id=pe2.phrase_id
#                GROUP BY p.phrase, p.id) AS sub
#            WHERE entry_count > 1 AND entry_count < 10;
#        """, [entry.id]))

    phrase_ids = [p.id for p in phrases]

    dest_ids = defaultdict(list)
    if phrase_ids:
        cursor = connection.cursor()
        # Using modulus not params here because we need to do funky literalizing of
        # the table
        cursor.execute("""
            SELECT pe.phrase_id, d.id FROM afg_phrase_entries pe 
            INNER JOIN afg_diaryentry d ON pe.diaryentry_id=d.id
            WHERE pe.phrase_id IN (SELECT * FROM (VALUES %s) AS phrase_id_set);
            """ % (",".join("(%s)" % i for i in phrase_ids)))
        for row in cursor.fetchall():
            dest_ids[int(row[0])].append(row[1])

    phrase_entries = [(phrase, dest_ids[phrase.id]) for phrase in phrases]

    if api:
        return utils.render_json(request, {
                'entry': entry.to_dict(),
                'phrase_entries': [{
                        'phrase': p.phrase, 
                        'entry_ids': ids,
                     } for p, ids in phrase_entries],
            })

    return utils.render_request(request, template, {
        'entry': entry,
        'phrase_entries': phrase_entries,
    })

@cache_page
def entry_popup(request):
    try:
        rids = [int(r) for r in request.GET.get('rids').split(',')]
        clicked = request.GET.get('clicked')
        join_to = request.GET.get('entry')
        texts = [urllib.unquote(t) for t in request.GET.get('texts').split(',')]
    except (KeyError, ValueError):
        raise Http404

    text_mapping = dict(zip(rids, texts))
    entries_mapping = DiaryEntry.objects.in_bulk(rids)
    entries = []
    texts = []
    for k in entries_mapping.keys():
        entries.append(entries_mapping[k])
        texts.append(text_mapping[k])

    return utils.render_request(request, "afg/entry_table.html", { 
        'entries': [(entry, _excerpt(entry.summary, [text])) for entry,text in zip(entries, texts)]
    })

def random_entry(request):
    count = DiaryEntry.objects.count()
    report_key = DiaryEntry.objects.all()[random.randint(0, count)].report_key
    return utils.redirect_to("afg.show_entry", report_key)

def _fix_amps(haystack):
    amps = re.compile("&amp;", re.I)
    while True:
        fixed = amps.sub("&", haystack)
        if fixed == haystack:
            break
        haystack = fixed
    return re.sub("&(?![A-Za-z0-9#]+;)", "&amp;", haystack)

def _excerpt(haystack, needles):
    if not needles:
        i = 200
        while i < len(haystack) and haystack[i] != " ":
            i += 1
        return haystack[0:i] + "..."

    haystack = re.sub("\s+", " ", haystack)
    haystack = _fix_amps(haystack)
    words = [re.sub("[^-A-Z0-9 ]", "", needle.upper()) for needle in needles]
    locations = defaultdict(list)
    for word in words:
        for match in re.finditer(word, haystack, re.I):
            locations[word].append(match.start())

    winner = {}
    min_dist = 1000000000
    for word1, locs1 in locations.iteritems():
        for loc1 in locs1:
            best_locs = {}
            for word2, locs2 in locations.iteritems():
                if word2 == word1:
                    continue
                loc1_loc2_dist = 1000000000
                best_word2_loc = None
                for loc2 in locs2:
                    dist = abs(loc2 - loc1)
                    # avoid overlapping words
                    if loc2 > loc1 and loc1 + len(word1) > loc2:
                        continue
                    if loc2 < loc1 and loc2 + len(word2) > loc1:
                        continue
                    if dist < loc1_loc2_dist:
                        loc1_loc2_dist = dist
                        best_word2_loc = loc2
                    else:
                        break
                best_locs[best_word2_loc] = word2
            distance = sum(best_locs.keys())
            if distance < min_dist:
                best_locs[loc1] = word1
                winner = best_locs
                min_dist = distance

    snipped = []
    if winner:
        snips = sorted(winner.items())
        n = 0
        for loc, word in snips:
            snipped.append((haystack[n:loc], 0))
            snipped.append((haystack[loc:loc+len(word)], 1))
            n = loc + len(word)
        snipped.append((haystack[n:], 0))
        out = []
        for i, (snip, bold) in enumerate(snipped):
            if bold:
                out.append("<b>")
                out.append(snip)
                out.append("</b>")
            else:
                if len(snip) > 100:
                    if i != 0:
                        out.append(snip[0:50])
                    out.append(" ... ")
                    if i != len(snipped) - 1:
                        out.append(snip[-50:])
                else:
                    out.append(snip)
        return mark_safe("".join(out))
    else:
        return haystack[0:200]


@cache_page
def api(request):
    return utils.render_request(request, "afg/api.html")

SEARCH_PARAMS = {
    'q': ('q', unicode),
    'date__day': ('date__day', int),
    'date__year': ('date__year', int),
    'date__month': ('date__month', int),
    'category': ('category', unicode),
    'type': ('type', unicode),
    'region': ('region', unicode),
    'attack_on': ('attack_on', unicode),
    'complex_attack': ('complex_attack', lambda e: "yes" if e else "no"),
    'unit_name': ('unit_name', unicode),
    'type_of_unit': ('type_of_unit', unicode),
    'reporting_unit': ('reporting_unit', unicode),
    'friendly_wia__gte': ('friendly_wia__gte', int),
    'friendly_wia__lte': ('friendly_wia__lte', int),
    'host_nation_wia__gte': ('host_nation_wia__gte', int),
    'host_nation_wia__lte': ('host_nation_wia__lte', int),
    'civilian_wia__gte': ('civilian_wia__gte', int),
    'civilian_wia__lte': ('civilian_wia__lte', int),
    'enemy_wia__gte': ('enemy_wia__gte', int),
    'enemy_wia__lte': ('enemy_wia__lte', int),
    'friendly_kia__gte': ('friendly_kia__gte', int),
    'friendly_kia__lte': ('friendly_kia__lte', int),
    'host_nation_kia__gte': ('host_nation_kia__gte', int),
    'host_nation_kia__lte': ('host_nation_kia__lte', int),
    'civilian_kia__gte': ('civilian_kia__gte', int),
    'civilian_kia__lte': ('civilian_kia__lte', int),
    'enemy_kia__gte': ('enemy_kia__gte', int),
    'enemy_kia__lte': ('enemy_kia__lte', int),
    'enemy_detained__gte': ('enemy_detained__gte', int),
    'enemy_detained__lte': ('enemy_detained__lte', int),
    'mgrs': ('mgrs', unicode),
    'originator_group': ('originator_group', unicode),
    'updated_by_group': ('updated_by_group', unicode),
    'affiliation': ('affiliation', unicode),
    'dcolor': ('dcolor', unicode),
    'classification': ('classification', unicode),
}

@cache_page
def search(request, about=False, api=False):
    params = {}
    for key in request.GET:
        trans = SEARCH_PARAMS.get(key, None)
        if trans and request.GET[key]:
            try:
                params[trans[0]] = trans[1](request.GET[key])
            except ValueError:
                continue

    # sorting
    sort_by = request.GET.get('sort_by', 'date')
    sort_dir = request.GET.get('sort_dir', 'asc')
    # special handling of full text search
    q = params.pop('q', None)
    if q:
        qs = DiaryEntry.objects.extra(where=['summary_tsv @@ plainto_tsquery(%s)'], params=[q])
    else:
        qs = DiaryEntry.objects.all()
    qs = qs.filter(**params)
    direction_indicator = '-' if sort_dir == 'desc' else ''
    if sort_by in ('date', 'total_casualties'):
        qs = qs.order_by(direction_indicator + sort_by)

    # Restore params now that we've finished filtering on the non-model elements
    if q:
        params['q'] = q
    params['sort_by'] = sort_by
    params['sort_dir'] = sort_dir


    p = paginator.Paginator(qs, 10)
    try:
        page = p.page(int(request.GET.get('p', 1)))
    except (ValueError, paginator.InvalidPage, paginator.EmptyPage):
        page = p.page(p.num_pages)

    if q:
        needles = q.split()
    else:
        needles = None
    entries = [(entry, _excerpt(entry.summary, needles)) for entry in page.object_list]

    choices = utils.OrderedDict()

    # Date choices
    choices['date__year'] = {
            'title': 'Year',
            'choices': [(d.year, d.year) for d in qs.dates('date', 'year')],
            'value': params.get('date__year', ''),
    }
    if 'date__year' in params or 'date__month' in params:
        choices['date__month'] = {
                'title': 'Month',
                'choices': sorted(set((d.strftime("%B"), d.month) for d in qs.dates('date', 'month'))),
                'value': params.get('date__month', ''),
        }
    if ('date__year' in params and 'date__month' in params) or 'date__day' in params:
        choices['date__day'] = {
                'title': 'Day',
                'choices': [(d.day, d.day) for d in qs.dates('date', 'day')],
                'value': params.get('date__day', ''),
        }

    # General field choices
    for field in ('type', 'region', 'attack_on', 'type_of_unit', 
            'affiliation', 'dcolor', 'classification', 'category'):
        cs = list(q.values()[0] for q in qs.distinct().order_by(field).values(field))
        choices[field] = {
            'title': field.replace('_', ' ').title(), 
            'choices': zip(cs, cs),
            'value': params.get(field, ''),
        }

    min_max_choices = utils.OrderedDict()
    # Integer choices
    for field in ('total_casualties', 'civilian_kia', 'civilian_wia', 'host_nation_kia', 'host_nation_wia', 'friendly_kia', 'friendly_wia', 'enemy_kia', 'enemy_wia', 'enemy_detained'):
        try:
            minimum = qs.order_by(field).values(field)[0][field]
            maximum = qs.order_by("-%s" % field).values(field)[0][field]
        except IndexError:
            continue
        if minimum == maximum and \
                not params.get(field + '__gte') and \
                not params.get(field + '__lte'):
            continue
        min_max_choices[field] = {
                'min': minimum,
                'max': maximum,
                'title': fix_constraint_name(field),
                'min_value': params.get(field + '__gte', ''),
                'max_value': params.get(field + '__lte', ''),
        }

    search_url = reverse('afg.search')

    # Links to remove constraints
    constraints = {}
    exclude = set(('sort_by', 'sort_dir'))
    for field in params.keys():
        if field not in exclude:
            value = params.pop(field)
            constraints[field] = {
                'value': value,
                'removelink': "%s?%s" % (search_url, urllib.urlencode(params)),
                'title': fix_constraint_name(field)
            }
            params[field] = value

    # Links to change sorting
    sort = {}
    for by in ('date', 'total_casualties'):
        sort_by = params.pop('sort_by', 'date')
        sort_dir = params.pop('sort_dir', 'asc')
        params['sort_by'] = by
        if sort_by == by:
            if sort_dir == 'asc':
                params['sort_dir'] = 'desc' 
                sort[by + '_asc'] = True
            else:
                sort[by + '_desc'] = True
        else:
            params['sort_dir'] = sort_dir
        sort[by] = "%s?%s" % (search_url, urllib.urlencode(params))
        params['sort_by'] = sort_by
        params['sort_dir'] = sort_dir

    if api:
        remapped_choices = {}
        for choice, opts in choices.iteritems():
            remapped_choices[choice] = {
                'value': opts['value'],
                'title': opts['title'],
                'choices': []
            }
            for disp, val in opts['choices']:
                if disp or val:
                    remapped_choices[choice]['choices'].append({
                            'value': val,
                            'display': disp,
                    })

        return utils.render_json(request, {
            'pageination': {
                'p': page.number,
                'num_pages': page.paginator.num_pages,
                'num_results': page.paginator.count,
            },
            'entries': [{
                    'report_key': e.report_key,
                    'excerpt': x
                 } for (e,x) in entries],
            'choices': remapped_choices,
            'min_max_choices': min_max_choices,
            'sort': {
                'sort_by': params['sort_by'],
                'sort_dir': params['sort_dir'],
            },
            'params': params,
        })

    return utils.render_request(request, "afg/search.html", {'page': page,
        'about': about,
        'entries': entries,
        'params': request.GET,
        'choices': choices,
        'min_max_choices': min_max_choices,
        'qstring': '%s?%s' % (search_url, urllib.urlencode(params)),
        'constraints': constraints,
        'sort': sort,
    })

def fix_constraint_name(field):
    field = field.replace('_', ' ')
    field = field.replace('wia', 'wounded')
    field = field.replace('kia', 'killed')
    field = field.replace('gte', ' - more than')
    field = field.replace('lte', ' - less than')
    field = field.replace('icontains', 'contains')
    return field[0].upper() + field[1:]
