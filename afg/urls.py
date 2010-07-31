from django.conf.urls.defaults import *

from afg import utils

rid = "(?P<rid>[-A-Za-z0-9]+)"

urlpatterns = patterns('afg.views',
    url(r'about/$', lambda r: utils.redirect_to('/')),
    url(r'entry_popup/$', 'entry_popup', name='afg.entry_popup'),
    url(r'search/$', 'search', name='afg.search'),
    url(r'random/$', 'random_entry', name='afg.random_entry'),
    url(r'^id/%s/$' % rid, 'show_entry',
        {'template': 'afg/entry_page.html'}, 
        name='afg.show_entry'),
    url(r'^id/%s\.stub$' % rid, 'show_entry', 
        {'template': 'afg/entry.html'}, 
        name='afg.show_entry_stub'),
    url(r'^$', 'search', {'about': True}, name='afg.about'),
)
