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


class gmala(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = 'https://www.hindilyrics4u.com'
        self.icon = self.ipath + 'gmala.png'
        self.list = {'02Browse by Movie Titles': self.bu + '/ZZZZTitles',
                     '03Browse Yearwise': self.bu + '/ZZZZYearwise',
                     '04Browse by Singer': self.bu + '/ZZZZSinger',
                     '05[COLOR yellow]** Search by Singer **[/COLOR]': self.bu + '/search.php?type=1&value=MMMM7',
                     '06[COLOR yellow]** Search by Composer **[/COLOR]': self.bu + '/search.php?type=2&value=MMMM7',
                     '07[COLOR yellow]** Search by Movie **[/COLOR]': self.bu + '/search.php?type=3&value=MMMM7',
                     '08[COLOR yellow]** Search by Song **[/COLOR]': self.bu + '/search.php?type=8&value=MMMM7'}

    def get_menu(self):
        return (self.list, 4, self.icon)

    def get_top(self, iurl):
        categories = []
        url, category = iurl.split('ZZZZ', 1)
        soup = document(client.request(url))
        path = '/singer/' if category == 'Singer' else '/movie/'
        seen = set()
        for link in soup.find_all('a', href=True):
            target = absolute(self.bu, link.get('href'))
            parsed = urllib_parse.urlsplit(target)
            label = link.get_text(' ', strip=True)
            if not parsed.path.startswith(path) or not parsed.path.endswith('.php'):
                continue
            year = bool(re.match(r'^\d{4}$', label))
            if category == 'Yearwise' and not year:
                continue
            if category != 'Yearwise' and (year or len(label) > 3):
                continue
            if target and target not in seen:
                seen.add(target)
                categories.append((label, self.icon, target))
        return (categories, 5)

    def get_second(self, url):
        categories = []
        soup = document(client.request(url))
        seen = set()
        for item in soup.select('div.thumb-item, td.w25p.h150'):
            link = item.find('a', href=True)
            if not link:
                continue
            target = absolute(url, link.get('href'))
            label = item.select_one('.thumb-caption') or item
            title = label.get_text(' ', strip=True) or link.get('title', '')
            if target and title and target not in seen:
                seen.add(target)
                categories.append((title, thumbnail(item, url, self.icon), target))
        if not categories:
            for link in soup.select('a[href*="/movie/"]'):
                target = absolute(url, link.get('href'))
                title = link.get_text(' ', strip=True)
                if target and urllib_parse.urlsplit(target).path.endswith('.htm') and title and target not in seen:
                    seen.add(target)
                    categories.append((title, self.icon, target))
        append_next(categories, soup, url, self.nicon)
        return (categories, 7)

    def get_items(self, url):
        movies = []
        if url.endswith('&value='):
            url += urllib_parse.quote_plus(self.get_SearchQuery('Hindi Geetmala'))
        soup = document(client.request(url))
        seen = set()
        for link in soup.select('a[href*="/song/"]'):
            target = absolute(url, link.get('href'))
            title = link.get_text(' ', strip=True) or link.get('title', '')
            if target and title and target not in seen:
                seen.add(target)
                movies.append((title, thumbnail(link.parent, url, self.icon), target))
        append_next(movies, soup, url, self.nicon)
        return (movies, 9)

    def get_video(self, url):
        soup = document(client.request(url))
        for item in soup.select('iframe[src], iframe[data-src], a[href*="youtube.com"], a[href*="youtu.be"]'):
            target = absolute(url, item.get('src') or item.get('data-src') or item.get('href'))
            if target and any(host in target for host in ('youtube.com/', 'youtu.be/', 'dailymotion.com/')):
                return target
        return ''
