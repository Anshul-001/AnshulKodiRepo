"""Regression checks for live site layouts, without a Kodi process or network."""
import importlib
import json
from pathlib import Path
import sys
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin.video.deccandelight'))

control = types.ModuleType('resources.lib.control')
control._ipath = 'images/'
control._ppath = ''
control.PY2 = False
control.get_setting = lambda key: 'false'
control.log = lambda *args: None
control.TRANSLATEPATH = lambda value: value
for name in ['mozhdr', 'droidhdr', 'jiohdr', 'ioshdr', 'chromehdr']:
    setattr(control, name, {'User-Agent': 'test'})
client = types.ModuleType('resources.lib.client')
client.request = lambda *args, **kwargs: None
cache = types.ModuleType('resources.lib.cache')
cache.get = lambda fn, hours, *args: fn(*args)
kodi = types.ModuleType('kodi_six')
kodi.xbmcvfs = types.SimpleNamespace(exists=lambda path: False)
for name, module in [('resources.lib.control', control), ('resources.lib.client', client),
                     ('resources.lib.cache', cache), ('kodi_six', kodi)]:
    sys.modules[name] = module

from resources.lib import base
from resources.lib.htmlutils import absolute, next_page, document

# Mirror probing is covered separately by the live audit. These tests isolate
# parser behavior, rather than depending on which external host answers today.
base.Scraper.resolve_domain = lambda self, site, mirrors, *args: mirrors[0]


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.pages = {}
        self.calls = []
        def request(url, **kwargs):
            self.calls.append((url, kwargs))
            return self.pages.get(url)
        client.request = request

    def scraper(self, name):
        module = importlib.import_module('resources.scrapers.' + name)
        return getattr(module, name)()

    def test_tamilgun_cards_lazy_images_and_pagination(self):
        obj = self.scraper('tgun')
        url = obj.bu + '/video-category/hd-movies/'
        self.pages[url] = '''<div class="image-item"><a class="image-link" href="/video/example/">
          <img data-src="/poster.jpg"><h3>Example &amp; More</h3></a></div>
          <a class="next page-numbers" href="page/2/">Next</a>'''
        items, mode = obj.get_items(url)
        self.assertEqual(mode, 8)
        self.assertEqual(items[0], ('Example & More', obj.bu + '/poster.jpg', obj.bu + '/video/example/'))
        self.assertEqual(items[-1][2], url + 'page/2/')

    def test_tamilgun_does_not_invent_retired_special_tv_category(self):
        obj = self.scraper('tgun')
        self.pages[obj.bu] = '<a class="cat-btn" href="/video-category/movies/">Movies</a>'
        menu, _, _ = obj.get_menu()
        self.assertEqual([k for k in menu if 'Search' not in k], ['01Movies'])

    def test_tamilgun_public_player_api_returns_hls_with_headers(self):
        obj = self.scraper('tgun')
        url = obj.bu + '/video/example/'
        player = 'https://player4.spirituallifewell.com/videos/abcd-1234'
        api = 'https://player4.spirituallifewell.com/api/playback/resolve'
        self.pages[url] = '<div id="player-1"><iframe src="' + player + '"></iframe></div>'
        self.pages[api] = json.dumps({'playbackOptions': [{'label': 'server 1', 'sourceUrl': 'https://cdn.example/movie.m3u8', 'isEmbed': False}]})
        videos = obj.get_videos(url)
        self.assertEqual(len(videos), 1)
        self.assertTrue(videos[0][1].startswith('https://cdn.example/movie.m3u8|Referer='))
        self.assertEqual(self.calls[-1][1]['params'], {'contentType': 'video', 'videoId': 'abcd-1234'})

    def test_tamilgun_api_failures_and_nonmedia_urls_are_not_streams(self):
        obj = self.scraper('tgun')
        player = 'https://player4.spirituallifewell.com/videos/abcd'
        api = 'https://player4.spirituallifewell.com/api/playback/resolve'
        for data in ['invalid', '[]', json.dumps({'sourceUrl': 'javascript:bad()'}), json.dumps({'sourceUrl': 'https://cdn.example/login.html'})]:
            self.pages[api] = data
            videos = []
            self.assertTrue(obj._public_player(player, videos))
            self.assertEqual(videos, [])
        self.assertFalse(obj._public_player('https://other.example/videos/abcd', []))

    def test_todaypk_current_cards(self):
        obj = self.scraper('todaypk')
        url = obj.bu + 'tamil-movies'
        self.pages[url] = '''<div class="boxed film"><a href="/example/full-movie.html" title="Example (2026)">
          <img src="/poster.jpg"></a><p><b>Example (2026)</b></p></div>'''
        items, mode = obj.get_items(url)
        self.assertEqual(mode, 8)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][2], 'https://todaypk.biz/example/full-movie.html')

    def test_todaypk_javascript_server_array_is_parsed_as_data(self):
        obj = self.scraper('todaypk')
        url = 'https://todaypk.biz/example.html'
        self.pages[url] = r'''<script>var locations = ["https:\/\/streamtape.to\/e\/example","https://dood.to/e/example"];</script>'''
        found = []
        obj.resolve_media = lambda target, videos, *args: found.append(target)
        obj.get_videos(url)
        self.assertEqual(found, ['https://streamtape.to/e/example', 'https://dood.to/e/example'])

    def test_todaypk_video_links_exclude_category_and_ad_navigation(self):
        obj = self.scraper('todaypk')
        url = 'https://todaypk.biz/example.html'
        self.pages[url] = '<div class="entry-content"><a href="/genre/action">Action</a><a href="/watchfree.php">Ad</a><a href="//mixdrop.ag/f/example">MixDrop</a></div>'
        found = []
        obj.resolve_media = lambda target, videos, *args: found.append(target)
        obj.get_videos(url)
        self.assertEqual(found, ['https://mixdrop.ag/f/example'])

    def test_todaypk_public_pkspeed_sources_include_quality_and_headers(self):
        obj = self.scraper('todaypk')
        url = 'https://pkembed.site/example'
        self.pages[url] = '<video><source src="https://cdn.example/movie.mp4" title="480p"><source src="javascript:bad()"></video>'
        videos = []
        obj._resolve_server(url, videos)
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0][0], 'PkSpeed 480p')
        self.assertTrue(videos[0][1].startswith('https://cdn.example/movie.mp4|Referer='))
        self.assertEqual(obj._resolve_server(url + '/missing', []), None)

    def test_desitellybox_channels_and_relative_show_links(self):
        obj = self.scraper('desit')
        self.pages[obj.bu] = '''<div class="td-fix-index"><strong>Star Plus</strong><img src="/star.jpg">
           <ul><li><a href="/category/star-plus/example/">Example</a></li></ul></div>'''
        menu, _, _ = obj.get_menu()
        self.assertEqual(menu['01Star Plus'], 'Star Plus')
        shows, mode = obj.get_second('Star Plus')
        self.assertEqual(mode, 7)
        self.assertEqual(shows[0][2], obj.bu + 'category/star-plus/example/')

    def test_desitellybox_excludes_written_updates_and_keeps_episode_links(self):
        obj = self.scraper('desit')
        url = obj.bu + 'category/example/'
        self.pages[url] = '''<h3 class="entry-title"><a href="/episode/">Example Watch Online</a></h3>
          <h3 class="entry-title"><a href="/text/">Example Written Update</a></h3>'''
        items, _ = obj.get_items(url)
        self.assertEqual([item[2] for item in items], [obj.bu + 'episode/'])

    def test_geetmala_internal_routes_filter_years_from_letters(self):
        obj = self.scraper('gmala')
        self.pages[obj.bu + '/'] = '''<a href="/movie/a.php">A</a><a href="/movie/1960.php">1960</a>
          <a href="/singer/a.php">A</a><a href="/movie/a.php">A</a>'''
        letters, _ = obj.get_top(obj.bu + '/ZZZZTitles')
        years, _ = obj.get_top(obj.bu + '/ZZZZYearwise')
        self.assertEqual([item[0] for item in letters], ['A'])
        self.assertEqual([item[0] for item in years], ['1960'])

    def test_geetmala_songs_are_deduplicated(self):
        obj = self.scraper('gmala')
        url = obj.bu + '/movie/example.htm'
        self.pages[url] = '<a href="/song/example.htm"></a><a href="/song/example.htm">Example Song</a>'
        items, mode = obj.get_items(url)
        self.assertEqual(mode, 9)
        self.assertEqual(items, [('Example Song', obj.icon, obj.bu + '/song/example.htm')])

    def test_ary_modern_program_data_and_official_episode_search(self):
        obj = self.scraper('ary')
        self.pages[obj.bu] = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {
            'onAir': [{'title': 'Example Drama', 'slug': 'example', 'media_type': 'drama'}]}}}) + '</script>'
        shows, _ = obj.get_second('on-air')
        self.assertEqual(shows[0][2], obj.bu + 'drama/example')
        self.pages[shows[0][2]] = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {
            'program': {'title': 'Example Drama'}}}}) + '</script>'
        api = 'https://api.dailymotion.com/user/arydigitalofficial/videos'
        self.pages[api] = json.dumps({'list': [{'id': 'x123', 'title': 'Example Episode 1'}], 'has_more': False})
        items, mode = obj.get_items(shows[0][2])
        self.assertEqual(mode, 9)
        self.assertEqual(items[0][2], 'https://www.dailymotion.com/video/x123')
        self.assertEqual(self.calls[-1][1]['params']['search'], 'Example Drama')

    def test_ary_missing_or_malformed_json_is_empty_without_exception(self):
        obj = self.scraper('ary')
        self.pages[obj.bu] = '<script id="__NEXT_DATA__">invalid</script>'
        self.assertEqual(obj.get_second('on-air'), ([], 7))
        self.assertEqual(obj.get_items('latestvideos'), ([], 9))

    def test_yodesi_newspaper_articles_and_lazy_images(self):
        obj = self.scraper('yodesi')
        url = obj.bu + 'category/example/'
        self.pages[url] = '''<article class="latestPost"><img data-src="/poster.jpg">
          <h2 class="front-view-title"><a href="/episode/">Example Episode</a></h2></article>'''
        items, mode = obj.get_items(url)
        self.assertEqual(mode, 8)
        self.assertEqual(items[0][2], obj.bu + 'episode/')

    def test_yodesi_current_host_links_and_social_links_are_filtered(self):
        obj = self.scraper('yodesi')
        url = obj.bu + 'episode/'
        self.pages[url] = '''<div class="thecontent"><a target="_blank" href="https://tvcine.me/player.php?id=1">Full Episode</a>
          <a target="_blank" href="https://facebook.com/share">Share</a></div>'''
        found = []
        obj.resolve_media = lambda target, videos, *args: found.append(target)
        obj.get_videos(url)
        self.assertEqual(found, ['https://tvcine.me/player.php?id=1'])

    def test_desitellybox_current_player_section_and_reset_between_episodes(self):
        obj = self.scraper('desit')
        url = obj.bu + 'episode/'
        self.pages[url] = '<div class="td-post-content"><a href="//business-credits.cc/media.php?id=1">Part 1</a></div>'
        obj.resolve_media = lambda target, videos, *args: videos.append((args[0], target))
        self.assertEqual(obj.get_videos(url), [('Part 1', 'https://business-credits.cc/media.php?id=1')])
        self.assertEqual(obj.get_videos(url + 'missing'), [])

    def test_yodesi_placeholder_follows_only_matching_show_and_date(self):
        obj = self.scraper('yodesi')
        url = obj.bu + 'example-4th-october-2026-video-episode-10/'
        correct = obj.bu + 'example-4th-october-2026-watch-online/'
        self.pages[url] = '<article><a href="/other-4th-october-2026-watch-online/">Other show</a><a href="/example-3rd-october-2026-watch-online/">Yesterday</a><a href="' + correct + '">Watch</a></article>'
        self.pages[correct] = '<div class="thecontent"><iframe src="https://tvcine.me/player.php?id=1"></iframe></div>'
        found = []
        obj.resolve_media = lambda target, videos, *args: found.append(target)
        obj.get_videos(url)
        self.assertEqual(found, ['https://tvcine.me/player.php?id=1'])
        self.assertEqual([call[0] for call in self.calls], [url, correct])

    def test_yodesi_placeholder_does_not_recurse_or_follow_other_sites(self):
        obj = self.scraper('yodesi')
        url = obj.bu + 'example-4th-october-2026-video-episode-10/'
        self.pages[url] = '<a href="https://other.example/example-4th-october-2026-watch-online/">Watch</a>'
        self.assertEqual(obj.get_videos(url), [])
        self.assertEqual(len(self.calls), 1)

    def test_todaypk_menu_excludes_provider_error_categories(self):
        obj = self.scraper('todaypk')
        self.pages[obj.bu[:-9]] = '<nav><a href="/category/tamil-movies">Tamil</a><a href="/category/malayalam-movies">Malayalam</a><a href="/category/tv-shows">TV Shows</a></nav>'
        menu, _, _ = obj.get_menu()
        self.assertEqual([title for title in menu if 'Search' not in title], ['01Tamil'])

    def test_yodesi_stale_archive_returns_when_posts_are_available(self):
        obj = self.scraper('yodesi')
        api = obj.bu + 'wp-json/wp/v2/categories?per_page=100'
        archive = obj.bu + 'category/colors/colors-awards-and-concerts/'
        self.pages[api] = json.dumps([{'name': 'Concerts', 'slug': 'colors-awards-and-concerts', 'count': 100, 'link': archive},
                                     {'name': 'Example', 'slug': 'example', 'count': 200, 'link': obj.bu + 'category/example/'}])
        self.pages[archive] = '<h1>Concerts</h1>'
        self.assertNotIn(archive, obj._categories().values())
        self.pages[archive] = '<article class="latestPost"><h2>New episode</h2></article>'
        self.assertIn(archive, obj._categories().values())

    def test_missing_http_documents_do_not_crash_changed_listing_parsers(self):
        for name in ['tgun', 'todaypk', 'desit', 'gmala', 'yodesi']:
            obj = self.scraper(name)
            self.assertEqual(obj.get_items(obj.bu + 'empty/')[0], [], name)

    def test_pagination_does_not_repeat_current_or_follow_disabled_last_page(self):
        url = 'https://example.org/list'
        self.assertEqual(next_page(document('<a rel="next" href="/list">Next</a>'), url), '')
        html = '<ul class="pagination"><li class="active">2</li><li class="disabled"><a href="?page=3">Next</a></li></ul>'
        self.assertEqual(next_page(document(html), url), '')
        self.assertEqual(absolute(url, 'javascript:alert(1)'), '')
        self.assertEqual(absolute(url, {'invalid': 'url'}), '')
        self.assertEqual(absolute(url, ' #navigation'), '')


if __name__ == '__main__':
    unittest.main()
