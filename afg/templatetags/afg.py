from django import template

register = template.Library()

@register.filter
def casualty_summary(entry):
    parts = []
    for attr in ('civilian', 'host_nation', 'friendly', 'enemy'):
        k = getattr(entry, attr + '_kia')
        w = getattr(entry, attr + '_wia')
        if k or w:
            counts = []
            if k:
                counts.append("%i killed" % k)
            if w:
                counts.append("%i wounded" % w)
            parts.append("%s: %s" % (attr.title().replace("_", " "), ", ".join(counts)))
    return "; ".join(parts)
