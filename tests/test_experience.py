"""Behavior checks for real application routes, caching, HTTP and playback fallback."""
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import test_scrapers as stubs
from resources.lib import collection, parallel, streams

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'plugin.video.deccandelight/resources/lib' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KodiControlTests(unittest.TestCase):
    def test_control_imports_real_progress_factory_from_strict_sdk(self):
        addon = types.SimpleNamespace(getAddonInfo=lambda key: '21.0' if key == 'version' else key)
        progress = type('DialogProgress', (), {})
        kodi = types.SimpleNamespace(
            xbmc=types.SimpleNamespace(getInfoLabel=lambda key: '21.1', LOGINFO=1,
                                      Keyboard=object, getUserAgent=lambda: 'Kodi', sleep=lambda ms: None),
            xbmcaddon=types.SimpleNamespace(Addon=lambda: addon),
            xbmcvfs=types.SimpleNamespace(translatePath=lambda path: path),
            xbmcgui=types.SimpleNamespace(ListItem=Item, Dialog=object, DialogProgress=progress),
            xbmcplugin=types.SimpleNamespace(addDirectoryItems=lambda *a: None,
                                            setResolvedUrl=lambda *a: None,
                                            setContent=lambda *a: None, endOfDirectory=lambda *a: None))
        with patch.dict(sys.modules, {'kodi_six': kodi}), patch.object(sys, 'argv', ['plugin://test/', '1', '']):
            control = load('native_control', 'control.py')
        self.assertIs(control.DialogProgress, progress)
        self.assertIsInstance(control.DialogProgress(), progress)


class Tag:
    def __init__(self):
        self.values = {}
    def __getattr__(self, name):
        return lambda *args: self.values.__setitem__(name, args)


class Item:
    def __init__(self, label='', path='', **kwargs):
        self.label, self.path, self.art, self.properties, self.context = label, path, {}, {}, []
        self.tag = Tag()
    def setArt(self, values): self.art.update(values)
    def setProperty(self, key, value): self.properties[key] = value
    def setLabel(self, label): self.label = label
    def setPath(self, path): self.path = path
    def getPath(self): return self.path
    def getVideoInfoTag(self): return self.tag
    def setMimeType(self, value): self.mime = value
    def setContentLookup(self, value): pass
    def setSubtitles(self, value): self.subs = value
    def addContextMenuItems(self, values): self.context.extend(values)


