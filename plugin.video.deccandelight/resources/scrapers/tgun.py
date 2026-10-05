'''
DeccanDelight scraper plugin
Copyright (C) 2016 gujal

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''
import json
import re

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import control, client
from resources.lib.base import Scraper
from resources.lib.htmlutils import absolute, append_next, document, thumbnail
from six.moves import urllib_parse


class tgun(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = 'https://tamilgun.now'
        self.icon = self.ipath + 'tgun.png'

    def get_menu(self):
        soup = document(client.request(self.bu))
        items = {}
        seen = set()
        links = soup.select('a.cat-btn[href], li[id^="menu"] a[href*="category"]')
        for link in links:
            url = absolute(self.bu + '/', link.get('href'))
            title = self.unescape(link.get_text(' ', strip=True))
            if not url or url in seen or title.lower() == 'home':
                continue
            seen.add(url)
            items['{:02d}{}'.format(len(items) + 1, title)] = url
        items['99[COLOR yellow]** Search **[/COLOR]'] = self.bu + '/?s='
        return (items, 7, self.icon)

    def get_items(self, url):
        movies = []
        if url.endswith('?s='):
            url += urllib_parse.quote_plus(self.get_SearchQuery('Tamil Gun'))
        soup = document(client.request(url))
        seen = set()
        for item in soup.select('div.image-item, article.video, article[class*="video"]'):
            link = item.select_one('a.image-link[href], h3 a[href], a[href]')
            heading = item.find('h3')
            if not link:
                continue
            target = absolute(url, link.get('href'))
            title = self.unescape(heading.get_text(' ', strip=True) if heading else link.get('title', link.get_text(' ', strip=True)))
            if not target or not title or target in seen:
                continue
            seen.add(target)
            if 'all episodes' in title.lower():
                target += 'MMMM7'
            movies.append((title, thumbnail(item, url, self.icon), target))
        append_next(movies, soup, url, self.nicon)
        return (movies, 8)

    def _public_player(self, url, videos):
        parsed = urllib_parse.urlsplit(url)
        if parsed.hostname != 'player4.spirituallifewell.com':
            return False
        match = re.match(r'^/videos/([0-9a-f-]+)$', parsed.path, re.I)
        if not match:
            return False
        root = '{}://{}/'.format(parsed.scheme, parsed.netloc)
        api = root + 'api/playback/resolve'
        try:
            raw = client.request(api, params={'contentType': 'video', 'videoId': match.group(1)},
                                 headers={'Referer': url, 'User-Agent': self.hdr.get('User-Agent', '')})
            data = json.loads(raw or '{}')
        except (TypeError, ValueError):
            return True
        if not isinstance(data, dict):
            return True
        options = data.get('playbackOptions') or [{'sourceUrl': data.get('sourceUrl'),
                                                   'isEmbed': data.get('selectedServerIsEmbed')}]
        seen = set()
        for option in options:
            if not isinstance(option, dict):
                continue
            source = absolute(root, option.get('sourceUrl'))
            if not source or source in seen:
                continue
            seen.add(source)
            label = 'TamilGun ' + (option.get('label') or 'Direct')
            if option.get('isEmbed'):
                self.resolve_media(source, videos, label)
            elif urllib_parse.urlsplit(source).path.lower().endswith(('.m3u8', '.mp4')):
                headers = urllib_parse.urlencode({'Referer': root, 'User-Agent': self.hdr.get('User-Agent', '')})
                videos.append((label, source + '|' + headers))
        return True

    def get_videos(self, url):
        videos = []
        if 'cinebix.com' in url:
            self.resolve_media(url, videos)
            return videos

        elif 'tamildbox.' in url or 'tamilhdbox' in url:
            self.resolve_media(url, videos)
            return videos

        html = client.request(url) or ''

        r = re.findall(r"unescape\('([^']+)", html)
        if r:
            for item in r:
                linkcode = urllib_parse.unquote(item)
                source = re.findall('<iframe.+?src="([^"]+)', linkcode, re.IGNORECASE)
                if source:
                    self.resolve_media(source[0], videos)

        mlink = SoupStrainer('div', {'id': re.compile('player-')})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        try:
            links = videoclass.find_all('iframe')
            for link in links:
                iurl = absolute(url, link.get('src'))
                if not iurl:
                    continue
                if self._public_player(iurl, videos):
                    continue
                if 'playallu.' in iurl:
                    vidhost, strlink = self.playallu(iurl, self.bu)
                    if vidhost is not None:
                        videos.append((vidhost, strlink))
                elif 'bit.ly' not in iurl:
                    self.resolve_media(iurl, videos)
        except:
            pass

        mlink = SoupStrainer('div', {'id': 'videoframe'})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        try:
            links = videoclass.find_all('iframe')
            for link in links:
                iurl = link.get('src')
                if iurl.startswith('//'):
                    iurl = 'https:' + iurl
                if 'playallu.' in iurl:
                    vidhost, strlink = self.playallu(iurl, self.bu)
                    if vidhost is not None:
                        videos.append((vidhost, strlink))
                else:
                    self.resolve_media(iurl, videos)
        except:
            pass

        try:
            links = videoclass.find_all('a')
            for link in links:
                if 'href' in str(link):
                    iurl = link.get('href')
                else:
                    iurl = link.get('onclick').split("'")[1]
                if iurl.startswith('//'):
                    iurl = 'https:' + iurl
                self.resolve_media(iurl, videos)
        except:
            pass

        mlink = SoupStrainer('div', {'class': 'post-entry'})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        try:
            links = videoclass.find_all('iframe')
            for link in links:
                iurl = link.get('src').replace('&amp;', '&')
                if iurl.startswith('//'):
                    iurl = 'https:' + iurl
                if 'playallu.' in iurl:
                    vidhost, strlink = self.playallu(iurl, self.bu)
                    if vidhost is not None:
                        videos.append((vidhost, strlink))
                else:
                    iurl += '|Referer={}'.format(urllib_parse.urljoin(url, '/'))
                    self.resolve_media(iurl, videos)
        except:
            pass

        mlink = SoupStrainer('div', {'class': 'entry-excerpt'})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        try:
            pdivs = videoclass.find_all('p')
            for pdiv in pdivs:
                links = pdiv.find_all('a')
                for link in links:
                    if 'href' in str(link):
                        iurl = link.get('href')
                    else:
                        iurl = link.get('onclick').split("'")[1]
                    if iurl.startswith('//'):
                        iurl = 'https:' + iurl
                    self.resolve_media(iurl, videos)
        except:
            pass

        try:
            links = videoclass.find_all('iframe')
            for link in links:
                iurl = link.get('src')
                if 'latest.htm' not in iurl:
                    self.resolve_media(iurl, videos)
        except:
            pass

        mlink = SoupStrainer('article')
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        try:
            links = videoclass.find_all('iframe')
            for link in links:
                iurl = link.get('src')
                if 'playallu.' in iurl:
                    vidhost, strlink = self.playallu(iurl, self.bu)
                    if vidhost is not None:
                        videos.append((vidhost, strlink))
                elif 'bit.ly' not in iurl:
                    self.resolve_media(iurl, videos)
        except:
            pass

        r = re.findall('vdf-data-json">(.*?)<', html)
        if r:
            sources = json.loads(r[0])
            iurl = 'https://www.youtube.com/watch?v={}'.format(sources['videos'][0]['youtubeID'])
            self.resolve_media(iurl, videos)

        r = re.search(r'beeteam368_pro_player\((.*?)\);\s', html)
        if r:
            iurl = re.findall('<iframe.+?src="([^"]+)', r.group(1).replace('\\', ''))[0]
            if iurl:
                if 'playallu.' in iurl:
                    vidhost, strlink = self.playallu(iurl, self.bu)
                    if vidhost is not None:
                        videos.append((vidhost, strlink))
                elif 'player3.' in iurl:
                    ihtml = client.request(iurl, referer=self.bu + '/')
                    s = re.search(r'urlStream":"([^"]+)', ihtml)
                    if s:
                        ref = urllib_parse.urljoin(iurl, '/')
                        headers = {'User-Agent': self.hdr.get('User-Agent', ''), 'Referer': ref, 'Origin': ref[:-1]}
                        strlink = s.group(1) + '|{}'.format(urllib_parse.urlencode(headers))
                        videos.append(('player3', strlink))
                else:
                    self.resolve_media(iurl + '$$' + self.bu, videos)

        return videos
