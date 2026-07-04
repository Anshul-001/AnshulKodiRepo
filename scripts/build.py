#!/usr/bin/env python3
"""Build script for Anshul Kodi Repo.

Packages each addon source folder into zips/<id>/<id>-<version>.zip,
regenerates addons.xml + addons.xml.md5, and writes index.html files so
Kodi can browse the repo over HTTP (GitHub Pages has no directory listing).

Run from the repo root:  python3 scripts/build.py
"""
import hashlib
import os
import re
import shutil
import zipfile
from xml.etree import ElementTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIPS = os.path.join(ROOT, 'zips')
EXCLUDE_DIRS = {'.git', '__pycache__', 'zips', 'scripts'}
ASSETS = ('icon.png', 'fanart.jpg', 'changelog.txt')


def addon_dirs():
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(name, 'addon.xml')
        if name not in EXCLUDE_DIRS and os.path.isfile(os.path.join(ROOT, path)):
            yield name


def build_zip(addon_id):
    src = os.path.join(ROOT, addon_id)
    tree = ElementTree.parse(os.path.join(src, 'addon.xml'))
    version = tree.getroot().get('version')
    out_dir = os.path.join(ZIPS, addon_id)
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, '{0}-{1}.zip'.format(addon_id, version))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for f in sorted(files):
                if f.endswith('.pyc') or f == '.DS_Store':
                    continue
                full = os.path.join(base, f)
                arc = os.path.join(addon_id, os.path.relpath(full, src))
                zf.write(full, arc)

    for asset in ASSETS:
        src_asset = os.path.join(src, asset)
        if os.path.isfile(src_asset):
            shutil.copy2(src_asset, out_dir)
            if asset == 'changelog.txt':
                shutil.copy2(src_asset, os.path.join(out_dir, 'changelog-{0}.txt'.format(version)))

    print('built', os.path.relpath(zip_path, ROOT))
    return addon_id


def build_manifest(ids):
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<addons>']
    for addon_id in ids:
        with open(os.path.join(ROOT, addon_id, 'addon.xml')) as f:
            xml = f.read()
        xml = re.sub(r'<\?xml[^>]*\?>\s*', '', xml)
        parts.append(xml.strip())
    parts.append('</addons>\n')
    manifest = '\n'.join(parts)
    with open(os.path.join(ROOT, 'addons.xml'), 'w') as f:
        f.write(manifest)
    md5 = hashlib.md5(manifest.encode('utf-8')).hexdigest()
    with open(os.path.join(ROOT, 'addons.xml.md5'), 'w') as f:
        f.write(md5)
    print('built addons.xml (md5 {0})'.format(md5))


def write_index(dir_path, entries):
    rows = ['<a href="{0}">{0}</a><br>'.format(e) for e in entries]
    html = '<!DOCTYPE html><html><body>\n{0}\n</body></html>\n'.format('\n'.join(rows))
    with open(os.path.join(dir_path, 'index.html'), 'w') as f:
        f.write(html)


def build_indexes():
    write_index(ROOT, ['zips/', 'addons.xml', 'addons.xml.md5'])
    subdirs = sorted(d for d in os.listdir(ZIPS) if os.path.isdir(os.path.join(ZIPS, d)))
    write_index(ZIPS, [d + '/' for d in subdirs])
    for d in subdirs:
        full = os.path.join(ZIPS, d)
        files = sorted(f for f in os.listdir(full) if f != 'index.html' and not f.startswith('.'))
        write_index(full, files)
    print('built index.html files')


if __name__ == '__main__':
    ids = [build_zip(a) for a in addon_dirs()]
    build_manifest(ids)
    build_indexes()