class Progress:
    def create(self, *args): pass
    def update(self, *args): pass
    def iscanceled(self): return False
    def close(self): pass


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rows, self.resolved, self.messages = [], [], []
        self.settings = {'version': '2.3.0', 'meta': 'false', 'autoplay': 'true', 'timeout': '6'}
        self.settings.update({site: 'true' for site in ['tgun', 'todaypk', 'yodesi', 'ary']})
        values = {
            '_version': '2.3.0', '_path': str(ROOT / 'plugin.video.deccandelight'),
            '_url': 'plugin://plugin.video.deccandelight/', '_handle': 1,
            '_ppath': self.tmp.name + '/', '_icon': 'icon.png', '_fanart': 'fanart.jpg',
            '_listitem': Item, 'kodiver': 21.2, 'DialogProgress': Progress,
            '_addon': types.SimpleNamespace(setSetting=lambda k,v: self.settings.__setitem__(k,v)),
            'get_setting': lambda key: self.settings.get(key, 'false'),
            'notify': lambda msg,*args: self.messages.append(msg),
            'addDir': lambda handle,rows,count: self.rows.extend(rows),
            'setContent': lambda *args: None, 'eod': lambda *args,**kwargs: None,
            'setResolvedUrl': lambda handle,success,item=None,**kwargs: self.resolved.append((success,item or kwargs.get('listitem'))),
            'xbmc': types.SimpleNamespace(executebuiltin=lambda *args: None),
            'pathExists': lambda path: False,
        }
        self.patches = [patch.dict(stubs.control.__dict__, values),
                        patch.dict(stubs.cache.__dict__, {'get': lambda fn,hours,*args,**kwargs: fn(*args),
                                                         'remove': lambda *args: None, 'cache_clear': lambda: None}),
                        patch.dict(stubs.client.__dict__, {'request_budget': lambda *args: nullcontext()})]
        for p in self.patches: p.start()
        from resources.lib import deccandelight, experience
        self.app, self.ux = deccandelight, experience
        hosted = patch.object(self.app, 'check_hosted_media', return_value=False)
        hosted.start()
        self.patches.append(hosted)

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def test_home_routes_are_grouped_and_include_personal_collections(self):
        self.app.list_sites()
        labels = [item.label for _,item,_ in self.rows]
        self.assertIn('Movies', labels)
        self.assertIn('My watchlist', labels)
        self.assertIn('Settings & tools', labels)
        self.assertEqual(len(labels), 9)
        self.assertTrue(all(item.art.get('poster') and item.tag.values.get('setPlot') for _,item,_ in self.rows))

    def test_watchlist_survives_reopening_and_routes_stable_title_page(self):
        page = 'https://example.org/movie/?q=A%2BB+C&sig=A%2FZ'
        self.ux.change_collection({'action':'17','site':'tgun','title':'Movie & More','thumb':'poster.jpg','iurl':page,'mode':'8'})
        self.ux.list_collection('watchlist')
        params = parse_qs(urlsplit(self.rows[0][0]).query)
        self.assertEqual(params['iurl'], [page])
        self.assertEqual(params['action'], ['14'])
        self.assertFalse(self.rows[0][2])
        self.assertTrue(any('Remove from watchlist' == label for label,_ in self.rows[0][1].context))
        self.ux.change_collection({'action':'18','kind':'watchlist','key':self.ux.database().items('watchlist')[0]['id']})
        self.assertEqual(self.ux.database().items('watchlist'), [])

    def test_manual_mode_keeps_server_picker_and_autoplay_context_action(self):
        self.settings['autoplay'] = 'false'
        url, item, folder = self.ux.title_row('tgun', 'Movie', 'poster', 'https://example.org/movie', 8)
        self.assertEqual(parse_qs(urlsplit(url).query)['action'], ['8'])
        self.assertTrue(folder)
        self.assertIn('Play automatically', [label for label,_ in item.context])

    def test_favorites_toggle_and_known_unavailable_source_has_retry_route(self):
        self.ux.change_collection({'action':'19','site':'tgun'})
        self.ux.database().save('health', {'site':'tgun','url':'','available':False})
        self.ux.source_list('favorites')
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(parse_qs(urlsplit(self.rows[0][0]).query)['action'], ['22'])
        self.ux.change_collection({'action':'19','site':'tgun'})
        self.assertEqual(self.ux.database().items('favorites'), [])

    def test_actual_player_preserves_signed_url_and_title(self):
        signed = 'https://cdn.example/movie.mp4?signature=A%2BB%2FZ+C&x=1'
        item = self.app.play_video(signed, resolve_only=True, quiet=True, title='Movie (2026)')
        self.assertEqual(item.getPath(), signed)
        self.assertEqual(item.tag.values['setTitle'], ('Movie (2026)',))
        self.assertEqual(self.resolved, [])

    def test_router_decodes_nested_url_once_and_keeps_question_marks(self):
        from resources.lib.router import routing
        signed = 'https://cdn.example/movie.mp4?signature=A%2BB%2FZ+C&q=?'
        with patch.object(self.app, 'play_video') as play:
            routing(self.ux.route(9, iurl=signed, title='A+B').split('?',1)[1])
        play.assert_called_once_with(signed, title='A+B')

    def test_smart_play_rejects_failed_media_and_uses_next_server(self):
        provider = types.SimpleNamespace(get_videos=lambda url:[('1080p bad','https://cdn.example/first.mp4'),
                                                               ('720p good','https://cdn.example/second.mp4')])
        def request(url,**kwargs):
            return (b'file', '403' if 'first' in url else '200', {'Content-Type':'video/mp4'})
        with patch.object(self.app,'scraper_for',return_value=provider), patch.object(stubs.client,'request',side_effect=request):
            self.ux.smart_play('tgun','Example','https://example.org/movie','poster')
        self.assertEqual(len(self.resolved),1)
        self.assertTrue(self.resolved[0][0])
        self.assertEqual(self.resolved[0][1].getPath(),'https://cdn.example/second.mp4')
        self.assertEqual(self.ux.database().items('recent')[0]['url'],'https://example.org/movie')

    def test_smart_play_no_servers_resolves_failure_without_unhandled_exception(self):
        with patch.object(self.app,'scraper_for',return_value=types.SimpleNamespace(get_videos=lambda url:[])):
            self.ux.smart_play('tgun','Example','https://example.org/movie','poster')
        self.assertFalse(self.resolved[0][0])
        self.assertIn('No working server',self.messages[-1])

    def test_metadata_update_does_not_mutate_cached_metadata(self):
        meta = {'title':'Example','tmdb_id':12,'art':{'poster':'poster'}}
        self.app.update_listitem(Item(),meta)
        self.assertEqual(meta['tmdb_id'],12)

    def test_movie_metadata_loads_concurrently_and_keeps_source_art_on_miss(self):
        self.settings['meta'] = 'true'
        state = {'active':0, 'peak':0}
        lock = threading.Lock()
        def metadata(title):
            with lock:
                state['active'] += 1
                state['peak'] = max(state['peak'], state['active'])
            time.sleep(0.02)
            with lock:
                state['active'] -= 1
            return {} if title == 'Movie 0' else {'title':title, 'tmdb_id':12, 'art':{'poster':'tmdb-poster'}}
        module = types.ModuleType('resources.lib.metautils')
        module.get_meta = metadata
        movies = [('Movie '+str(i),'source-poster','https://site/movie/'+str(i)) for i in range(8)]
        provider = types.SimpleNamespace(get_items=lambda url:(movies,8))
        with patch.dict(sys.modules, {'resources.lib.metautils':module}), patch.object(self.app,'scraper_for',return_value=provider):
            self.app.list_items('tgun','https://site/list/')
        self.assertEqual(len(self.rows),8)
        self.assertGreater(state['peak'],1)
        self.assertLessEqual(state['peak'],4)
        self.assertEqual(self.rows[0][1].art['poster'],'source-poster')
        self.assertEqual(self.rows[1][1].art['poster'],'tmdb-poster')

    def test_global_search_prompts_once_deduplicates_and_keeps_alternative_sources(self):
        class Provider:
            def get_menu(self):
                return ({'99Search':'https://site/?s='},7,'icon')
            def get_items(self,url):
                self.get_SearchQuery('Source')
                movie = ('Example','poster','https://site/example/')
                return ([movie,movie],8)
        self.settings.update({'ary':'false','yodesi':'false'})
        before = getattr(stubs.control,'PRESET_QUERY',None)
        with patch.object(stubs.control,'keyboard_query',return_value='Example',create=True) as keyboard,patch.object(self.app,'scraper_for',side_effect=lambda site:Provider()):
            self.app.global_search()
        keyboard.assert_called_once()
        self.assertEqual(len(self.rows),2)
        self.assertEqual(getattr(stubs.control,'PRESET_QUERY',None),before)



