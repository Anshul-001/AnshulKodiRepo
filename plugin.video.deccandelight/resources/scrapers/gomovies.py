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
import re
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import client
from resources.lib.base import Scraper
from six.moves import urllib_parse


class gomovies(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('gomovies', ['https://ogomovies.org/'], 'category/tamil-movies/', 'loop-entry') + 'category/'
        self.icon = self.ipath + 'gomovies.png'

        self.list = {'01Tamil Movies': self.bu + 'tamil-movies/',
                     '02Telugu Movies': self.bu + 'telugu-movies/',
                     '03Malayalam Movies': self.bu + 'malayalam-movies/',
                     '04Kannada Movies': self.bu + 'kannada-movies/',
                     '05Hindi Movies': self.bu + 'bollywood-movies/',
                     '06Punjabi Movies': self.bu + 'punjabi-movies/',
                     '07Multi Audio Movies': self.bu + 'multi-language-movies/',
                     '08Hollywood': self.bu + 'hollywood-movies/',
                     '09Hindi Dubbed': self.bu + 'hindi-dubbed-movies/',
                     '10Dual Audio': self.bu + 'dual-audio/',
                     '11South Indian': self.bu + 'south-indian-movies/',
                     '12Netflix Movies': self.bu + 'netflix-movies/',
                     '50Web Series': self.bu + 'web-series/',
                     '51TV Shows': self.bu + 'tv-shows/',
                     '99[COLOR yellow]** Search **[/COLOR]': self.bu[:-9] + '?s='}

    def get_menu(self):
        return (self.list, 7, self.icon)

    def get_items(self, url):
        movies = []
        if url[-3:] == '?s=':
            search_text = self.get_SearchQuery('GoMovies')
            search_text = urllib_parse.quote_plus(search_text)
            url = url + search_text

        html = client.request(url, verify=False)
        mlink = SoupStrainer('article', {'class': re.compile('loop-entry')})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        plink = SoupStrainer('div', {'class': 'nav-links'})
        Paginator = BeautifulSoup(html, "html.parser", parse_only=plink)
        items = mdiv.find_all('article')

        for item in items:
            hdr = item.find(['h1', 'h2', 'h3'], {'class': 'entry-title'})
            if not hdr or not hdr.find('a'):
                continue
            link = hdr.find('a')
            title = self.unescape(link.text).strip()
            title = title.encode('utf-8') if self.PY2 else title
            iurl = link['href']

            try:
                img = item.find('img')
                thumb = img.get('data-src') or img.get('src')
                if not thumb or thumb.startswith('data:'):
                    srcset = img.get('data-srcset') or img.get('srcset') or ''
                    thumb = srcset.split(' ')[0] if srcset else self.icon
            except:
                thumb = self.icon

            movies.append((title, thumb, iurl))

        nextli = Paginator.find('a', {'class': 'next'})
        if nextli and nextli.get('href'):
            purl = nextli['href']
            currpg = Paginator.find('span', {'class': 'current'})
            currpg = currpg.text.strip() if currpg else '1'
            title = 'Next Page.. (Currently in Page {})'.format(currpg)
            movies.append((title, self.nicon, purl))

        return (movies, 8)

    def get_videos(self, url):
        videos = []
        html = client.request(url, verify=False)
        mlink = SoupStrainer('div', {'class': re.compile('entry-content')})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        links = videoclass.find_all('a', href=True)
        for link in links:
            iurl = link['href']
            if self.bu[:-9] in iurl or 'np-downloader' in iurl or iurl.endswith('.srt'):
                continue
            self.resolve_media(iurl, videos)

        try:
            for frame in videoclass.find_all('iframe'):
                iurl = frame.get('src') or frame.get('data-src') or frame.get('data-litespeed-src')
                if iurl:
                    if iurl.startswith('//'):
                        iurl = 'https:' + iurl
                    self.resolve_media(iurl, videos)
        except:
            pass

        return videos
