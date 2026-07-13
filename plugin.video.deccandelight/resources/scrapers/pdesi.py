'''
DeccanDelight scraper plugin
Copyright (C) 2021 gujal

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

import base64
import re

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import client
from resources.lib.base import Scraper
from six.moves import urllib_parse


class pdesi(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('pdesi', ['https://www.play-desi.org/'], 'movie/', 'TPost')
        self.icon = self.ipath + 'pdesi.png'
        self.videos = []

    def get_menu(self):
        html = client.request(self.bu, verify=False)
        mlink = SoupStrainer('nav', {'class': 'Menu'})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        items = mdiv.find_all('li', {'class': 'menu-item'})
        mlist = {}
        ino = 1
        seen = []
        for item in items:
            a = item.find('a', href=True)
            if not a:
                continue
            href = a['href']
            label = a.get_text(strip=True)
            if not label or href in seen or href.rstrip('/') == self.bu.rstrip('/'):
                continue
            seen.append(href)
            mlist.update({'{0:02d}{1}'.format(ino, label): href})
            ino += 1
        mlist.update({'99[COLOR yellow]** Search **[/COLOR]': '{0}?s='.format(self.bu)})
        return (mlist, 7, self.icon)

    def get_items(self, url):
        """
        List the shows/movies (article listing) for a category or search.
        Series articles are routed to the episode lister (mode 6), movie
        articles straight to the video lister (mode 8), via a per-item
        MMMM tag so mixed search results route correctly.
        """
        episodes = []
        if url[-3:] == '?s=':
            search_text = self.get_SearchQuery('PlayDesi')
            search_text = urllib_parse.quote_plus(search_text)
            url = url + search_text

        html = client.request(url)
        mlink = SoupStrainer('article')
        items = BeautifulSoup(html, "html.parser", parse_only=mlink)

        for item in items.find_all('article'):
            a = item.find('a', href=True)
            head = item.find(['h2', 'h3'])
            if not a or not head:
                continue
            title = self.unescape(head.get_text(strip=True))
            title = title.encode('utf8') if self.PY2 else title
            iurl = a['href']
            img = item.find('img')
            thumb = self.icon
            if img:
                thumb = img.get('data-src') or img.get('src') or self.icon
                if 'data:image' in thumb:
                    thumb = img.get('data-src') or img.get('data-lazy-src') or self.icon
            if thumb.startswith('http'):
                thumb = '{0}|Referer={1}'.format(thumb, self.bu)
            nextmode = 6 if '/series/' in iurl else 8
            episodes.append((title, thumb, '{0}MMMM{1}'.format(iurl, nextmode)))

        plink = SoupStrainer('nav', {'class': re.compile('pagination')})
        Paginator = BeautifulSoup(html, "html.parser", parse_only=plink)
        nxt = Paginator.find('a', {'class': re.compile(r'\bnext\b')})
        if nxt and nxt.get('href'):
            purl = nxt['href']
            currpg = Paginator.find('span', {'class': re.compile('current')})
            currpg = currpg.text.strip() if currpg else '?'
            pages = Paginator.find_all('a', {'class': 'page-numbers'})
            try:
                lastpg = pages[-2].text.strip()
            except IndexError:
                lastpg = '?'
            title = 'Next Page.. (Currently in Page {0} of {1})'.format(currpg, lastpg)
            episodes.append((title, self.nicon, purl))

        return (episodes, 8)

    def get_third(self, iurl):
        """
        List the episodes of a series. Each episode routes to get_videos.
        """
        shows = []
        html = client.request(iurl)
        pdiv = BeautifulSoup(html, "html.parser", parse_only=SoupStrainer('div', {'class': 'Image'}))
        pimg = pdiv.find('img')
        thumb = self.icon
        if pimg:
            thumb = pimg.get('data-src') or pimg.get('src') or self.icon
            if 'data:image' in thumb:
                thumb = pimg.get('data-src') or self.icon
        mlink = SoupStrainer('div', {'class': re.compile('TPTblCn')})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        for td in mdiv.find_all('td', {'class': 'MvTbTtl'}):
            a = td.find('a', href=True)
            if not a:
                continue
            title = self.unescape(a.get_text(strip=True))
            title = title.encode('utf8') if self.PY2 else title
            shows.append((title, thumb, a['href']))
        return (shows, 8)

    def get_videos(self, url):
        self.videos = []
        html = client.request(url)
        mlink = SoupStrainer('li', {'data-src': True})
        options = BeautifulSoup(html, "html.parser", parse_only=mlink)

        for li in options.find_all('li', attrs={'data-src': True}):
            try:
                trurl = base64.b64decode(li['data-src']).decode('utf-8')
            except Exception:
                continue
            vidtxt = li.get_text(' ', strip=True)
            vidtxt = re.sub(r'^\d+\s*', '', vidtxt).strip()
            try:
                ehtml = client.request(trurl, referer=url)
                embed = re.search(r'<iframe[^>]+src=["\']([^"\']+)', ehtml)
                if embed:
                    vidurl = embed.group(1)
                    if vidurl.startswith('//'):
                        vidurl = 'https:' + vidurl
                    self.resolve_media('{0}|Referer={1}'.format(vidurl, self.bu), self.videos, vidtxt)
            except Exception:
                pass

        return sorted(self.videos)

    def get_video(self, url):
        return self.get_videos(url)
