#!/usr/bin/env python3
"""Render original SVG artwork to Kodi PNG/JPEG assets. No runtime dependency."""
from pathlib import Path
import io
from html import escape
import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'plugin.video.deccandelight'
VECTORS = ROOT / 'resources/artwork'
IMAGES = ROOT / 'resources/images'
VECTORS.mkdir(exist_ok=True)

GLYPHS = {
 'search':'<circle cx="95" cy="92" r="58"/><path d="m139 137 49 49"/>',
 'movies':'<rect x="24" y="62" width="190" height="134" rx="14"/><path d="M24 100h190M35 63l35 37m12-37 35 37m12-37 35 37m12-37 35 37"/><path d="m101 126 40 23-40 23Z" fill="currentColor" stroke="none"/>',
 'shows':'<rect x="22" y="55" width="194" height="133" rx="16"/><path d="m74 22 46 33 43-33m-61 194h39m-19-29v29"/><path d="m104 96 42 27-42 27Z" fill="currentColor" stroke="none"/>',
 'music':'<path d="M88 170V55l106-22v115M88 93l106-22"/><ellipse cx="62" cy="174" rx="27" ry="20"/><ellipse cx="168" cy="151" rx="27" ry="20"/>',
 'watchlist':'<path d="M66 28h108a9 9 0 0 1 9 9v178l-63-45-63 45V37a9 9 0 0 1 9-9Z"/><path d="M120 77v54m-27-27h54"/>',
 'recent':'<path d="M30 105a87 87 0 1 1 10 72M30 105V45m0 60h60"/><path d="M122 70v58l40 24"/>',
 'favorites':'<path d="m120 27 28 60 66 10-48 47 12 66-58-31-58 31 12-66-48-47 66-10Z"/>',
 'sources':'<rect x="25" y="28" width="73" height="73" rx="13"/><rect x="143" y="28" width="73" height="73" rx="13"/><rect x="25" y="143" width="73" height="73" rx="13"/><rect x="143" y="143" width="73" height="73" rx="13"/>',
 'tools':'<path d="M55 57h131M55 119h131M55 181h131"/><circle cx="85" cy="57" r="18" fill="#102d3b"/><circle cx="155" cy="119" r="18" fill="#102d3b"/><circle cx="101" cy="181" r="18" fill="#102d3b"/>',
 'play':'<circle cx="120" cy="120" r="95"/><path d="m96 72 75 48-75 48Z" fill="currentColor" stroke="none"/>',
}
TILES = {
 'search':('Search','ALL YOUR SOURCES','FIND YOUR NEXT WATCH'),
 'movies':('Movies','CINEMA, EVERY LANGUAGE','DISCOVER'),
 'shows':('TV & shows','EPISODES & CATCH-UP','DISCOVER'),
 'music':('Music','SONGS, FILMS & SINGERS','DISCOVER'),
 'watchlist':('My watchlist','SAVE NOW. WATCH LATER.','YOUR COLLECTION'),
 'recent':('Recently opened','PICK UP YOUR NEXT WATCH','YOUR COLLECTION'),
 'favorites':('Favorite sources','YOUR GO-TO PROVIDERS','YOUR COLLECTION'),
 'sources':('All sources','MORE PLACES TO DISCOVER','BROWSE'),
 'tools':('Settings & tools','MAKE IT YOURS','PERSONALIZE'),
 'play':('Play automatically','FIND A WORKING SERVER','READY TO WATCH'),
}


def render(name, svg, target):
    (VECTORS / (name + '.svg')).write_text(svg)
    data = cairosvg.svg2png(bytestring=svg.encode())
    if target.suffix == '.jpg':
        Image.open(io.BytesIO(data)).convert('RGB').save(target, quality=90, optimize=True)
    else:
        target.write_bytes(data)


