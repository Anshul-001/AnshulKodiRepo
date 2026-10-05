"""
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
"""
import re

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import client
from resources.lib.base import Scraper
from resources.lib.htmlutils import absolute, append_next, document, thumbnail
from six.moves import urllib_parse


class desit(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = 'https://www.desitellybox.to/'
        self.icon = self.ipath + 'desit.png'
        self.videos = []

    def get_menu(self):
        soup = document(client.request(self.bu))
        items = {}
        for block in soup.select('div.td-fix-index, div.colm.span_1_of_3'):
            label = block.find('strong')
            if label and block.find('a', href=True):
                title = self.unescape(label.get_text(' ', strip=True))
                items['{:02d}{}'.format(len(items) + 1, title)] = title
        items['99[COLOR yellow]** Search **[/COLOR]'] = self.bu + '?s=MMMM7'
        return (items, 5, self.icon)

    def get_second(self, iurl):
        shows = []
        soup = document(client.request(self.bu))
        seen = set()
        for block in soup.select('div.td-fix-index, div.colm.span_1_of_3'):
            label = block.find('strong')
            if not label or self.unescape(label.get_text(' ', strip=True)) != iurl:
                continue
            for link in block.select('li a[href]'):
                title = self.unescape(link.get_text(' ', strip=True))
                target = absolute(self.bu, link.get('href'))
                if target and target not in seen and 'completed shows' not in title.lower():
                    seen.add(target)
                    shows.append((title, thumbnail(block, self.bu, self.icon), target))
        return (shows, 7)

    def get_items(self, url):
        episodes = []
        if url.endswith('?s='):
            url += urllib_parse.quote_plus(self.get_SearchQuery('Desi Tashan'))
        soup = document(client.request(url))
        seen = set()
        for heading in soup.select('h3.entry-title, h4'):
            link = heading.find('a', href=True)
            if not link:
                continue
            title = self.unescape(link.get_text(' ', strip=True))
            target = absolute(url, link.get('href'))
            if 'watch online' not in title.lower() or not target or target in seen:
                continue
            seen.add(target)
            episodes.append((self.clean_title(title), thumbnail(heading.parent, url, self.icon), target))
        append_next(episodes, soup, url, self.nicon)
        return (episodes, 8)

    def get_videos(self, url):
        self.videos = []
        soup = document(client.request(url))
        content = soup.select_one('.td-post-content, .entry_content, .entry-content')
        if content is None:
            return []
        seen = set()
        for item in content.select('a[href], iframe[src], iframe[data-src]'):
            target = absolute(url, item.get('href') or item.get('src') or item.get('data-src'))
            if not target or target in seen:
                continue
            seen.add(target)
            part = re.search(r'(Part\s*\d+)', item.get_text(' ', strip=True), re.I)
            self.resolve_media(target, self.videos, part.group(1) if part else '')
        return sorted(self.videos)
