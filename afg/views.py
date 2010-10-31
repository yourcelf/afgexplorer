import re
import json
import urllib
import random
import datetime
from collections import defaultdict

from django.http import Http404
from django.utils.safestring import mark_safe
from django.db import connection
from django.core import paginator
from django.core.urlresolvers import reverse

from haystack.query import SearchQuerySet
from haystack.utils import Highlighter
import haystack

from afg.models import DiaryEntry
from afg.search_indexes import DiaryEntryIndex
from afg import utils

def about(request):
    return utils.render_request(request, "about.html")

def show_entry(request, rid, template='afg/entry_page.html', api=False):
    try:
        entry = DiaryEntry.objects.get(report_key=rid)
    except DiaryEntry.DoesNotExist:
        raise Http404

    if api:
        return utils.render_json(request, {
                'entry': entry.to_dict(),
            })

    return utils.render_request(request, template, {
        'entry': entry,
    })

def entry_popup(request):
    try:
        rids = [r for r in request.GET.get('rids').split(',')]
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
    report_key = DiaryEntry.objects.all().values(
            'report_key').order_by()[random.randint(0, count)]['report_key']
    return utils.redirect_to("afg.show_entry", report_key)

def _excerpt(text, needles):
    if not needles:
        i = 200
        while i < len(text) and text[i] != " ":
            i += 1
        return text[0:i] + "..."

    text = re.sub("\s+", " ", text)
    words = [re.sub("[^-A-Z0-9 ]", "", needle.upper()) for needle in needles]
    locations = defaultdict(list)
    for word in words:
        for match in re.finditer(word, text, re.I):
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
            snipped.append((text[n:loc], 0))
            snipped.append((text[loc:loc+len(word)], 1))
            n = loc + len(word)
        snipped.append((text[n:], 0))
        out = []
        for i, (snip, bold) in enumerate(snipped):
            if bold:
                out.append("<em>")
                out.append(snip)
                out.append("</em>")
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
        return text[0:200]


def api(request):
    return utils.render_request(request, "afg/api.html")

