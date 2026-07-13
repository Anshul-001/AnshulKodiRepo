'''
movierulz deccandelight plugin
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

# MovieRulz hops domains constantly. This list spans the current
# families; the probe below picks the first one that actually serves
# the expected listing markup from the user's network, cached 8h.
# When all of these die, add whichever mirror loads in a browser.
MIRRORS = [
    'https://www.5movierulz.support/',
    'https://www.5movierulz.voto/',
    'https://www.5movierulz.gdn/',
    'https://www.5movierulz.discount/',
    'https://www.5movierulz.limited/',
    'https://www.5movierulz.repair/',
    'https://www.5movierulz.fan/',
]


class mrulz(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        base = self.first_working_mirror(MIRRORS, 'category/telugu-movies/', 'boxed film')
        self.bu = base + 'category/'
        self.icon = self.ipath + 'mrulz.png'
        self.list = {'01Tamil Movies': self.bu + 'tamil-movies/',
                     '02Telugu Movies': self.bu + 'telugu-movies/',
                     '03Malayalam Movies': self.bu + 'malayalam-movies/',
                     '04Kannada Movies': self.bu + 'kannada-movies/',
                     '11Hindi Movies': self.bu + 'bollywood-movie/',
                     '21English Movies': self.bu + 'hollywood-movies/',
                     '31Tamil Dubbed Movies': self.bu + 'tamil-dubbed-movies/',
                     '32Telugu Dubbed Movies': self.bu + 'telugu-dubbed-movies/',
                     '33Hindi Dubbed Movies': self.bu + 'hindi-dubbed-movies/',
                     '34Bengali Movies': self.bu + 'bengali-movies/',
                     '35Punjabi Movies': self.bu + 'punjabi-movies/',
                     '41[COLOR cyan]Adult Movies[/COLOR]': self.bu + 'adult-movies/',
                     '42[COLOR cyan]Adult 18+[/COLOR]': self.bu + 'adult-18/',
                     '99[COLOR yellow]** Search **[/COLOR]': self.bu[:-9] + '?s='}

    def get_menu(self):
        return (self.list, 7, self.icon)

    def get_items(self, url):
        movies = []
        if url[-3:] == '?s=':
            search_text = self.get_SearchQuery('Movie Rulz')
            search_text = urllib_parse.quote_plus(search_text)
            url = url + search_text

        html = client.request(url, headers=self.hdr)
        mlink = SoupStrainer('div', {'id': 'list'})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        plink = SoupStrainer('div', {'class': 'pagination'})
        Paginator = BeautifulSoup(html, "html.parser", parse_only=plink)
        items = mdiv.find_all('div', {'class': 'boxed film'})

        for item in items:
            title = self.unescape(item.text)
            if ')' in title:
                title = title.split(')')[0] + ')'
            title = self.clean_title(title)
            url = item.find('a')['href']
            try:
                thumb = item.find('img')['src']
            except:
                thumb = self.icon
            movies.append((title, thumb, url))

        nextli = Paginator.find('a', string=re.compile(r'Next'))
        if nextli and nextli.get('href'):
            purl = nextli['href']
            pages = [p for p in purl.split('/') if p]
            try:
                currpg = int(pages[-1]) - 1
            except ValueError:
                currpg = 1
            title = 'Next Page.. (Currently in Page {})'.format(currpg)
            movies.append((title, self.nicon, purl))

        return (movies, 8)

    def get_videos(self, url):
        videos = []

        html = client.request(url, headers=self.hdr)
        mlink = SoupStrainer('div', {'class': 'entry-content'})
        videoclass = BeautifulSoup(html, "html.parser", parse_only=mlink)

        try:
            links = videoclass.find_all('a')
            for link in links:
                vidurl = link.get('href')
                self.resolve_media(vidurl, videos)
        except:
            pass

        r = re.search(r'var\s*locations\s*=\s*([^;]+)', html)
        if r:
            links = json.loads(r.group(1))
            for link in links:
                if 'vcdnlare' in link or 'uperbox' in link:
                    link += '$${0}'.format(url)
                self.resolve_media(link, videos)

        return videos