class EngineTests(unittest.TestCase):
    def test_quality_preference_dedup_and_direct_priority(self):
        videos=[('4K','https://cdn/a.mp4'),('1080p','https://cdn/b.mp4'),('720p','https://cdn/c.mp4'),('Duplicate','https://cdn/b.mp4')]
        self.assertEqual(streams.rank(videos,1080)[0][0],'1080p')
        self.assertEqual(streams.rank(videos)[0][0],'4K')
        self.assertEqual(len(streams.rank(videos)),3)
        self.assertEqual(streams.quality('Movie (2026)'),0)

    def test_media_check_rejects_html_and_preserves_headers_and_url(self):
        calls=[]
        def request(url,**kwargs):
            calls.append((url,kwargs));return (b'<!DOCTYPE html>','200',{'content-type':'text/html'})
        signed='https://cdn/movie.mp4?sig=A%2BB|Referer=https%3A%2F%2Fsite%2F'
        self.assertFalse(streams.media_available(signed,request))
        self.assertEqual(calls[0][0],'https://cdn/movie.mp4?sig=A%2BB')
        self.assertEqual(calls[0][1]['headers']['Referer'],'https://site/')
        self.assertTrue(streams.media_available('https://cdn/master.m3u8',lambda *a,**k:(b'#EXTM3U\n','200',{'content-type':'application/vnd.apple.mpegurl'})))

    def test_parallel_workers_are_bounded_and_keep_result_order(self):
        state={'active':0,'peak':0};lock=threading.Lock()
        def task(job,deadline,stop):
            with lock:state['active']+=1;state['peak']=max(state['peak'],state['active'])
            time.sleep(0.02)
            with lock:state['active']-=1
            return job*2
        result,partial=parallel.collect(range(8),task,workers=2,seconds=2)
        self.assertFalse(partial)
        self.assertEqual(result,[(i,i*2) for i in range(8)])
        self.assertEqual(state['peak'],2)

    def test_deadline_returns_completed_jobs_and_signals_slow_worker(self):
        stopped=threading.Event()
        def task(job,deadline,stop):
            if job==0:return 'fast'
            stop.wait(1);stopped.set();return 'slow'
        start=time.monotonic()
        rows,partial=parallel.collect([0,1],task,workers=2,seconds=0.08)
        self.assertLess(time.monotonic()-start,0.3)
        self.assertEqual(rows,[(0,'fast')]);self.assertTrue(partial)
        self.assertTrue(stopped.wait(0.3))

    def test_cancelled_pool_does_not_start_requests(self):
        calls=[]
        result,partial=parallel.collect([1],lambda *args:calls.append(args),cancelled=lambda:True)
        self.assertEqual(calls,[]);self.assertEqual(result,[]);self.assertTrue(partial)

    def test_collection_is_persistent_unicode_safe_bounded_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'collections.db');store=collection.Collection(path)
            store.save('watchlist',{'site':'tgun','url':'https://example/movie','title':'தமிழ்'})
            store.save('watchlist',{'site':'tgun','url':'https://example/movie','title':'Updated'})
            self.assertEqual(len(collection.Collection(path).items('watchlist')),1)
            for i in range(105):store.save('recent',{'site':'tgun','url':str(i)})
            self.assertEqual(len(store.items('recent')),100)
            self.assertEqual(store.items('recent')[0]['url'],'104')


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        import kodi_six
        addon=types.SimpleNamespace(Addon=lambda:types.SimpleNamespace(getAddonInfo=lambda key:self.tmp.name))
        with patch.object(kodi_six,'xbmcaddon',addon,create=True),patch.object(kodi_six,'xbmc',types.SimpleNamespace(),create=True):
            self.cache=load('cache_checks','cache.py')
        self.cache.cacheFile=str(Path(self.tmp.name)/'cache.db')
    def tearDown(self):self.tmp.cleanup()

    def test_cache_reuses_valid_value_and_stream_call_refuses_stale_failure(self):
        values=[['good'],[]]
        def fetch():return values.pop(0)
        self.assertEqual(self.cache.get(fetch,1),['good'])
        self.assertEqual(self.cache.get(fetch,1),['good'])
        self.assertEqual(self.cache.get(fetch,0,_stale=False),[])

    def test_empty_listing_not_cached_and_corrupt_row_recovers(self):
        calls=[]
        def fetch():calls.append(1);return ([],8)
        self.cache.get(fetch,1);self.cache.get(fetch,1)
        self.assertEqual(len(calls),2)
        key=self.cache._hash_function(fetch)
        self.cache.cache_insert(key,b'not-zlib')
        self.assertEqual(self.cache.get(fetch,1),([],8))
        self.cache.cache_clear();self.assertIsNone(self.cache.cache_get(key))

    def test_concurrent_cache_writes_and_reads_use_independent_connections(self):
        def work(index):
            self.cache.cache_insert(str(index),b'value')
            return self.cache.cache_get(str(index))['value']
        with ThreadPoolExecutor(max_workers=5) as pool:
            self.assertEqual(list(pool.map(work,range(20))),[b'value']*20)




