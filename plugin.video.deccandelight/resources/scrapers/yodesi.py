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
from resources.lib import client
from resources.lib.base import Scraper
from six.moves import urllib_parse


class yodesi(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('yodesi', ['https://yodesionline.com/'], 'category/anupama-serial/', 'item-list')
        self.icon = self.ipath + 'yodesi.png'
        self.videos = []
        # The relaunched site is organised as one WordPress category per serial
        # (no channel grouping). get_menu fetches the live list; this static set
        # of popular serials is the fallback if that request fails.
        self.list = {'01Yeh Rishta Kya Kehlata Hai': self.bu + 'category/yeh-rishta-kya-kehlata-hai-serial/',
                     '02Kyunki Saas Bhi Kabhi Bahu Thi 2': self.bu + 'category/kyunki-saas-bhi-kabhi-bahu-thi-2/',
                     '03Anupama': self.bu + 'category/anupama-serial/',
                     '04Kyunki Rishton Ke Bhi Roop Badalte Hai': self.bu + 'category/kyunki-rishton-ke-bhi-roop-badalte-hai/',
                     '05Mannat': self.bu + 'category/mannat/',
                     '06Mr and Mrs Parshuram': self.bu + 'category/mr-and-mrs-parshuram/',
                     '07Seher Hone Ko Hai': self.bu + 'category/seher-hone-ko-hai/',
                     '08O Humnava Tum Dena Saath Mera': self.bu + 'category/o-humnava-tum-dena-saath-mera/',
                     '09Tu Juliet Jatt Di': self.bu + 'category/tu-juliet-jatt-di/',
                     '10Udne Ki Aasha': self.bu + 'category/udne-ki-aasha/',
                     '11Pushpa Impossible': self.bu + 'category/pushpa-impossible/',
                     '12Taarak Mehta Ka Ooltah Chashmah': self.bu + 'category/taarak-mehta-ka-ooltah-chashmah/',
                     '13Jhanak': self.bu + 'category/jhanak/',
                     '14Mangal Lakshmi': self.bu + 'category/mangal-lakshmi/',
                     '15Naagin 7': self.bu + 'category/naagin-7/'}

    def get_menu(self):
        mlist = self._categories()
        mlist.update({'99[COLOR yellow]** Search **[/COLOR]': self.bu + '?s=MMMM7'})
        return (mlist, 7, self.icon)

    def _categories(self):
        """
        Build the {NN Serial Name: category url} dict from the live WordPress
        REST endpoint, falling back to the static list on any failure.
        """
        try:
            data = client.request(self.bu + 'wp-json/wp/v2/categories?per_page=100')
            cats = json.loads(data)
            cats = [c for c in cats if c.get('link') and c.get('count', 0) > 0
                    and self.unescape(c.get('name', '')).lower() != 'uncategorized']
            cats.sort(key=lambda c: -c.get('count', 0))
            if not cats:
                raise ValueError('no categories')
            mlist = {}
            for ino, cat in enumerate(cats, 1):
                mlist['{0:02d}{1}'.format(ino, self.unescape(cat['name']))] = cat['link']
            return mlist
        except Exception:
            return dict(self.list)

    def get_second(self, iurl):
        """
        List the available serials (kept for API compatibility; the live menu
        goes straight to the episode listing).
        """
        shows = []
        for title, url in sorted(self._categories().items()):
            title = re.sub(r'^\d+', '', title)
            shows.append((title, self.icon, url))
        return (shows, 7)

    def get_items(self, url):
        movies = []
        if url[-3:] == '?s=':
            search_text = self.get_SearchQuery('YoDesi')
            search_text = urllib_parse.quote_plus(search_text)
            url = url + search_text
        html = client.request(url)
        mlink = SoupStrainer('article', {'class': re.compile('item-list')})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        items = mdiv.find_all('article')

        for item in items:
            head = item.find('h2', {'class': 'post-box-title'}) or item
            link = head.find('a')
            if not link:
                continue
            title = self.unescape(link.get_text(strip=True))
            title = self.clean_title(title)
            url = link.get('href')
            img = item.find('img')
            try:
                thumb = img.get('data-src') or img.get('src')
            except AttributeError:
                thumb = self.icon
            movies.append((title, thumb or self.icon, url))

        plink = SoupStrainer('div', {'class': 'pagination'})
        Paginator = BeautifulSoup(html, "html.parser", parse_only=plink)
        nextpg = Paginator.find('span', {'id': 'tie-next-page'})
        if nextpg and nextpg.find('a'):
            purl = nextpg.find('a').get('href')
            curr = Paginator.find('span', {'class': 'current'})
            currpg = curr.get_text(strip=True) if curr else '?'
            pages = Paginator.find('span', {'class': 'pages'})
            lastpg = re.search(r'of\s*([\d,]+)', pages.get_text()) if pages else None
            lastpg = lastpg.group(1) if lastpg else '?'
            title = 'Next Page.. (Currently in Page {0} of {1})'.format(currpg, lastpg)
            movies.append((title, self.nicon, purl))

        return (movies, 8)

    def get_videos(self, url):
        self.videos = []
        html = client.request(url)
        mlink = SoupStrainer('div', {'class': re.compile('single-post-video')})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)
        links = videoclass.find_all('iframe')
        if not links:
            mlink = SoupStrainer('article', {'id': 'the-post'})
            videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)
            links = videoclass.find_all('iframe')

        multi = len(links) > 1
        for idx, link in enumerate(links, 1):
            vidurl = link.get('src') or link.get('data-litespeed-src') or link.get('data-src')
            if not vidurl:
                continue
            if vidurl.startswith('//'):
                vidurl = 'https:' + vidurl
            vidtxt = 'Part {0}'.format(idx) if multi else ''
            self.resolve_media(vidurl, self.videos, vidtxt)

        links = videoclass.find_all('a', {'target': '_blank'})
        for link in links:
            vidurl = link.get('href')
            if not vidurl:
                continue
            vidtxt = self.unescape(link.text)
            vidtxt = re.search(r'(Part\s*\d+)', vidtxt, re.IGNORECASE)
            vidtxt = vidtxt.group(1) if vidtxt else ''
            self.resolve_media(vidurl, self.videos, vidtxt)

        return sorted(self.videos)
