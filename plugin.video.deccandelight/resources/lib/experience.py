"""Home, personal collections, diagnostics and one-click playback."""
import os
import time
from six.moves import urllib_parse

from resources.lib import cache, client, control, parallel, streams
from resources.lib.collection import Collection

GROUPS = {
    'movies': ['tgun', 'tyogi', 'hlinks', 'moviehax', 'einthusan', 'mrulz', 'wompk',
               'gomovies', 'todaypk', 'flinks', 'dcine', 'hflinks'],
    'shows': ['desiseri', 'desit', 'pdesi', 'yodesi', 'ary', 'geo', 'hum'],
    'music': ['gmala'],
}


def application():
    from resources.lib import deccandelight
    return deccandelight


def database():
    return Collection(os.path.join(control.TRANSLATEPATH(control._ppath), 'collections.db'))


def route(action, **values):
    return control._url + '?' + urllib_parse.urlencode(dict(values, action=action))


def setting_int(name, default, low, high):
    try:
        return max(low, min(high, int(control.get_setting(name))))
    except (ValueError, TypeError):
        return default


def art(name):
    return control._ipath + 'hub-' + name + '.png'


def row(title, url, image, plot='', folder=True):
    app = application()
    item = app.make_listitem(label=title)
    item.setArt({'thumb': image, 'icon': image, 'poster': image, 'fanart': control._fanart})
    app.update_listitem(item, {'title': title, 'plot': plot, 'mediatype': 'video'})
    return url, item, folder


def finish(rows, content='movies'):
    control.addDir(control._handle, rows, len(rows))
    control.setContent(control._handle, content)
    control.eod(control._handle)


def home():
    tiles = [
        ('Search everything', 13, 'search', 'One search across your enabled movie and television sources.', {}),
        ('Movies', 15, 'movies', 'Tamil, Telugu, Hindi and more. Choose a source and discover its latest films.', {'group': 'movies'}),
        ('TV & shows', 15, 'shows', 'Catch up on serials and official Urdu channel episodes.', {'group': 'shows'}),
        ('Music', 15, 'music', 'Browse Hindi songs by film, year or singer.', {'group': 'music'}),
        ('My watchlist', 16, 'watchlist', 'Titles you saved. Open their current servers whenever you are ready.', {'kind': 'watchlist'}),
        ('Recently opened', 16, 'recent', 'Return to titles you recently opened. Links are refreshed before playback.', {'kind': 'recent'}),
        ('Favorite sources', 15, 'favorites', 'Your favorite providers, gathered in one place.', {'group': 'favorites'}),
        ('All sources', 15, 'sources', 'Browse all enabled providers. Long-press a source to make it a favorite.', {'group': 'all'}),
        ('Settings & tools', 20, 'tools', 'Playback preferences, source availability and cache controls.', {}),
    ]
    finish([row(title, route(action, **values), art(image), plot) for title, action, image, plot, values in tiles])


def enabled_sources():
    return [site[2:] for site in sorted(application().sites) if control.get_setting(site[2:]) == 'true']


def source_list(group='all'):
    app = application()
    enabled = enabled_sources()
    favorites = {item['site'] for item in database().items('favorites')}
    selected = (sorted(favorites) if group == 'favorites' else GROUPS.get(group, enabled))
    status = {item['site']: item for item in database().items('health')}
    rows = []
    for site in selected:
        if site not in enabled:
            continue
        name = app.sitenames.get(site, site)
        unavailable = status.get(site, {}).get('available') is False and time.time() - status[site]['updated'] < 1800
        title = name + (' [COLOR grey]• unavailable[/COLOR]' if unavailable else '')
        plot = 'Browse ' + name + '. Long-press for favorite and refresh actions.'
        url = route(22, site=site) if unavailable else route(1, site=site)
        entry = row(title, url, control._ipath + site + '.png', plot)
        entry[1].addContextMenuItems([
            ('Remove favorite' if site in favorites else 'Favorite this source', 'RunPlugin(' + route(19, site=site) + ')'),
            ('Retry and refresh', 'RunPlugin(' + route(23, site=site) + ')'),
        ])
        rows.append(entry)
    if not rows:
        control.notify('Long-press a source to add it to favorites.' if group == 'favorites' else 'Enable sources in Settings.')
    finish(rows)


def record(site, title, thumb, url, mode):
    return {'site': site, 'title': title, 'thumb': thumb or control._icon, 'url': url, 'mode': int(mode)}


def title_row(site, title, thumb, url, mode, collection=None, key=None):
    app = application()
    if 'MMMM' in url:
        url, mode = url.rsplit('MMMM', 1)
    mode = int(mode)
    automatic = mode == 8 and control.get_setting('autoplay') != 'false'
    target = route(14 if automatic else mode, site=site, title=title, thumb=thumb, iurl=url)
    item = app.make_listitem(label=title)
    item.setArt({'thumb': thumb or control._icon, 'icon': thumb or control._icon,
                 'poster': thumb or control._icon, 'fanart': control._fanart})
    app.update_listitem(item, {'title': title, 'plot': app.sitenames.get(site, site), 'mediatype': 'video'})
    if automatic or mode == 9:
        item.setProperty('IsPlayable', 'true')
    save = route(17, site=site, title=title, thumb=thumb, iurl=url, mode=mode)
    actions = [('Save to watchlist', 'RunPlugin(' + save + ')')]
    if collection == 'watchlist':
        actions[0] = ('Remove from watchlist', 'RunPlugin(' + route(18, kind='watchlist', key=key) + ')')
    if mode == 8:
        manual = route(8, site=site, title=title, thumb=thumb, iurl=url)
        actions.append(('Choose a server', 'Container.Update(' + manual + ')'))
        actions.append(('Play automatically', 'PlayMedia(' + route(14, site=site, title=title, thumb=thumb, iurl=url) + ')'))
    item.addContextMenuItems(actions)
    return target, item, not (automatic or mode == 9)


def list_collection(kind):
    if kind not in ('watchlist', 'recent'):
        return
    rows = []
    for item in database().items(kind):
        if item['site'] not in application().sitenames:
            continue
        rows.append(title_row(item['site'], item['title'], item['thumb'], item['url'], item['mode'], kind, item['id']))
    if not rows:
        control.notify('Save a title using its context menu.' if kind == 'watchlist' else 'Open a title to see it here.')
    finish(rows)


def change_collection(params):
    action = params['action']
    store = database()
    if action == '17':
        item = record(params['site'], params['title'], params.get('thumb', ''), params['iurl'], params.get('mode', 8))
        store.save('watchlist', item)
        control.notify('Saved to watchlist')
    elif action == '18':
        store.remove(params.get('kind', 'watchlist'), params['key'])
        control.xbmc.executebuiltin('Container.Refresh')
    elif action == '19':
        item = {'site': params['site'], 'url': ''}
        key = store.key(item)
        favorites = {value['id'] for value in store.items('favorites')}
        if key in favorites:
            store.remove('favorites', key)
            control.notify('Removed favorite')
        else:
            store.save('favorites', item)
            control.notify('Source added to favorites')
        control.xbmc.executebuiltin('Container.Refresh')


def tools():
    rows = [
        row('Playback & browsing settings', route(25), art('tools'), 'Choose automatic playback, quality preference and enabled sources.', False),
        row('Source availability', route(21), art('sources'), 'Check your enabled sources and retry unavailable providers.'),
        row('ResolveURL / TorBox settings', route(12), art('tools'), 'ResolveURL has its own resolver account settings, separate from Umbrella.', False),
        row('Refresh browsing cache', route(0), art('recent'), 'Fetch fresh menus, mirrors and titles. Your watchlist is preserved.', False),
        row('Refresh movie artwork', route(11), art('movies'), 'Clear cached movie metadata and artwork lookups.', False),
    ]
    finish(rows)


def availability():
    app = application()
    dialog = control.DialogProgress()
    dialog.create('Checking sources', 'Checking your enabled providers…')

    def check(site, deadline, stop):
        with client.request_budget(deadline, stop):
            try:
                scraper = app.scraper_for(site)
                menu, mode, _ = scraper.get_menu()
                choices = [(title, url) for title, url in sorted(menu.items()) if 'Search' not in title and 'Adult' not in title]
                if not choices:
                    return False
                _, url = choices[0]
                if 'MMMM' in url:
                    url, mode = url.rsplit('MMMM', 1)
                method = {4: 'get_top', 5: 'get_second', 6: 'get_third', 7: 'get_items'}.get(int(mode))
                if method:
                    items, _ = getattr(scraper, method)(url)
                    return bool(items)
                return bool(menu)
            except Exception:
                return False
    try:
        results, partial = parallel.collect(enabled_sources(), check, workers=5, seconds=30,
                                            cancelled=dialog.iscanceled,
                                            progress=lambda done, total: dialog.update(int(done * 100 / max(1, total)), '{} of {} sources checked'.format(done, total)))
    finally:
        dialog.close()
    store = database()
    for site, available in results:
        store.save('health', {'site': site, 'url': '', 'available': bool(available)})
    if partial:
        control.notify('Showing completed checks. Retry to check remaining sources.')
    health = {item['site']: item for item in store.items('health')}
    rows = []
    for site in enabled_sources():
        state = health.get(site, {})
        label = 'Available' if state.get('available') else ('Unavailable' if state else 'Not checked')
        rows.append(row(app.sitenames[site] + ' • ' + label, route(22, site=site), control._ipath + site + '.png',
                        'Availability on this network. Retry here when a provider changes.'))
    finish(rows)


def source_status(site):
    name = application().sitenames.get(site, site)
    choice = control.Dialog().select(name, ['Retry source now', 'Choose another source'])
    if choice == 0:
        refresh(site)
        control.xbmc.executebuiltin('Container.Update(' + route(1, site=site) + ')')
    elif choice == 1:
        control.xbmc.executebuiltin('Container.Update(' + route(15, group='all') + ')')


def refresh(site):
    scraper = application().scraper_for(site)
    cache.cache_clear()
    store = database()
    store.remove('health', store.key({'site': site, 'url': ''}))
    control.xbmc.executebuiltin('Container.Refresh')


def smart_play(site, title, url, thumb):
    app = application()
    database().save('recent', record(site, title, thumb, url, 8))
    dialog = control.DialogProgress()
    dialog.create('Finding a working server', title)
    state = {'message': 'Refreshing servers…', 'percent': 0}
    preferred = [0, 2160, 1080, 720, 480][setting_int('preferred_quality', 0, 0, 4)]

    def find(_, deadline, stop):
        with client.request_budget(deadline, stop):
            videos = app.scraper_for(site).get_videos(url)
            candidates = streams.rank(videos or [], preferred)
            for index, (label, candidate) in enumerate(candidates):
                if stop.is_set() or time.monotonic() >= deadline:
                    return None
                state.update(message='Trying {}'.format(label), percent=int(index * 100 / max(1, len(candidates))))
                try:
                    item = app.play_video(candidate, resolve_only=True, quiet=True, title=title)
                    if item and streams.media_available(item.getPath(), client.request):
                        item.setArt({'thumb': thumb, 'poster': thumb, 'fanart': control._fanart})
                        return item
                except Exception:
                    continue
        return None
    try:
        results, partial = parallel.collect([None], find, workers=1, seconds=50,
                                            cancelled=dialog.iscanceled,
                                            progress=lambda *_: dialog.update(state['percent'], state['message']))
        cancelled = dialog.iscanceled()
    finally:
        dialog.close()
    chosen = results[0][1] if results else None
    if chosen:
        control.setResolvedUrl(control._handle, True, chosen)
    else:
        if not cancelled:
            control.notify('No working server found. Try another source or Choose a server.')
        control.setResolvedUrl(control._handle, False, app.make_listitem())