class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path.startswith('/redirect'):
                    self.send_response(302);self.send_header('Location','/target');self.end_headers();return
                self.send_response(200)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Set-Cookie','session='+self.headers.get('X-Identity','none'))
                self.end_headers()
                self.wfile.write(json.dumps({'path':self.path,'cookie':self.headers.get('Cookie','')}).encode())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start()
        cls.root='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.worker.join()
    def setUp(self):
        self.patch=patch.dict(stubs.control.__dict__,{'pathExists':lambda path:False})
        self.patch.start();self.client=load('http_checks','client.py');self.client.CERT_FILE=None
    def tearDown(self):self.patch.stop()

    def test_real_http_preserves_existing_query_and_encoded_signature(self):
        body=self.client.request(self.root+'/?signature=A%2BB%2FZ+C',headers={'User-Agent':'test'},params={'extra':'x+y'})
        self.assertEqual(json.loads(body)['path'],'/?signature=A%2BB%2FZ+C&extra=x%2By')

    def test_parallel_http_cookie_jar_is_request_scoped(self):
        from urllib import request
        before=request._opener
        def call(identity):
            result=self.client.request(self.root+'/',output='extended',headers={'User-Agent':'test','X-Identity':str(identity)})
            return result[4]
        with ThreadPoolExecutor(max_workers=5) as pool:
            cookies=list(pool.map(call,range(10)))
        self.assertEqual(cookies,['session='+str(i) for i in range(10)])
        self.assertIs(request._opener,before)
        self.assertEqual(json.loads(self.client.request(self.root+'/',headers={'User-Agent':'test'}))['cookie'],'')

    def test_redirect_control_and_ssl_context_do_not_leak_between_requests(self):
        import ssl
        from urllib import request
        before=request._opener;context=ssl._create_default_https_context
        result=self.client.request(self.root+'/redirect',output='extended',redirect=False,verify=False,headers={'User-Agent':'test'})
        self.assertEqual(result[1],'302')
        followed=self.client.request(self.root+'/redirect',headers={'User-Agent':'test'})
        self.assertEqual(json.loads(followed)['path'],'/target')
        self.assertIs(request._opener,before);self.assertIs(ssl._create_default_https_context,context)

    def test_expired_request_budget_makes_no_network_call(self):
        with self.client.request_budget(time.monotonic()-1):
            with patch('urllib.request.build_opener') as opener:
                self.assertIsNone(self.client.request(self.root+'/'))
                opener.assert_not_called()


