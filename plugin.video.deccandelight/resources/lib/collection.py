"""Private local collections of stable title pages, never resolved streams."""
from contextlib import contextmanager
import hashlib
import json
import os
import sqlite3
import time


class Collection:
    LIMITS = {'watchlist': 500, 'recent': 100, 'favorites': 50, 'health': 50}

    def __init__(self, path):
        self.path = path

    @staticmethod
    def key(record):
        return hashlib.sha256((record.get('site', '') + '\0' + record.get('url', '')).encode('utf-8')).hexdigest()

    @contextmanager
    def connection(self):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute('CREATE TABLE IF NOT EXISTS collection '
                         '(kind TEXT, id TEXT, value TEXT, updated REAL, PRIMARY KEY(kind,id))')
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, kind, record):
        if kind not in self.LIMITS:
            raise ValueError('Unknown collection')
        key = self.key(record)
        with self.connection() as conn:
            conn.execute('INSERT OR REPLACE INTO collection VALUES(?,?,?,?)',
                         (kind, key, json.dumps(record, ensure_ascii=False), time.time()))
            conn.execute('DELETE FROM collection WHERE kind=? AND id NOT IN '
                         '(SELECT id FROM collection WHERE kind=? ORDER BY updated DESC LIMIT ?)',
                         (kind, kind, self.LIMITS[kind]))
        return key

    def items(self, kind):
        with self.connection() as conn:
            rows = conn.execute('SELECT id,value,updated FROM collection WHERE kind=? '
                                'ORDER BY updated DESC', (kind,)).fetchall()
        result = []
        for key, payload, stamp in rows:
            try:
                item = json.loads(payload)
                if isinstance(item, dict):
                    result.append(dict(item, id=key, updated=stamp))
            except (ValueError, TypeError):
                continue
        return result

    def remove(self, kind, key):
        with self.connection() as conn:
            conn.execute('DELETE FROM collection WHERE kind=? AND id=?', (kind, key))

    def clear(self, kind):
        with self.connection() as conn:
            conn.execute('DELETE FROM collection WHERE kind=?', (kind,))
