# -*- coding: utf-8 -*-
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import hashlib
import os
from contextlib import closing
import json
import pickle
import re
import six
import time
import zlib
from kodi_six import xbmc, xbmcvfs, xbmcaddon
try:
    from sqlite3 import dbapi2 as db, OperationalError, Binary
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError, Binary


TRANSLATEPATH = xbmcvfs.translatePath if six.PY3 else xbmc.translatePath
cacheFile = TRANSLATEPATH(xbmcaddon.Addon().getAddonInfo('profile') + '/cache.db')
cache_table = 'cache'


def _decode(row):
    try:
        return pickle.loads(zlib.decompress(row['value']))
    except (ValueError, TypeError, KeyError, zlib.error, pickle.UnpicklingError, EOFError):
        return None


def _has_content(value):
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], (list, dict)):
        return bool(value[0])
    return bool(value)


def get(function, duration, *args, **kwargs):
    # Streams can opt out of stale fallback without changing scraper kwargs.
    stale = kwargs.pop('_stale', True)
    key = _hash_function(function, *args, **kwargs)
    row = cache_get(key)
    cached = _decode(row) if row else None
    if cached is not None and _is_cache_valid(row['date'], duration):
        return cached
    fresh = function(*args, **kwargs)
    if not _has_content(fresh):
        return cached if stale and cached is not None else fresh
    cache_insert(key, Binary(zlib.compress(pickle.dumps(fresh))))
    return fresh


def remove(function, *args, **kwargs):
    key = _hash_function(function, *args, **kwargs)
    with closing(_get_connection()) as conn:
        try:
            conn.execute('DELETE FROM cache WHERE key=?', (key,))
            conn.commit()
        except OperationalError:
            pass


def timeout(function, *args, **kwargs):
    row = cache_get(_hash_function(function, *args, **kwargs))
    return int(row['date']) if row else 0


def cache_get(key):
    with closing(_get_connection()) as conn:
        try:
            return conn.execute('SELECT * FROM cache WHERE key=?', (key,)).fetchone()
        except OperationalError:
            return None


def cache_insert(key, value):
    with closing(_get_connection()) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BINARY, date INTEGER)')
        conn.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)', (key, value, int(time.time())))
        conn.commit()


def cache_clear():
    with closing(_get_connection()) as conn:
        for table in (cache_table, 'rel_list', 'rel_lib'):
            conn.execute('DROP TABLE IF EXISTS ' + table)
        conn.commit()
        conn.execute('VACUUM')


def _get_connection():
    os.makedirs(os.path.dirname(cacheFile) or '.', exist_ok=True)
    conn = db.connect(cacheFile, timeout=10)
    conn.row_factory = _dict_factory
    return conn


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _hash_function(function_instance, *args, **kwargs):
    return _get_function_name(function_instance) + _generate_md5(*args, **kwargs)


def _get_function_name(function_instance):
    return re.sub(
        r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+',
        '',
        repr(function_instance))


def _generate_md5(*args, **kwargs):
    md5_hash = hashlib.md5()
    [md5_hash.update(str(arg) if six.PY2 else str(arg).encode()) for arg in args]
    md5_hash.update(json.dumps(kwargs) if six.PY2 else json.dumps(kwargs).encode())
    return md5_hash.hexdigest()


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff
