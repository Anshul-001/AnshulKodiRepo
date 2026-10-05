"""
    Deccan Delight Kodi Addon
    Copyright (C) 2016 gujal

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
import importlib
import tempfile
import time

import six
from resources.lib import cache, client, control, experience, parallel, streams
from resources.lib.base import Scraper, check_hosted_media
from resources.scrapers import *  # NoQA
from six.moves import urllib_parse, urllib_request


_changelog = control._path + '/changelog.txt'
try:
    cache_duration = float(control.get_setting('timeout'))
except (TypeError, ValueError):
    cache_duration = 6

msites = [
    'tgun', 'tamilian', 'tyogi', 'torm', 'hlinks',
    'moviehax', 'ibomma', 'einthusan', 'mrulz', 'mghar',
    'b2t', 'wompk', 'gomovies', 'cinevez', 'todaypk',
    'flinks', 'dcine', 'hflinks'
]


def clear_cache():
    """
    Clear the cache database.
    """
    msg = 'Cached Data has been cleared'
    cache.cache_clear()
    control.notify(msg)


if control.get_setting('version') != control._version:
    control._addon.setSetting('version', control._version)
    cache.cache_clear()
    control.notify('Updated to ' + control._version)

sites = {
    '01tgun': 'Tamil Gun : [COLOR yellow]Tamil[/COLOR]',
    # '02tamilian': 'Tamilian : [COLOR yellow]Tamil[/COLOR]',
    '03tyogi': 'Tamil Yogi : [COLOR yellow]Tamil[/COLOR]',
    # '21ibomma': 'iBOMMA : [COLOR yellow]Telugu[/COLOR]',
    # '22torm': 'TOR Malayalam : [COLOR yellow]Malayalam[/COLOR]',
    '31hlinks': 'Hindi Links 4U : [COLOR yellow]Hindi[/COLOR]',
    '32moviehax': 'Movie Hax : [COLOR yellow]Hindi[/COLOR]',
    '42einthusan': 'Einthusan : [COLOR magenta]Various[/COLOR]',
    '43mrulz': 'Movie Rulz : [COLOR magenta]Various[/COLOR]',
    # '44mghar': 'Movies Ghar : [COLOR magenta]Various[/COLOR]',
    # '45b2t': 'Bolly 2 Tolly : [COLOR magenta]Various[/COLOR]',
    '47wompk': 'Online Movies PK : [COLOR magenta]Various[/COLOR]',
    '48gomovies': '0GoMovies : [COLOR magenta]Various[/COLOR]',
    # '49cinevez': 'Cine Vez : [COLOR magenta]Various[/COLOR]',
    '50todaypk': 'TodayPk : [COLOR magenta]Various[/COLOR]',
    '51flinks': 'Film Links 4U : [COLOR magenta]Various[/COLOR]',
    '52dcine': 'Desi Cinemas : [COLOR magenta]Various[/COLOR]',
    '53hflinks': 'HindiLinks4U Pro : [COLOR magenta]Various[/COLOR]',
    # '71ttvshow': 'Tamil TV Show: [COLOR yellow]Tamil Catchup TV[/COLOR]',
    # '72skytamil': 'sky Tamil: [COLOR yellow]Tamil Catchup TV[/COLOR]',
    # '73tdhool': 'Tamil Dhool : [COLOR yellow]Tamil Catchup TV[/COLOR]',
    # '77manatv': 'Mana Telugu : [COLOR yellow]Telugu Catchup TV[/COLOR]',
    # '81apnetv': 'Apne TV : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    '82desiseri': 'Desi Serials : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    '83desit': 'DesiTellyBox : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    '84pdesi': 'Play Desi : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    # '85sghar': 'Serial Ghar : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    # '86wapne': 'Watch Apne : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    '87yodesi': 'Yo Desi : [COLOR yellow]Hindi Catchup TV[/COLOR]',
    '91ary': 'ARY Digital : [COLOR yellow]Urdu Catchup TV[/COLOR]',
    '92geo': 'Geo TV : [COLOR yellow]Urdu Catchup TV[/COLOR]',
    '93hum': 'HUM TV : [COLOR yellow]Urdu Catchup TV[/COLOR]',
    '99gmala': 'Hindi Geetmala : [COLOR yellow]Hindi Songs[/COLOR]'
}

# site code (without the 2-digit sort prefix) -> friendly name, for labelling
# results in the merged global-search list
sitenames = {k[2:]: v.split(' : ')[0].split(':')[0].strip() for k, v in sites.items()}


def scraper_for(site):
    from resources.scrapers import __all__
    if site not in __all__:
        raise ValueError('Unknown source')
    module = importlib.import_module('resources.scrapers.' + site)
    return getattr(module, site)()


def make_listitem(*args, **kwargs):
    if control.kodiver < 18.0:
        li = control._listitem(*args, **kwargs)
    else:
        li = control._listitem(*args, offscreen=True, **kwargs)
    return li


def update_listitem(li, labels):
    labels = dict(labels)
    cast2 = labels.pop('cast2') if 'cast2' in labels.keys() else []
    unique_ids = {}
    tmdb_id = labels.get('tmdb_id')
    imdb_id = labels.get('imdb_id')
    if tmdb_id:
        unique_ids.update({'tmdb': tmdb_id})
        labels.pop('tmdb_id')
    if imdb_id:
        unique_ids.update({'imdb': imdb_id})
        labels.pop('imdb_id')
    if control.kodiver > 19.8 and isinstance(labels, dict):
        vtag = li.getVideoInfoTag()
        if labels.get('title'):
            vtag.setTitle(labels['title'])
        if labels.get('tag'):
            vtag.setTagLine(labels['tag'])
        if labels.get('plot'):
            vtag.setPlot(labels['plot'])
        if labels.get('year'):
            vtag.setYear(int(labels['year']))
        if labels.get('premiered'):
            vtag.setPremiered(labels['premiered'])
        if labels.get('duration'):
            vtag.setDuration(labels['duration'])
        if labels.get('country'):
            vtag.setCountries(labels['country'])
        if labels.get('genre'):
            vtag.setGenres(labels['genre'])
        if labels.get('director'):
            vtag.setDirectors(labels['director'])
        if labels.get('writer'):
            vtag.setWriters(labels['writer'])
        if labels.get('studio'):
            vtag.setStudios(labels['studio'])
        if labels.get('rating'):
            vtag.setRating(labels['rating'])
        if labels.get('trailer'):
            vtag.setTrailer(labels['trailer'])
        if labels.get('mediatype'):
            vtag.setMediaType(labels['mediatype'])
        if unique_ids:
            vtag.setUniqueIDs(unique_ids)
        if cast2:
            vtag.setCast(control.makecast(cast2))

    else:
        li.setInfo(type='Video', infoLabels=labels)
        if unique_ids:
            li.setUniqueIDs(unique_ids)
        if cast2:
            li.setCast(cast2)
    return li


def list_sites():
    experience.home()


def _search_site(job, deadline, stop):
    site, query = job
    with client.request_budget(deadline, stop):
        scraper = scraper_for(site)
        scraper.get_SearchQuery = lambda _: query
        menu, mode, icon = cache.get(scraper.get_menu, cache_duration)
        surl = next((url.split('MMMM')[0] for title, url in menu.items() if 'Search' in title), None)
        if not surl:
            return []
        movies, imode = scraper.get_items(surl)
        return [(site, imode, movie) for movie in movies if 'Next Page' not in movie[0]]


def global_search():
    query = control.keyboard_query('Search movies & shows')
    if not query:
        experience.finish([])
        return
    dialog = control.DialogProgress()
    dialog.create('Searching your sources', query)
    health = {item['site']: item for item in experience.database().items('health')}
    enabled = [site for site in experience.enabled_sources()
               if health.get(site, {}).get('available') is not False or time.time() - health[site]['updated'] >= 1800]
    try:
        jobs, partial = parallel.collect([(site, query) for site in enabled], _search_site,
                                        workers=5, seconds=25, cancelled=dialog.iscanceled,
                                        progress=lambda done, total: dialog.update(int(done * 100 / max(1,total)), '{} of {} sources finished'.format(done,total)))
    finally:
        dialog.close()
    results = [entry for _, entries in jobs if entries for entry in entries]
    results.sort(key=lambda entry: (query.lower() not in entry[2][0].lower(), entry[2][0].lower(), entry[0]))
    rows, seen = [], set()
    for site, mode, movie in results:
        key = (site, movie[2])
        if key in seen:
            continue
        seen.add(key)
        entry = experience.title_row(site, movie[0] or 'Unknown', movie[1] or control._icon, movie[2], mode)
        entry[1].setLabel((movie[0] or 'Unknown') + ' [COLOR grey]• ' + sitenames[site] + '[/COLOR]')
        rows.append(entry)
    if not rows:
        control.notify('No matches. Try a shorter title or another source.')
    elif partial:
        control.notify('Showing completed searches. Some sources did not finish.')
    experience.finish(rows)


def list_menu(site):
    scraper = scraper_for(site)
    menu, mode, icon = cache.get(scraper.get_menu, cache_duration)
    rows = []
    for title, url in sorted(menu.items()):
        if 'Adult' in title and control.get_setting('adult') != 'true':
            continue
        label = re.sub(r'^\d+', '', title)
        nextmode = mode
        if 'MMMM' in url:
            url, nextmode = url.rsplit('MMMM', 1)
        image = icon
        if 'Search' in label:
            label, image = 'Search this source', experience.art('search')
        entry = experience.row(label, experience.route(nextmode, site=site, iurl=url), image,
                               'Browse ' + sitenames.get(site, site) + '.', int(nextmode) != 9)
        if int(nextmode) == 9:
            entry[1].setProperty('IsPlayable', 'true')
        rows.append(entry)
    if not rows:
        control.notify('This source is unavailable. Retry in Source availability.')
    experience.finish(rows, 'videos')


def list_top(site, iurl):
    """
    Create the Site menu in the Kodi interface.
    """
    scraper = scraper_for(site)
    menu, mode = cache.get(scraper.get_top, cache_duration, iurl)
    listing = []
    for title, icon, iurl in menu:
        if 'MMMM' in iurl:
            nurl, nmode = iurl.split('MMMM')
            list_item = make_listitem(label=title)
            list_item.setArt({'thumb': icon,
                              'icon': icon,
                              'fanart': control._fanart})
            url = '{0}?action={1}&site={2}&iurl={3}'.format(control._url, nmode, site, urllib_parse.quote(nurl))
            is_folder = True
            listing.append((url, list_item, is_folder))
        else:
            list_item = make_listitem(label=title)
            list_item.setArt({'thumb': icon,
                              'icon': icon,
                              'poster': icon,
                              'fanart': control._fanart})
            url = '{0}?action={1}&site={2}&iurl={3}'.format(control._url, mode, site, urllib_parse.quote(iurl))
            is_folder = True
            listing.append((url, list_item, is_folder))
    control.addDir(control._handle, listing, len(listing))
    control.setContent(control._handle, 'videos')
    control.eod(control._handle)


def list_second(site, iurl):
    scraper = scraper_for(site)
    menu, mode = cache.get(scraper.get_second, cache_duration, iurl)
    rows = []
    for title, icon, page in menu:
        if 'Next Page' in title:
            rows.append(experience.row(title, experience.route(5, site=site, iurl=page), icon))
        else:
            rows.append(experience.title_row(site, title, icon, page, mode))
    experience.finish(rows, 'tvshows')


def list_third(site, iurl):
    scraper = scraper_for(site)
    menu, mode = cache.get(scraper.get_third, cache_duration, iurl)
    rows = []
    for title, icon, page in menu:
        if 'Next Page' in title:
            rows.append(experience.row(title, experience.route(6, site=site, iurl=page), icon))
        else:
            rows.append(experience.title_row(site, title, icon, page, mode))
    experience.finish(rows, 'tvshows')


def list_items(site, iurl):
    scraper = scraper_for(site)
    if iurl.endswith('='):
        movies, mode = scraper.get_items(iurl)
    else:
        movies, mode = cache.get(scraper.get_items, cache_duration, iurl)
    metadata = {}
    if control.get_setting('meta') == 'true' and site in msites:
        from resources.lib.metautils import get_meta
        titles = list(dict.fromkeys(movie[0] for movie in movies if 'Next Page' not in movie[0]))
        def lookup(title, deadline, stop):
            with client.request_budget(deadline, stop):
                return get_meta(title)
        completed, _ = parallel.collect(titles, lookup, workers=4, seconds=12)
        metadata = {title: value for title, value in completed if value}
    rows = []
    for movie in movies:
        title, thumb, page = movie[:3]
        if 'Next Page' in title:
            rows.append(experience.row(title, experience.route(7, site=site, iurl=page), thumb, 'More titles from this source.'))
            continue
        entry = experience.title_row(site, title or 'Unknown', thumb, page, mode)
        meta = metadata.get(title)
        if meta and meta.get('tmdb_id'):
            data = dict(meta)
            art = data.pop('art', {}) or {}
            update_listitem(entry[1], data)
            entry[1].setArt({'poster': art.get('poster') or thumb,
                            'fanart': art.get('fanart') or control._fanart})
        rows.append(entry)
    if not rows:
        control.notify('No titles available here. Refresh or try another category.')
    experience.finish(rows)


def list_videos(site, title, iurl, thumb):
    experience.database().save('recent', experience.record(site, title, thumb, iurl, 8))
    scraper = scraper_for(site)
    videos = cache.get(scraper.get_videos, 1.0 / 60, iurl, _stale=False) or []
    preferred = [0, 2160, 1080, 720, 480][experience.setting_int('preferred_quality', 0, 0, 4)]
    rows = []
    if videos:
        target = experience.route(14, site=site, title=title, thumb=thumb, iurl=iurl)
        best = experience.row('Play best available', target, experience.art('play'), 'Try working servers automatically in your preferred quality.', False)
        best[1].setProperty('IsPlayable', 'true')
        rows.append(best)
    for name, video in streams.rank(videos, preferred):
        item = make_listitem(label=name)
        item.setArt({'thumb': thumb, 'icon': thumb, 'poster': thumb, 'fanart': control._fanart})
        update_listitem(item, {'title': title, 'plot': 'Play this server. Use Play best available for automatic fallback.'})
        item.setProperty('IsPlayable', 'true')
        target = experience.route(9, iurl=video, title=title)
        rows.append((target, item, False))
    if not videos:
        control.notify('No video servers found for this title. Try another source.')
    experience.finish(rows, 'videos')


def resolve_url(url, subs=False, quiet=False):
    hmf = check_hosted_media(url, subs)
    if not hmf:
        if not quiet:
            control.notify('This video host is not supported by ResolveURL.')
        return False

    try:
        if subs:
            resp = hmf.resolve()
            stream_url = resp.get('url')
        else:
            stream_url = hmf.resolve()
        # If resolveurl returns false then the video url was not resolved.
        if not stream_url or not isinstance(stream_url, six.string_types):
            if not stream_url:
                msg = 'File removed'
            else:
                msg = str(stream_url)
            if not quiet:
                control.notify(msg, 'Resolve URL', 5000)
            return False
    except Exception as e:
        try:
            msg = str(e)
        except:
            msg = url
        if not quiet:
            control.notify(msg, 'Resolve URL', 5000)
        return False

    if subs:
        return resp
    return stream_url


class StopDownloading(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def downloadVideo(url, name):

    def _pbhook(downloaded, filesize, url=None, dp=None, name=''):
        try:
            percent = min(int((downloaded * 100) / filesize), 100)
            currently_downloaded = float(downloaded) / (1024 * 1024)
            kbps_speed = int(downloaded / (time.perf_counter() if six.PY3 else time.clock() - start))
            if kbps_speed > 0:
                eta = (filesize - downloaded) / kbps_speed
            else:
                eta = 0
            kbps_speed = kbps_speed / 1024
            total = float(filesize) / (1024 * 1024)
            mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total)
            e = 'Speed: %.02f MB/s ' % kbps_speed
            e += 'ETA: %02d:%02d' % divmod(eta, 60)
            dp.update(percent, '{0}[CR]{1}[CR]{2}'.format(name[:50], mbs, e))
        except:
            percent = 100
            dp.update(percent)
        if dp.iscanceled():
            dp.close()
            raise StopDownloading('Stopped Downloading')

    def getResponse(url, hdrs, size):
        try:
            if size > 0:
                size = int(size)
                hdrs['Range'] = 'bytes=%d-' % size

            req = urllib_request.Request(url, headers=hdrs)

            resp = urllib_request.urlopen(req, timeout=30)
            return resp
        except:
            return None

    def doDownload(url, dest, dp, name):
        headers = {}
        if '|' in url:
            url, uheaders = url.split('|')
            headers = dict(urllib_parse.parse_qsl(uheaders))

        if 'User-Agent' not in list(headers.keys()):
            headers.update(control.mozhdr)

        resp = getResponse(url, headers, 0)

        if not resp:
            dialog.ok("Indian Movie Hub", 'Download Failed[CR]No response')
            return False
        try:
            content = int(resp.headers['Content-Length'])
        except:
            content = 0
        try:
            resumable = 'bytes' in resp.headers['Accept-Ranges'].lower()
        except:
            resumable = False
        if resumable:
            control.log("Download is resumable")

        if content < 1:
            dialog.ok("Indian Movie Hub", 'Unknown File Size[CR]Cannot Download')
            return False

        size = 8192
        mb = content / (1024 * 1024)

        if content < size:
            size = content

        total = 0
        errors = 0
        count = 0
        resume = 0
        sleep = 0

        control.log('Filesize : {0}MB {1} '.format(mb, dest))
        f = control.openFile(dest, 'w')

        chunk = None
        chunks = []

        while True:
            downloaded = total
            for c in chunks:
                downloaded += len(c)
            percent = min(100 * downloaded / content, 100)

            _pbhook(downloaded, content, url, dp, name)

            chunk = None
            error = False

            try:
                chunk = resp.read(size)
                if not chunk:
                    if percent < 99:
                        error = True
                    else:
                        while len(chunks) > 0:
                            c = chunks.pop(0)
                            f.write(c)
                            del c
                        f.close()
                        return True

            except Exception as e:
                control.log(str(e))
                error = True
                sleep = 10
                errno = 0

                if hasattr(e, 'errno'):
                    errno = e.errno

                if errno == 10035:  # 'A non-blocking socket operation could not be completed immediately'
                    pass

                if errno == 10054:  # 'An existing connection was forcibly closed by the remote host'
                    errors = 10  # force resume
                    sleep = 30

                if errno == 11001:  # 'getaddrinfo failed'
                    errors = 10  # force resume
                    sleep = 30

            if chunk:
                errors = 0
                chunks.append(chunk)
                if len(chunks) > 5:
                    c = chunks.pop(0)
                    f.write(c)
                    total += len(c)
                    del c

            if error:
                errors += 1
                count += 1
                control.sleep(sleep * 1000)

            if (resumable and errors > 0) or errors >= 10:
                if (not resumable and resume >= 50) or resume >= 500:
                    # Give up!
                    return False

                resume += 1
                errors = 0
                if resumable:
                    chunks = []
                    # create new response
                    resp = getResponse(url, headers, total)
                else:
                    # use existing response
                    pass

    def clean_filename(s):
        if not s:
            return ''
        badchars = '\\/:*?"<>|\''
        for c in badchars:
            s = s.replace(c, '')
        return s.strip()

    download_path = control.get_setting('dlfolder')
    while not download_path:
        control.notify('Choose download directory in Settings!', 'Download:', 5000)
        control._addon.openSettings()
        download_path = control.get_setting('dlfolder')

    dp = control.pDialog
    name = re.sub(r'\[/?(?:COLOR|I|CR|B).*?]', '', name).strip()
    dp.create('Indian Movie Hub Download', name[:50])
    tmp_file = tempfile.mktemp(dir=download_path, suffix=".mp4")
    tmp_file = control.makeFilename(tmp_file)
    vidfile = control.makeFilename(download_path + clean_filename(name) + ".mp4")
    if not control.pathExists(vidfile):
        start = time.perf_counter() if six.PY3 else time.clock()
        try:
            downloaded = doDownload(url, tmp_file, dp, name)
            if downloaded:
                try:
                    control.renameFile(tmp_file, vidfile)
                    return vidfile
                except:
                    return tmp_file
            else:
                raise StopDownloading('Stopped Downloading')
        except:
            while control.pathExists(tmp_file):
                try:
                    control.deleteFile(tmp_file)
                    break
                except:
                    pass
    else:
        control.notify('Download:', 'File already exists!')


def play_video(vid_url, dl=False, resolve_only=False, quiet=False, title=None):
    """
    Play a video by the provided path.
    """
    streamer_list = [
        'tamilgun', 'mersalaayitten', 'mhdtvworld.', '/hls/', 'poovee.',
        'watchtamiltv.', 'cloudspro.', 'abroadindia.', 'nextvnow.', 'harpalgeo.',
        'hindilyrics4u.', '.mp4', 'googlevideo.', 'playembed.', 'akamaihd.',
        'tamilhdtv.', 'andhrawatch.', 'tamiltv.', 'athavantv', 'cinemalayalam',
        'justmoviesonline.', '.mp3', 'googleapis.', '.m3u8', 'telugunxt.',
        'playallu.', 'bharat-movies.', 'googleusercontent.', 'arydigital.',
        'space-cdn.', 'einthusan.', 'd0stream.', 'telugugold.', '.xdiv.',
        'hum.tv', 'apnevideotwo.', 'player.business', 'tamilian.'
    ]
    # Create a playable item with a path to play.
    title = title or 'unknown'
    stream_url = False
    if 'ZZZZ' in vid_url:
        vid_url, title = vid_url.split('ZZZZ', 1)

    play_item = make_listitem(path=vid_url)

    # Set title/year metadata so Kodi's subtitle services (OpenSubtitles,
    # Subscene, ...) can search for external subtitles by name during playback.
    if title and title != 'unknown':
        try:
            clean = re.sub(r'\[/?COLOR[^\]]*\]|\[/?B\]', '', title).strip()
            info = {'title': clean, 'mediatype': 'movie'}
            ym = re.search(r'\b(19|20)\d{2}\b', clean)
            if ym:
                info['year'] = int(ym.group(0))
            update_listitem(play_item, info)
        except Exception:
            pass

    if any([x in vid_url for x in streamer_list]):
        if 'einthusan.' in vid_url:
            scraper = einthusan.einthusan()  # NoQA
            stream_url = scraper.get_video(vid_url)
            play_item.setPath(stream_url)
        elif '.xdiv.' in vid_url:
            scraper = ibomma.ibomma()  # NoQA
            stream_url = scraper.get_video(vid_url)
            play_item.setPath(stream_url)
        elif 'apnevideotwo.' in vid_url:
            stream_url = urllib_parse.quote(vid_url, ':/|=?')
            play_item.setPath(stream_url)
        elif 'player.business' in vid_url:
            headers = dict(control.mozhdr)
            spage = client.request(vid_url, headers=headers)
            matches = re.findall(r'"src":"([^"]+)","label":"([^"]+)', spage)
            if len(matches) > 1:
                sources = []
                for match in matches:
                    sources.append(match[1])
                ret = 0 if quiet else control.Dialog().select('Choose a Source', sources)
                if ret < 0:
                    return None
                match = matches[ret]
            else:
                match = matches[0]
            stream_url = match[0] + '|User-Agent={}'.format(headers['User-Agent'])
            play_item.setPath(stream_url)
        # elif ('tamilyogi.' in vid_url or 'tamilvip.' in vid_url) and '.m3u8' not in vid_url:
        #     scraper = tyogi.tyogi()  # NoQA
        #     stream_url = scraper.get_video(vid_url)
        #     if stream_url:
        #         stream_url = resolve_url(stream_url, quiet=quiet)
        #         if stream_url:
        #             play_item.setPath(stream_url)
        #         else:
        #             play_item.setPath(None)
        elif 'hindilyrics4u.' in vid_url:
            scraper = gmala.gmala()  # NoQA
            stream_url = scraper.get_video(vid_url)
            if stream_url:
                if 'youtube.' in stream_url:
                    stream_url = resolve_url(stream_url, quiet=quiet)
                play_item.setPath(stream_url)
        elif 'tamilgun.' in vid_url:
            if '.m3u8' in vid_url:
                stream_url = vid_url
            else:
                scraper = tgun.tgun()  # NoQA
                stream_url = scraper.get_video(vid_url)
            if stream_url:
                play_item.setPath(stream_url)
        elif 'arydigital.' in vid_url:
            scraper = ary.ary()  # NoQA
            stream_url = scraper.get_video(vid_url)
            if check_hosted_media(stream_url):
                stream_url = resolve_url(stream_url, quiet=quiet)
            if stream_url:
                play_item.setPath(stream_url)
            else:
                play_item.setPath(None)
        elif 'harpalgeo.' in vid_url:
            scraper = geo.geo()  # NoQA
            stream_url = scraper.get_video(vid_url)
            play_item.setPath(stream_url)
        elif 'hum.tv' in vid_url:
            scraper = hum.hum()  # NoQA
            stream_url = scraper.get_video(vid_url)
            if stream_url:
                embeds = ['youtube.', 'dailymotion', 'youtu.be']
                if any(x for x in embeds if x in stream_url):
                    stream_url = resolve_url(stream_url, quiet=quiet)
                if stream_url:
                    play_item.setPath(stream_url)
                else:
                    play_item.setPath(None)
            else:
                play_item.setPath(None)
        elif 'playembed.' in vid_url or 'videoapne.' in vid_url or '.m3u8' in vid_url:
            stream_url = vid_url
            play_item.setPath(stream_url)
        elif 'load.' in vid_url:
            stream_url = resolve_url(vid_url, quiet=quiet)
            if stream_url:
                play_item.setPath(stream_url)
            else:
                play_item.setPath(None)
        elif '.mp4' in vid_url:
            if '|' not in vid_url and check_hosted_media(vid_url):
                stream_url = resolve_url(vid_url, quiet=quiet)
            else:
                stream_url = vid_url
            if stream_url:
                play_item.setPath(stream_url)
            else:
                play_item.setPath(None)
        else:
            stream_url = vid_url
            play_item.setPath(stream_url)
    else:
        stream_url = False
        resp = resolve_url(vid_url, subs=True, quiet=quiet)
        if resp:
            stream_url = resp.get('url')
            subtitles = resp.get('subs')
        if stream_url:
            play_item.setPath(stream_url)
            if subtitles:
                play_item.setSubtitles(list(subtitles.values()))
        else:
            # play_item.setPath(None)
            return

    if dl and stream_url:
        downloadVideo(stream_url, title)

    elif stream_url:
        non_ia = ['yupp', 'SUNNXT', 'tamilgun', 'vidmojo', 'serafim', '__temp_',
                  'cloud', 'proxysite', 'dailymotion']
        # control.log(stream_url, level='info')

        if control.kodiver >= 17.0 and not any(x in stream_url for x in non_ia):
            if '.m3u8' in stream_url or '/m3u8/' in stream_url or '/hls/' in stream_url:
                # control.log('Attempting playback with ISA', level='info')
                play_item.setMimeType('application/x-mpegURL')
                play_item.setContentLookup(False)
                adaptive_list = [
                    'master', 'adaptive', 'tamilray', 'index', 'playallu',
                    'thrfive', 'video', 'v1lst', 'turbovi', 'hls-vod'
                ]
                if any([x in stream_url for x in adaptive_list]):
                    if control.kodiver < 19.0:
                        play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                    else:
                        play_item.setProperty('inputstream', 'inputstream.adaptive')
                    if control.kodiver < 20.9:
                        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                    if '|' in stream_url:
                        _, strhdr = stream_url.split('|')
                        play_item.setProperty('inputstream.adaptive.stream_headers', strhdr)
                        if control.kodiver > 21.8:
                            play_item.setProperty('inputstream.adaptive.common_headers', strhdr)
                        elif control.kodiver > 19.8:
                            play_item.setProperty('inputstream.adaptive.manifest_headers', strhdr)
                        play_item.setPath(stream_url)

            if '.mpd' in stream_url:
                if control.kodiver < 19.0:
                    play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                else:
                    play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                play_item.setMimeType('application/dash+xml')
                play_item.setContentLookup(False)

            elif '.ism' in stream_url:
                if control.kodiver < 19.0:
                    play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                else:
                    play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', 'ism')
                play_item.setMimeType('application/vnd.ms-sstr+xml')
                play_item.setContentLookup(False)

        if resolve_only:
            return play_item
        control.setResolvedUrl(control._handle, True, listitem=play_item)
