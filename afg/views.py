import re
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

from afg.models import DiaryEntry, Phrase
from afg.search_indexes import DiaryEntryIndex
from afg import utils

def about(request):
    return utils.render_request(request, "about.html")

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
# Equivalent query without denormalization:
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

    # Narrow query set by given facets
    for key,val in request.GET.iteritems():
        if val:
            # Add an "exact" param and split by '__'.  If the field already has
            # e.g. __gte, the __exact addendum is ignored, since we only look
            # at the first two parts.
            field_name, lookup = (key + "__exact").rsplit(r'__')[0:2]
            # "type" is a reserved name for Solr, so munge it to "type_"
            field_name = "type_" if field_name == "type" else field_name
            field = DiaryEntryIndex.fields.get(field_name, None)
            if field and field.faceted:
                # Dates are handled specially below
                if isinstance(field, haystack.fields.DateTimeField):
                    continue
                elif isinstance(field, haystack.fields.IntegerField):
                    try:
                        val = int(val)
                    except ValueError:
                        continue
                elif isinstance(field, haystack.fields.FloatField):
                    try:
                        val = float(val)
                    except ValueError:
                        continue
                else:
                    val = sqs.query.clean(val)
                if lookup == 'exact':
                    sqs = sqs.narrow(u'%s:"%s"' % (field.index_fieldname, val))
                elif lookup == 'gte':
                    sqs = sqs.narrow(u"%s:[%s TO *]" % (field.index_fieldname, val))
                elif lookup == 'lte':
                    sqs = sqs.narrow(u"%s:[* TO %s]" % (field.index_fieldname, val))
                else:
                    continue
                params[key] = val

    # Narrow query set by given date facets
    for key, field in date_fields.iteritems():
        date = request.GET.get(key, '')
        if date:
            try:
                year, month, day = [int(d) for d in (date + "-0-0").split("-")[0:3]]
                if year > 3000 or month > 12 or day > 31:
                    raise ValueError
            except ValueError:
                year, month, day = 0, 0, 0
        else:
            # Legacy date format 
            day = int(request.GET.get(key + '__day', 0))
            month = int(request.GET.get(key + '__month', 0))
            year = int(request.GET.get(key + '__year', 0))
        if year:
            if not month:
                start = datetime.datetime(year, 1, 1)
                end = datetime.datetime(year + 1, 1, 1) - datetime.timedelta(seconds=1)
                params[key] = start.strftime("%Y")
                sqs = sqs.date_facet(key, start, end, 'month')
            elif not day:
                start = datetime.datetime(year, month, 1)
                next_month = datetime.datetime(year, month, 1) + datetime.timedelta(days=31)
                end = datetime.datetime(next_month.year, next_month.month, 1) - datetime.timedelta(seconds=1)
                params[key] = start.strftime("%Y-%m")
                sqs = sqs.date_facet(key, start, end, 'day')
            else:
                start = datetime.datetime(year, month, day)
                end = datetime.datetime(year, month, day + 1) - datetime.timedelta(seconds=1)
                params[key] = start.strftime("%Y-%m-%d")
                sqs = sqs.date_facet('date', start, end, 'day')
            sqs = sqs.narrow("%s:[%s TO %s]" % (key, start.isoformat() + "Z", end.isoformat() + "Z"))
        else:
            start = DiaryEntryIndex.min_date
            end = DiaryEntryIndex.max_date
            sqs = sqs.date_facet(key, start, end, 'year')

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
    total_count = sqs.count()
    counts = sqs.facet_counts()
    choices = utils.OrderedDict()
    for key in DiaryEntryIndex.search_facet_display:
        field = DiaryEntryIndex.fields[key]
        choice = {
            'title': fix_constraint_name(key),
            'value': params.get(key, '')
        }
        if isinstance(field, haystack.fields.CharField):
            choice['choices'] = sorted((k, k, c) for k, c in counts['fields'][key] if c > 0)
            choice['type'] = 'text'
        elif isinstance(field, haystack.fields.DateTimeField):
            choice['type'] = 'date'
            date_facets = []
            for d,c in sorted(counts['dates'][key].iteritems()):
                try:
                    # magic method to parse ISO date format.
                    dt = datetime.datetime(*map(int, re.split('[^\d]', d)[:-1]))
                    if c > 0:
                        date_facets.append((dt, c))
                except (TypeError, ValueError):
                    pass

            year, month, day = (params.get(key, '') + "--").split("-")[0:3]
            if year:
                if month:
                    if day: 
                        d = datetime.date(int(year), int(month), int(day))
                        choice['choices'] = [(d.strftime("%Y %B %e"), d.strftime("%Y-%m-%d"), total_count)]
                    else:
                        choice['choices'] = [(d.strftime("%B %e"), d.strftime("%Y-%m-%d"), c) for d, c in date_facets]
                else:
                    choice['choices'] = [(d.strftime("%B"), d.strftime("%Y-%m"), c) for d, c in date_facets]
            else:
                choice['choices'] = [(d.year, d.year, c) for d, c in date_facets]
        elif isinstance(field, haystack.fields.IntegerField):
            # Integer choices
            facets = sorted([(int(k), v) for k,v in counts['fields'][key] if v > 0])
            if facets:
                choice.update({
                    'type': 'min_max',
                    'counts': [v for k,v in facets],
                    'vals': [k for k,v in facets],
                    'min_value': facets[0][0],
                    'max_value': facets[-1][0],
                    'chosen_min': params.get(key + '__gte', ''),
                    'chosen_max': params.get(key + '__lte', ''),
                })
        choices[key] = choice

    search_url = reverse('afg.search')

    # Links to remove constraints
    constraints = {}
    exclude = set(('sort',))
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
            if opts['type'] == 'min_max':
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
                    'report_key': e.report_key,
                    'excerpt': x
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

def fix_constraint_name(field):
    field = field.replace('_', ' ')
    field = field.replace('wia', 'wounded')
    field = field.replace('kia', 'killed')
    field = field.replace('gte', ' - more than')
    field = field.replace('lte', ' - less than')
    field = field.replace('icontains', 'contains')
    return field[0].upper() + field[1:]