class MirrorTests(unittest.TestCase):
    def test_old_remote_registry_falls_back_to_working_local_template(self):
        module=load('mirror_checks','base.py')
        control_values={'get_setting':lambda key:'false'}
        old={'mirrors':['https://old.example/'],'probe':'old/path','marker':'old-layout'}
        pages={'https://old.example/old/path':None,'https://new.example/':'latestPost'}
        with patch.dict(stubs.cache.__dict__,{'get':lambda fn,hours,*args,**kwargs:fn(*args)}),patch.object(module,'remote_site_config',return_value=old),patch.object(stubs.client,'request',side_effect=lambda url,**kwargs:pages.get(url)):
            scraper=module.Scraper()
            self.assertEqual(scraper.resolve_domain('example',['https://new.example/'],'','latestPost'),'https://new.example/')

    def test_empty_remote_probe_is_preserved_and_valid_remote_wins(self):
        module=load('mirror_checks','base.py')
        config={'mirrors':['https://remote.example/'],'probe':'','marker':'current-layout'}
        with patch.dict(stubs.cache.__dict__,{'get':lambda fn,hours,*args,**kwargs:fn(*args)}),patch.object(module,'remote_site_config',return_value=config),patch.object(stubs.client,'request',side_effect=lambda url,**kwargs:'current-layout' if url=='https://remote.example/' else ''):
            self.assertEqual(module.Scraper().resolve_domain('example',['https://local.example/'],'old/path','local-layout'),'https://remote.example/')


if __name__=='__main__':unittest.main()