def search(request, about=False, api=False):
    sqs = SearchQuerySet()
    params = {}

    # Full text search
    q = request.GET.get('q', None)
    if q:
        sqs = sqs.auto_query(q).highlight()
        params['q'] = q

    # prepare fields for faceting; dates are special-cased later.
    summary = None
    date_fields = {}
    for facet in DiaryEntryIndex.search_facet_display:
        field = DiaryEntryIndex.fields[facet]
        if isinstance(field, haystack.fields.DateTimeField):
            date_fields[facet] = field
        else:
            sqs = sqs.facet(facet)
    # XXX: Set field-specific range limit for total casualties
    sqs = sqs.raw_params(**{'f.total_casualties_exact.facet.limit': 200})

    # Narrow query set by given facets
    for key,val in request.GET.iteritems():
        if val:
            # Add an "exact" param and split by '__'.  If the field already has
            # e.g. __gte, the __exact addendum is ignored, since we only look
            # at the first two parts.
            field_name, lookup = (key + "__exact").rsplit(r'__')[0:2]
            # "type" is a reserved name for Solr, so munge it to "type_"
            if field_name == "type":
                field_name = "type_"
            field = DiaryEntryIndex.fields.get(field_name, None)
            if field and field.faceted:
                # Dates are handled specially below
                if isinstance(field, haystack.fields.DateTimeField):
                    continue
                elif isinstance(field, haystack.fields.IntegerField):
                    try:
                        clean_val = int(val)
                    except ValueError:
                        continue
                elif isinstance(field, haystack.fields.FloatField):
                    try:
                        clean_val = float(val)
                    except ValueError:
                        continue
                else:
                    clean_val = sqs.query.clean(val)
                if lookup == 'exact':
                    sqs = sqs.narrow(u'%s:"%s"' % (field.index_fieldname + "_exact", clean_val))
                elif lookup == 'gte':
                    sqs = sqs.narrow(u"%s:[%s TO *]" % (field.index_fieldname, clean_val))
                elif lookup == 'lte':
                    sqs = sqs.narrow(u"%s:[* TO %s]" % (field.index_fieldname, clean_val))
                else:
                    continue
                params[key] = val

    # Narrow query set by given date facets
    for key, field in date_fields.iteritems():
        start_str = request.GET.get(key + '__gte', '')
        end_str = request.GET.get(key + '__lte', '')
        start = None
        end = None
        if start_str:
            try:
                start = datetime.datetime(*[int(a) for a in (start_str + '-1-1').split('-')[0:3]])
            except ValueError:
                start = None
        if end_str:
            try:
                end = datetime.datetime(*[int(a) for a in ((end_str + '-1-1').split('-')[0:3])])
            except ValueError:
                end = None
        if not start and not end:
            # Legacy (deprecated) date format -- here to preserve old URLs
            day = int(request.GET.get(key + '__day', 0))
            month = int(request.GET.get(key + '__month', 0))
            year = int(request.GET.get(key + '__year', 0))
            if year:
                if month:
                    if day:
                        start = datetime.datetime(year, month, day)
                        end = start + datetime.timedelta(days=1)
                    else:
                        start = datetime.datetime(year, month, 1)
                        next_month = start + datetime.timedelta(days=31)
                        end = datetime.datetime(next_month.year, next_month.month, 1)
                else:
                    start = datetime.datetime(year, 1, 1)
                    end = datetime.datetime(year + 1, 1, 1)
        if start:
            sqs = sqs.narrow("%s:[%s TO *]" % (key, start.isoformat() + 'Z'))
            params[key + '__gte'] = start.strftime("%Y-%m-%d")
        else:
            start = DiaryEntryIndex.min_date
        if end:
            sqs = sqs.narrow("%s:[* TO %s]" % (key, end.isoformat() + 'Z'))
            params[key + '__lte'] = end.strftime("%Y-%m-%d")
        else:
            end = DiaryEntryIndex.max_date

        span = max(1, (end - start).days)
        gap = max(1, int(span / 100)) # target 100 facets
        sqs = sqs.date_facet(key, start, end, 'day', gap)

    # sorting
    sort = request.GET.get('sort', '')
    # Legacy sorting
    if request.GET.get('sort_by', ''):
        sort_by = request.GET.get('sort_by', '')
        if sort_by == 'casualties':
            sort_by = 'total_casualties'
        sort_dir = request.GET.get('sort_dir', 'asc')
        direction_indicator = '-' if sort_dir == 'desc' else ''
        sort = direction_indicator + sort_by
    if sort.strip('-') not in DiaryEntryIndex.fields:
        sort = DiaryEntryIndex.offer_to_sort_by[0][1]
    sqs = sqs.order_by(sort)
    params['sort'] = sort

    # Pagination
    p = paginator.Paginator(sqs, 10)
    try:
        page = p.page(int(request.GET.get('p', 1)))
    except (ValueError, paginator.InvalidPage, paginator.EmptyPage):
        page = p.page(p.num_pages)

    # Results Summaries and highlighting
    entries = []
    for entry in page.object_list:
        if entry.highlighted:
            excerpt = mark_safe(u"... %s ..." % entry.highlighted['text'][0])
        else:
            excerpt = (entry.summary or '')[0:200] + "..."
        entries.append((entry, excerpt))

    # Choices
    counts = sqs.facet_counts()
    choices = utils.OrderedDict()
    for key in DiaryEntryIndex.search_facet_display:
        field = DiaryEntryIndex.fields[key]
        choice = None
        if isinstance(field, haystack.fields.CharField):
            facets = sorted((k, k, c) for k, c in counts['fields'][key] if c > 0)
            if facets:
                choice = {
                    'choices': facets,
                    'type': 'text',
                    'value': params.get(key, ''),
                }
        elif isinstance(field, haystack.fields.IntegerField):
            # Integer choices
            facets = sorted([(int(k), c) for k,c in counts['fields'][key] if c > 0])
            if facets:
                choice = {
                    'type': 'min_max',
                    'counts': [c for k,c in facets],
                    'vals': [k for k,c in facets],
                    'min_value': facets[0][0],
                    'max_value': facets[-1][0],
                    'chosen_min': params.get(key + '__gte', ''),
                    'chosen_max': params.get(key + '__lte', ''),
                }
        elif isinstance(field, haystack.fields.DateTimeField):
            facets = sorted(counts['dates'].get(key, {}).iteritems())
            if facets:
                val_counts = []
                vals = []
                last_dt = None
                for d,c in facets:
                    if c > 0:
                        try:
                            last_dt = _iso_to_datetime(d)
                            val_counts.append(c)
                            vals.append(last_dt.strftime('%Y-%m-%d'))
                        except (TypeError, ValueError):
                            pass
                if vals and last_dt:
                    max_value = min(
                        _iso_to_datetime(counts['dates'][key]['end']),
                        DiaryEntryIndex.max_date,
                        last_dt + datetime.timedelta(
                            days=int(re.sub('[^\d]', '', counts['dates'][key]['gap']))
                        )
                    )
                    vals.append(max_value.strftime('%Y-%m-%d'))
                    val_counts.append(0)
                    choice = {
                        'type': 'date',
                        'counts': val_counts,
                        'vals': vals,
                        'min_value': vals[0],
                        'max_value': vals[-1],
                        'chosen_min': params.get(key + '__gte', ''),
                        'chosen_max': params.get(key + '__lte', ''),
                    }
        if choice:
            choice['title'] = fix_constraint_name(key)
            choices[key] = choice

    search_url = reverse('afg.search')

    # Links to remove constraints
    constraints = {}
    exclude = set(('sort',))
    for key in params.keys():
        if key not in exclude:
            value = params.pop(key)
            constraints[key] = {
                'value': value,
                'removelink': "%s?%s" % (search_url, urllib.urlencode(params)),
                'title': fix_constraint_name(key)
            }
            params[key] = value

    # Links to change sorting
    sort_links = []
    current_sort = params.pop('sort')
    current_key = sort.strip('-')
    for display, new_key in DiaryEntryIndex.offer_to_sort_by:
        # Change directions only if it's the same sort key
        if current_key == new_key:
            direction = '' if current_sort[0] == '-' else '-'
        else:
            direction = '-' if current_sort[0] == '-' else ''
        params['sort'] = direction + new_key
        sort_links.append({
            'link': "%s?%s" % (search_url, urllib.urlencode(params)), 
            'title': display, 
            'desc': current_sort[0] == '-',
            'current': current_key == new_key,
        })
    params['sort'] = current_sort

    if api:
        remapped_choices = {}
        for choice, opts in choices.iteritems():
            if opts['type'] in ('min_max', 'date'):
                remapped_choices[choice] = opts
            else:
                remapped_choices[choice] = {
                    'value': opts['value'],
                    'title': opts['title'],
                    'choices': [],
                }
                for disp, val, count in opts['choices']:
                    if disp or val:
                        remapped_choices[choice]['choices'].append({
                                'value': val,
                                'display': disp,
                                'count': count,
                        })

        return utils.render_json(request, {
            'pagination': {
                'p': page.number,
                'num_pages': page.paginator.num_pages,
                'num_results': page.paginator.count,
            },
            'entries': [{
                    'title': e.title,
                    'date': e.date.isoformat(),
                    'release': e.release,
                    'region': e.region,
                    'report_key': e.report_key,
                    'excerpt': x,
                    'total_casualties': e.total_casualties,
                 } for (e,x) in entries],
            'choices': remapped_choices,
            'sort': params['sort'],
            'params': params,
        })

    return utils.render_request(request, "afg/search.html", {'page': page,
        'about': about,
        'entries': entries,
        'params': request.GET,
        'choices': choices,
        'qstring': '%s?%s' % (search_url, urllib.urlencode(params)),
        'constraints': constraints,
        'sort_links': sort_links,
    })

def _iso_to_datetime(iso_date_str):
    return datetime.datetime(*map(int, re.split('[^\d]', iso_date_str)[:-1]))

def fix_constraint_name(name):
    name = name.replace('_', ' ')
    name = name.replace('wia', 'wounded')
    name = name.replace('kia', 'killed')
    name = name.replace('gte', ' - more than')
    name = name.replace('lte', ' - less than')
    name = name.replace('icontains', 'contains')
    return name[0].upper() + name[1:]