def tile(name, title, subtitle, eyebrow):
    color = '#f3c383' if name in ('movies','watchlist','play') else '#77decd'
    words = title.split(' ')
    lines = [title] if len(title)<17 else [' '.join(words[:-1]),words[-1]]
    text = ''.join('<text x="44" y="{}" font-size="38" font-weight="bold">{}</text>'.format(578+i*47,escape(line)) for i,line in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="768" viewBox="0 0 512 768">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#071b29"/><stop offset="1" stop-color="#163c49"/></linearGradient><radialGradient id="glow"><stop stop-color="{color}" stop-opacity=".14"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient></defs>
<rect width="512" height="768" fill="url(#bg)"/><circle cx="315" cy="320" r="280" fill="url(#glow)"/>
<path d="M360-30 80 800M490-30 210 800M620-30 340 800" stroke="#c5eee5" stroke-opacity=".025" stroke-width="40"/>
<rect x="20" y="20" width="472" height="728" rx="8" stroke="#b5d6e2" stroke-opacity=".12" fill="none"/>
<g font-family="DejaVu Sans, sans-serif" fill="#e6f1f4"><text x="44" y="70" font-size="15" letter-spacing="2.2">INDIAN MOVIE HUB</text>
<text x="44" y="109" font-size="13" fill="{color}" letter-spacing="1.7">{escape(eyebrow)}</text>
<g transform="translate(137 237)" color="{color}" fill="none" stroke="currentColor" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">{GLYPHS[name]}</g>
<path d="M44 510h48" stroke="{color}" stroke-width="4"/>{text}
<text x="44" y="695" font-size="12" fill="#b5cdd6" letter-spacing="1.1">{escape(subtitle)}</text></g></svg>'''

for name,(title,subtitle,eyebrow) in TILES.items():
    render('hub-'+name,tile(name,title,subtitle,eyebrow),IMAGES/('hub-'+name+'.png'))

fanart='''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><defs><linearGradient id="b" x2="1" y2="1"><stop stop-color="#061320"/><stop offset="1" stop-color="#163744"/></linearGradient><radialGradient id="g"><stop stop-color="#377e7f" stop-opacity=".22"/><stop offset="1" stop-color="#377e7f" stop-opacity="0"/></radialGradient></defs><rect width="1920" height="1080" fill="url(#b)"/><ellipse cx="1520" cy="380" rx="800" ry="650" fill="url(#g)"/><g stroke="#82c7bd" stroke-opacity=".06" fill="none"><circle cx="1560" cy="410" r="345" stroke-width="2"/><circle cx="1560" cy="410" r="285" stroke-width="30"/><path d="m1440 220 330 190-330 190Z" stroke-width="3"/></g><path d="m0 1010 1920-460M0 1080l1920-460" stroke="#e5c292" stroke-opacity=".035" stroke-width="40"/><g font-family="DejaVu Sans, sans-serif" fill="#c4dedf" fill-opacity=".55"><text x="1330" y="974" font-size="27" letter-spacing="6">INDIAN MOVIE HUB</text><text x="1330" y="1016" font-size="14" letter-spacing="3" fill-opacity=".5">CINEMA · TELEVISION · MUSIC</text></g></svg>'''
render('fanart',fanart,ROOT/'fanart.jpg')
icon=f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><defs><linearGradient id="b" x2="1" y2="1"><stop stop-color="#071b29"/><stop offset="1" stop-color="#163c49"/></linearGradient></defs><rect width="512" height="512" rx="48" fill="url(#b)"/><circle cx="256" cy="240" r="182" fill="none" stroke="#77decd" stroke-opacity=".13" stroke-width="2"/><g transform="translate(137 105)" color="#f3c383" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round" stroke-linejoin="round">{GLYPHS['movies']}</g><g font-family="DejaVu Sans,sans-serif" text-anchor="middle" fill="#edf5f5"><text x="256" y="395" font-size="30" font-weight="bold" letter-spacing="3">INDIAN MOVIE</text><text x="256" y="443" font-size="30" font-weight="bold" letter-spacing="9">HUB</text></g></svg>'''
render('icon',icon,ROOT/'icon.png')
print('Rendered 10 home cards, icon and fanart from original SVG sources.')

(IMAGES/'hub-icon.png').write_bytes((ROOT/'icon.png').read_bytes())
(IMAGES/'hub-fanart.jpg').write_bytes((ROOT/'fanart.jpg').read_bytes())
