"""Small helpers shared by the HTML scrapers."""
import re

from bs4 import BeautifulSoup
from six import string_types
from six.moves import urllib_parse


def document(html):
    return BeautifulSoup(html or '', 'html.parser')


def absolute(base, href):
    if not isinstance(href, string_types):
        return ''
    href = href.strip()
    if not href or href.startswith(('#', 'javascript:', 'data:')):
        return ''
    url = urllib_parse.urljoin(base, href.strip())
    return url if urllib_parse.urlsplit(url).scheme in ('http', 'https') else ''


def thumbnail(item, base, fallback):
    img = item.find('img')
    if img:
        src = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
        return absolute(base, src) or fallback
    return fallback


def next_page(soup, current):
    link = soup.select_one('a[rel="next"], a.next, a.nextpostslink, #tie-next-page a')
    if not link:
        pages = soup.select_one('.pagination, .wp-pagenavi, .page-navigation')
        if pages:
            active = pages.select_one('li.active, span.current')
            sibling = active.find_next_sibling() if active else None
            if sibling and 'disabled' not in sibling.get('class', []):
                link = sibling if sibling.name == 'a' else sibling.find('a', href=True)
            if not link:
                link = next((a for a in pages.find_all('a', href=True)
                             if re.search(r'next|older|»|›', a.get_text(' ', strip=True), re.I)
                             and not (a.parent and 'disabled' in a.parent.get('class', []))), None)
    url = absolute(current, link.get('href')) if link else ''
    return url if url.rstrip('/') != current.rstrip('/') else ''


def append_next(items, soup, current, icon):
    url = next_page(soup, current)
    if url:
        items.append(('Next Page...', icon, url))
