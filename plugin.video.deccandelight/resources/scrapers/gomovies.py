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
import json
from six.moves import urllib_parse
from resources.lib import client
from resources.lib.base import Scraper
from resources.lib.htmlutils import absolute, append_next, document


class gomovies(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('gomovies', ['https://ogomovies.dev/'], 'genre/tamil/', 'ml-item')
        self.icon = self.ipath + 'gomovies.png'
        self.list = {'01Tamil Movies': self.bu + 'genre/tamil/',
                     '02Telugu Movies': self.bu + 'genre/telugu/',
                     '03Malayalam Movies': self.bu + 'genre/malayalam-movies/',
                     '04Hindi Movies': self.bu + 'genre/bollywood/',
                     '05Hollywood': self.bu + 'genre/hollywood/'}

    def get_menu(self):
        soup = document(client.request(self.bu))
        items, seen = {}, set()
        for link in soup.select('#menu a[href], .top-menu a[href]'):
            url = absolute(self.bu, link.get('href'))
            parsed = urllib_parse.urlsplit(url)
            if parsed.netloc != urllib_parse.urlsplit(self.bu).netloc or not parsed.path.startswith('/genre/'):
                continue
            # Current navigation contains duplicate trailing slashes.
            url = urllib_parse.urlunsplit(parsed._replace(path=re.sub(r'/+', '/', parsed.path), fragment=''))
            title = link.get_text(' ', strip=True)
            if not title or url in seen:
                continue
            seen.add(url)
            items['%02d%s' % (len(items) + 1, title)] = url
        if not items:
            items = dict(self.list)
        items['99[COLOR yellow]** Search **[/COLOR]'] = self.bu + '?s='
        return items, 7, self.icon

    def get_items(self, url):
        if url.endswith('?s='):
            return self._search(self.get_SearchQuery('0GoMovies').strip()), 8
        soup = document(client.request(url))
        movies, seen = [], set()
        listing = soup.select_one('.movies-list-full')
        cards = listing.select('.ml-item') if listing else soup.select('.ml-item, article.loop-entry')
        for item in cards:
            link = item.select_one('a.ml-mask[href], .entry-title a[href]')
            if not link:
                continue
            target = absolute(url, link.get('href'))
            heading = item.find(['h1', 'h2', 'h3'])
            title = link.get('oldtitle') or link.get('title') or (heading.get_text(' ', strip=True) if heading else '')
            if not target or not title or target in seen:
                continue
            seen.add(target)
            img = item.find('img')
            raw = (img.get('data-original') or img.get('data-src') or img.get('src')) if img else ''
            if not raw or raw.startswith('data:'):
                srcset = (img.get('data-srcset') or img.get('srcset') or '') if img else ''
                raw = srcset.split(' ')[0]
            thumb = absolute(url, raw) or self.icon
            if urllib_parse.urlsplit(target).path.startswith('/tv/'):
                target += 'MMMM6'
            movies.append((self.clean_title(title), thumb, target))
        append_next(movies, soup, url, self.nicon)
        return movies, 8

    def _search(self, query):
        if not query:
            return []
        raw = client.request(self.bu + 'wp-admin/admin-ajax.php',
                             params={'action': 'search_suggestions', 'keyword': query},
                             headers={'Referer': self.bu})
        try:
            payload = json.loads(raw or '{}')
            html = payload.get('content', '') if isinstance(payload, dict) else ''
        except (TypeError, ValueError):
            return []
        if not isinstance(html, str):
            return []
        items, seen = [], set()
        for item in document(html).select('li'):
            link = item.select_one('a.ss-title[href]')
            if not link:
                continue
            target = absolute(self.bu, link.get('href'))
            title = link.get_text(' ', strip=True)
            if not target or not title or target in seen:
                continue
            seen.add(target)
            image = item.select_one('a.thumb')
            match = re.search(r'url\((.*?)\)', image.get('style', '')) if image else None
            thumb = absolute(self.bu, match.group(1).strip('\"\'')) if match else self.icon
            if urllib_parse.urlsplit(target).path.startswith('/tv/'):
                target += 'MMMM6'
            items.append((title, thumb or self.icon, target))
        return items

    def _watch_page(self, url):
        soup = document(client.request(url))
        parsed = urllib_parse.urlsplit(url)
        expected = parsed.path.rstrip('/') + '/watching'
        for link in soup.select('a[href]'):
            target = absolute(url, link.get('href'))
            candidate = urllib_parse.urlsplit(target)
            if candidate.netloc == parsed.netloc and candidate.path.rstrip('/') == expected:
                return document(client.request(target)), target
        return soup, url

    def get_third(self, url):
        soup, watching = self._watch_page(url)
        parsed = urllib_parse.urlsplit(watching)
        rows, seen = [], set()
        for node in soup.select('.episode-item[id]'):
            match = re.fullmatch(r'episode-(\d+)', node.get('id', ''))
            if not match or match.group(1) in seen:
                continue
            seen.add(match.group(1))
            link = node.find('a')
            title = (link.get('title') if link else '') or node.get_text(' ', strip=True)
            query = dict(urllib_parse.parse_qsl(parsed.query))
            query['episode_id'] = match.group(1)
            target = urllib_parse.urlunsplit(parsed._replace(query=urllib_parse.urlencode(query)))
            rows.append((title.strip(), self.icon, target))
        def order(row):
            number = re.search(r'Episode\s*(\d+)', row[0], re.I)
            return int(number.group(1)) if number else 0
        rows.sort(key=order)
        return rows, 8

    def get_videos(self, url):
        # Follow only this title's public watching page, including series
        # query parameters. Never use trailers or related titles as servers.
        soup, url = self._watch_page(url)
        episode = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query)).get('episode_id')
        targets, seen = [], set()
        for node in soup.select('.episode-item'):
            if episode and node.get('id') != 'episode-' + episode:
                continue
            for key in ('data-drive', 'data-openload', 'data-streamgo', 'data-putload'):
                target = absolute(url, node.get(key))
                if target and target not in seen:
                    seen.add(target)
                    targets.append((node.get_text(' ', strip=True), target))
        for node in soup.select('#iframe-embed, .entry-content iframe, #player2 iframe'):
            target = absolute(url, node.get('src') or node.get('data-src') or node.get('data-litespeed-src'))
            if target and target not in seen:
                seen.add(target)
                targets.append(('', target))
        for link in soup.select('.entry-content a[href]'):
            target = absolute(url, link.get('href'))
            if (target and target not in seen and urllib_parse.urlsplit(target).netloc != urllib_parse.urlsplit(self.bu).netloc
                    and 'np-downloader' not in target and not urllib_parse.urlsplit(target).path.endswith('.srt')):
                seen.add(target)
                targets.append(('', target))
        videos = []
        for label, target in targets:
            self.resolve_media(target, videos, label)
        return videos
