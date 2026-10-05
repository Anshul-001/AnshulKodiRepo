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
from resources.lib.htmlutils import absolute, append_next, document, thumbnail
from six.moves import urllib_parse


class yodesi(Scraper):
    def __init__(self):
        Scraper.__init__(self)
        self.bu = self.resolve_domain('yodesi', ['https://www.yodesi.net/', 'https://yodesi.tv/'], '', 'latestPost')
        self.icon = self.ipath + 'yodesi.png'
        self.videos = []
        self.list = {'01Latest Episodes': self.bu}

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
                # WordPress reports a nonzero count for this empty archive.
                # Keep it hidden while empty and let it return when posts do.
                if cat.get('slug') == 'colors-awards-and-concerts':
                    page = client.request(cat['link'])
                    if page is not None and not document(page).select_one('article.latestPost, div.latestPost'):
                        continue
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
        if url.endswith('?s='):
            url += urllib_parse.quote_plus(self.get_SearchQuery('YoDesi'))
        soup = document(client.request(url))
        seen = set()
        for item in soup.select('article, div.latestPost'):
            heading = item.find(['h2', 'h3'])
            link = heading.find('a', href=True) if heading else None
            if not link:
                continue
            target = absolute(url, link.get('href'))
            title = self.clean_title(self.unescape(link.get_text(' ', strip=True)))
            if not target or not title or target in seen:
                continue
            seen.add(target)
            movies.append((title, thumbnail(item, url, self.icon), target))
        append_next(movies, soup, url, self.nicon)
        return (movies, 8)

    def get_videos(self, url):
        self.videos = []
        seen = set()

        def extract(page, source):
            content = page.select_one('.thecontent, .entry-content, .single-post-video, article#the-post, article') or page
            for item in content.select('iframe, a[target="_blank"], a[rel="nofollow"]'):
                target = absolute(source, item.get('src') or item.get('data-litespeed-src') or item.get('data-src') or item.get('href'))
                if not target or target in seen or any(host in target for host in ('facebook.com/', 'twitter.com/', 'pinterest.com/', 'linkedin.com/')):
                    continue
                seen.add(target)
                self.resolve_media(target, self.videos, item.get_text(' ', strip=True))

        soup = document(client.request(url))
        extract(soup, url)
        if not seen:
            # Some "Video Episode" posts contain only a related Watch Online
            # link. Follow one matching show/date on this site, never a different
            # episode or an arbitrary related article.
            parsed = urllib_parse.urlsplit(url)
            prefix = re.match(r'(.+?-\d+(?:st|nd|rd|th)-[a-z]+-\d{4})-', parsed.path, re.I)
            if prefix:
                wanted = prefix.group(1) + '-watch-online/'
                for link in soup.find_all('a', href=True):
                    target = absolute(url, link.get('href'))
                    candidate = urllib_parse.urlsplit(target)
                    if candidate.netloc == parsed.netloc and candidate.path == wanted and target != url:
                        extract(document(client.request(target)), target)
                        break
        return sorted(self.videos)
