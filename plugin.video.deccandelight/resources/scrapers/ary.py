'''
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
'''
import json
import re
from six.moves import urllib_parse
from resources.lib import client
from resources.lib.base import Scraper
from resources.lib.htmlutils import absolute, append_next, document, thumbnail


class ary(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = 'https://arydigital.tv/'
        self.icon = self.ipath + 'ary.png'
        self.list = {'01On Air Dramas': 'on-air',
                     '02Current Dramas': 'popularplaylists',
                     '03Finished Dramas': 'archiveplaylists',
                     '04Latest Videos': 'latestvideosMMMM7'}

    def get_menu(self):
        return (self.list, 5, self.icon)

    def get_second(self, iurl):
        shows = []
        soup = document(client.request(self.bu))
        tag = soup.find('script', id='__NEXT_DATA__')
        try:
            data = json.loads(tag.string or tag.get_text()) if tag else {}
        except (TypeError, ValueError):
            data = {}
        props = data.get('props', {}).get('pageProps', {})
        key = {'on-air': 'onAir', 'popularplaylists': 'mustWatch', 'archiveplaylists': 'archive'}.get(iurl, iurl)
        items = props.get(key, [])
        for item in items if isinstance(items, list) else []:
            title = self.unescape(item.get('title', ''))
            slug = item.get('slug')
            if not title or not slug:
                continue
            link = next((a for a in soup.find_all('a', href=True) if a['href'].rstrip('/').endswith('/' + slug)), None)
            target = absolute(self.bu, link['href'] if link else item.get('media_type', 'drama') + '/' + slug)
            shows.append((title, item.get('poster') or item.get('img') or self.icon, target))
        if not shows and data.get('buildId'):
            raw = client.request('{0}_next/data/{1}/{2}.json'.format(self.bu, data['buildId'], iurl))
            try:
                legacy = json.loads(raw or '{}').get('pageProps', {}).get('data', {}) or {}
            except ValueError:
                legacy = {}
            for item in legacy.get('series', []) or []:
                if item.get('title') and item.get('seriesDM'):
                    image = absolute('https://node.aryzap.com/public/', item.get('imagePoster')) or self.icon
                    shows.append((self.unescape(item['title']), image, item['seriesDM']))
        return (shows, 7)

    def get_items(self, iurl):
        movies = []
        page = '1'
        if '#' in iurl:
            iurl, page = iurl.rsplit('#', 1)
        params = {'fields': 'title,thumbnail_360_url,id', 'page': page, 'limit': 50, 'sort': 'recent'}
        if iurl == 'latestvideos':
            plurl = 'https://api.dailymotion.com/user/arydigitalofficial/videos'
        elif iurl.startswith(self.bu):
            soup = document(client.request(iurl))
            tag = soup.find('script', id='__NEXT_DATA__')
            try:
                program = json.loads(tag.string or tag.get_text()).get('props', {}).get('pageProps', {}).get('program', {}) if tag else {}
            except (TypeError, ValueError):
                program = {}
            title = program.get('title')
            if not title:
                return (movies, 9)
            plurl = 'https://api.dailymotion.com/user/arydigitalofficial/videos'
            params['search'] = title
        else:
            plurl = 'https://api.dailymotion.com/playlist/{0}/videos'.format(iurl)
        raw = client.request(plurl, params=params)
        try:
            data = json.loads(raw or '{}')
        except ValueError:
            return (movies, 9)
        for item in data.get('list', []) or []:
            if item.get('id') and item.get('title'):
                target = 'https://www.dailymotion.com/video/' + item['id']
                movies.append((self.unescape(item['title']), item.get('thumbnail_360_url') or self.icon, target))
        if data.get('has_more'):
            movies.append(('Next Page...', self.nicon, '{0}#{1}'.format(iurl, int(page) + 1)))
        return (movies, 9)
