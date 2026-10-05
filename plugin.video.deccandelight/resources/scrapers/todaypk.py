"""
DeccanDelight scraper plugin
Copyright (C) 2019 gujal

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
"""

import json
import re

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import client, jsunpack
from resources.lib.base import Scraper
from resources.lib.htmlutils import absolute, append_next, document, thumbnail
from six.moves import urllib_parse


class todaypk(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('todaypk', ['https://todaypk.biz/'], 'category/tamil-movies', 'boxed film') + 'category/'
        self.icon = self.ipath + 'todaypk.png'
        self.list = {'01Tamil Movies': self.bu + 'tamil-movies',
                     '02Telugu Movies': self.bu + 'telugu-movies',
                     '03Bollywood Movies': self.bu + 'bollywood-movies',
                     '04Hollywood Movies': self.bu + 'hollywood-movies',
                     '05South Indian Hindi Dubbed Movies': self.bu + 'south-indian-hindi-dubbed/',
                     '06Web Series': self.bu + 'web-series/'}

    def get_menu(self):
        soup = document(client.request(self.bu[:-9]))
        items = {}
        seen = set()
        for link in soup.select('nav a[href*="/category/"], .navbar a[href*="/category/"], .menu a[href*="/category/"]'):
            url = absolute(self.bu, link.get('href'))
            title = link.get_text(' ', strip=True)
            if not url or not title or url in seen:
                continue
            # These published categories currently return provider errors or
            # "No result found". Other languages remain in the live menu.
            if urllib_parse.urlsplit(url).path.rstrip('/').split('/')[-1] in ('malayalam-movies', 'tv-shows'):
                continue
            seen.add(url)
            items['{:02d}{}'.format(len(items) + 1, title)] = url
        if not items:
            items = dict(self.list)
        items['99[COLOR yellow]** Search **[/COLOR]'] = self.bu[:-9] + 'search_movies?s='
        return (items, 7, self.icon)

    def get_items(self, url):
        movies = []
        if url.endswith('?s='):
            url += urllib_parse.quote_plus(self.get_SearchQuery('Today PK'))
        soup = document(client.request(url))
        seen = set()
        for item in soup.select('div.boxed.film, #content div[id^="post-"]'):
            link = item.find('a', href=True)
            if not link:
                continue
            target = absolute(url, link.get('href'))
            heading = item.find(['h2', 'b'])
            title = self.unescape(heading.get_text(' ', strip=True) if heading else link.get('title', ''))
            if not target or not title or target in seen:
                continue
            seen.add(target)
            movies.append((self.clean_title(title), thumbnail(item, url, self.icon), target))
        append_next(movies, soup, url, self.nicon)
        return (movies, 8)

    def _resolve_server(self, url, videos, label=''):
        if urllib_parse.urlsplit(url).hostname != 'pkembed.site':
            self.resolve_media(url, videos, label)
            return
        # This public PkSpeed alias is absent from ResolveURL's VKSpeed
        # host list. Read the same HTML video sources used by its player.
        html = client.request(url, headers={'Referer': self.bu[:-9]}) or ''
        if jsunpack.detect(html):
            try:
                html = jsunpack.unpack(html)
            except (ValueError, IndexError, TypeError):
                return
        for source in document(html).select('source[src]'):
            target = absolute(url, source.get('src'))
            if not target or not urllib_parse.urlsplit(target).path.lower().endswith(('.mp4', '.m3u8')):
                continue
            headers = urllib_parse.urlencode({'Referer': url, 'User-Agent': self.hdr.get('User-Agent', '')})
            video = ('PkSpeed ' + (source.get('title') or label or 'Direct'), target + '|' + headers)
            if video not in videos:
                videos.append(video)

    def get_videos(self, url):
        videos = []
        html = client.request(url) or ''
        soup = document(html)
        seen = set()
        match = re.search(r'var\s+locations\s*=\s*(\[[^\]]*\])', html)
        try:
            locations = json.loads(match.group(1)) if match else []
        except ValueError:
            locations = []
        for location in locations:
            target = absolute(url, location) if isinstance(location, str) else ''
            if target and target not in seen:
                seen.add(target)
                self._resolve_server(target, videos)
        for item in soup.select('iframe[src], iframe[data-src], button.btn a[href], .entry-content a[href], .player a[href]'):
            target = absolute(url, item.get('src') or item.get('data-src') or item.get('href'))
            if not target or target in seen:
                continue
            # Entry content also contains genre/quality navigation and ad
            # buttons. Only external hosts and actual iframes are servers.
            if item.name != 'iframe' and urllib_parse.urlsplit(target).netloc == urllib_parse.urlsplit(url).netloc:
                continue
            seen.add(target)
            if '/waaw/' in target:
                target = 'https://hqq.ac/e/' + target.split('=')[-1]
            quality = re.search(r'(\d+p)', item.get_text())
            self._resolve_server(target, videos, quality.group(1) if quality else '')
        return videos
