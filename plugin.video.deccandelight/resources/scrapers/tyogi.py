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


class tyogi(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('tyogi', ['https://tamilyogi.legal/'], 'genre/tamil/', 'movie-card')
        self.icon = self.ipath + 'tyogi.png'

    def get_menu(self):
        html = client.request(self.bu)
        items = {}
        mlink = SoupStrainer('li', {'class': re.compile('menu-item')})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        sno = 1
        for li in mdiv.find_all('li'):
            a = li.find('a')
            if not a or not a.get('href'):
                continue
            title = a.text.strip()
            if not title or title.lower() == 'home':
                continue
            url = urllib_parse.urljoin(self.bu, a.get('href'))
            items['%02d' % sno + title] = url
            sno += 1
        items['%02d' % sno + '[COLOR yellow]** Search **[/COLOR]'] = self.bu + '?s='
        return (items, 7, self.icon)

    def get_items(self, iurl):
        movies = []
        if iurl[-3:] == '?s=':
            search_text = self.get_SearchQuery('TamilYogi')
            search_text = urllib_parse.quote_plus(search_text)
            iurl += search_text

        nmode = 8
        html = client.request(iurl)

        mlink = SoupStrainer('article', {'class': 'movie-card'})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        items = mdiv.find_all('article', {'class': 'movie-card'})

        plink = SoupStrainer('div', {'class': 'pagination'})
        Paginator = BeautifulSoup(html, "html.parser", parse_only=plink)

        for item in items:
            a = item.find('a')
            if not a or not a.get('href'):
                continue
            url = urllib_parse.urljoin(self.bu, a.get('href'))
            title = item.find('h3').text.strip()
            if ')' in title and '-series' not in iurl and '/tvshows' not in iurl:
                title = title.split(')')[0] + ')'
            try:
                img = item.find('img')
                thumb = img.get('data-src') or img.get('src')
                if thumb and thumb.startswith('/'):
                    thumb = urllib_parse.urljoin(self.bu, thumb)
                if not thumb:
                    thumb = self.icon
            except:
                thumb = self.icon
            movies.append((title, thumb, url))

        nextli = Paginator.find('a', {'class': re.compile('next')})
        if nextli and nextli.get('href'):
            purl = nextli.get('href')
            try:
                currpg = Paginator.find('span', {'class': re.compile('current')}).text.strip()
                nums = [a.text.strip() for a in Paginator.find_all('a', {'class': 'page-numbers'})
                        if a.text.strip().isdigit()]
                lastpg = nums[-1] if nums else currpg
                pgtxt = '{0} of {1}'.format(currpg, lastpg)
            except:
                pgtxt = purl.rstrip('/').split('/')[-1]
            title = 'Next Page... (Currently in Page {0})'.format(pgtxt)
            movies.append((title, self.nicon, purl))

        return (movies, nmode)

    def get_videos(self, url):
        videos = []

        html = client.request(url, headers=self.hdr)
        mlink = SoupStrainer('button', {'class': re.compile('v3-btn')})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        links = videoclass.find_all('button')
        if not links:
            for vidurl in re.findall(r'data-url=["\']([^"\']+)', html):
                self.resolve_media(vidurl + '$${0}'.format(self.bu), videos)
            return videos

        for link in links:
            vidurl = link.get('data-url')
            if not vidurl:
                continue
            vidurl = vidurl.replace(' ', '') + '$${0}'.format(self.bu)
            vidtxt = link.text.strip()
            self.resolve_media(vidurl, videos, vidtxt=vidtxt)

        return videos

    def get_video(self, url):
        html = client.request(url, referer=self.bu)
        eurls = re.findall(r'data-url=["\']([^"\']+)', html)
        for eurl in eurls:
            eurl = eurl.replace(' ', '') + '$${0}'.format(self.bu)
            if self.hmf(eurl):
                return eurl

        self.log('{0} not resolvable.\n'.format(url), 'info')
        return
