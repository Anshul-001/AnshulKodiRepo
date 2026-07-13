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


class hflinks(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('hflinks', ['https://hindilinks4u.foundation/'], 'genre/bollywood/', 'ml-item')
        self.icon = self.ipath + 'hflinks.png'

        self.list = {'01Dual Audio': self.bu + 'genre/dual-audio/',
                     '02Bollywood': self.bu + 'genre/bollywood/',
                     '03New Movies': self.bu + 'release-year/2026/',
                     '04Trending': self.bu + 'genre/top-rated/',
                     '05Hindi Web Series': self.bu + 'genre/web-series/',
                     '06Hollywood': self.bu + 'genre/hollywood/',
                     '07Hollywood Dubbed': self.bu + 'genre/hollywood-dubbed/',
                     '08South Dubbed': self.bu + 'genre/south-special/',
                     '09English Series': self.bu + 'series/',
                     '10Action': self.bu + 'genre/action/',
                     '11Adventure': self.bu + 'genre/adventure/',
                     '12Comedy': self.bu + 'genre/comedy/',
                     '13Crime': self.bu + 'genre/crime/',
                     '14Drama': self.bu + 'genre/drama/',
                     '15Horror': self.bu + 'genre/horror/',
                     '16Thriller': self.bu + 'genre/thriller/',
                     '97[COLOR cyan]Adult Erotic Movies[/COLOR]': self.bu + 'genre/erotic-movies/',
                     '99[COLOR yellow]** Search **[/COLOR]': self.bu + '?s='}

    def get_menu(self):
        return (self.list, 7, self.icon)

    def get_items(self, url):
        movies = []
        if url[-3:] == '?s=':
            search_text = self.get_SearchQuery('FilmLinks4U')
            search_text = urllib_parse.quote_plus(search_text)
            url = url + search_text

        html = client.request(url.replace('&amp;', '&'))
        mlink = SoupStrainer('div', {'class': 'movies-list movies-list-full'})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        plink = SoupStrainer('div', {'id': 'pagination'})
        Paginator = BeautifulSoup(html, "html.parser", parse_only=plink)
        items = mdiv.find_all('div', {'class': re.compile('^ml-item')})
        for item in items:
            title = self.unescape(item.find('a')['oldtitle'])
            title = self.clean_title(title)
            iurl = item.find('a')['href']
            try:
                thumb = item.find('img')['data-original']
            except:
                thumb = self.icon
            movdet = item.find('div', {'id': 'hidden_tip'})
            if 'Adult' not in movdet.text and 'Erotic' not in movdet.text:
                movies.append((title, thumb, iurl))
            elif self.adult:
                movies.append((title, thumb, iurl))

        r = re.search('class="active".+?href="([^"]+)', str(Paginator))
        if r:
            currpg = Paginator.find('li', {'class': 'active'}).text.strip()
            lastpg = Paginator.find_all('li')[-1].find('a')['href'].split('/')[-2]
            title = 'Next Page.. (Currently in Page {} of {})'.format(currpg, lastpg)
            movies.append((title, self.nicon, r.group(1)))

        return (movies, 8)

    def get_videos(self, url):
        videos = []

        html = client.request(url)
        mlink = SoupStrainer('div', {'itemprop': 'description'})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)
        mlink1 = SoupStrainer('div', {'id': 'player2'})
        videoclass1 = BeautifulSoup(html, "html.parser", parse_only=mlink1)

        try:
            vtabs = videoclass.find_all('a')
            for vtab in vtabs:
                videourl = vtab.get('href')
                if 'speedostream' in videourl or 'embdproxy' in videourl:
                    videourl = '{0}|Referer={1}'.format(videourl, self.bu)
                self.resolve_media(videourl, videos)
        except:
            pass

        try:
            vtabs = videoclass1.find_all('div', {'class': re.compile('movieplay')})
            for vtab in vtabs:
                if vtab.find('iframe') is not None:
                    videourl = vtab.find('iframe')['src']
                    if 'speedostream' in videourl or 'embdproxy' in videourl:
                        videourl = '{0}|Referer={1}'.format(videourl, self.bu)
                    self.resolve_media(videourl, videos)
        except:
            pass

        return videos
