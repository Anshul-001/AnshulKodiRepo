"""Server quality ordering and small, bounded media checks."""
import re
from six.moves import urllib_parse


def quality(label):
    match = re.search(r'\b(2160|1080|720|576|480|360|240)\s*p?\b|\b4k\b', label, re.I)
    return (int(match.group(1)) if match.group(1) else 2160) if match else 0


def rank(videos, preference=0):
    seen = set()
    choices = []
    for label, url in videos:
        if not isinstance(url, str) or not url or url in seen:
            continue
        seen.add(url)
        choices.append((label, url))

    def score(item):
        label, url = item
        resolution = quality(label)
        direct = urllib_parse.urlsplit(url.split('|', 1)[0]).path.lower().endswith(('.mp4', '.m3u8', '.mp3'))
        # A preference picks the closest known quality; unknown HLS masters
        # remain adaptive. It is not a promise to upscale the source.
        preferred = resolution if not preference else (-abs(resolution - preference) if resolution else -10000)
        return (preferred, direct)
    return sorted(choices, key=score, reverse=True)


def media_available(url, request):
    address, _, encoded = url.partition('|')
    scheme = urllib_parse.urlsplit(address).scheme
    if scheme == 'plugin':
        return True
    if scheme not in ('http', 'https'):
        return False
    headers = dict(urllib_parse.parse_qsl(encoded))
    # A range plus a two-KiB client read avoids downloading video just to
    # choose a server. A GET also works with hosts that reject HEAD.
    headers.setdefault('Range', 'bytes=0-2047')
    response = request(address, headers=headers, limit='2', output='extended', timeout='8')
    if not response or not isinstance(response, tuple) or len(response) < 3:
        return False
    body, code, response_headers = response[:3]
    if str(code) not in ('200', '206'):
        return False
    content = {k.lower(): v for k, v in response_headers.items()}.get('content-type', '').lower()
    if 'text/html' in content or 'application/json' in content:
        return False
    path = urllib_parse.urlsplit(address).path.lower()
    if '.m3u8' in path or 'mpegurl' in content:
        if isinstance(body, bytes):
            body = body.decode('utf-8', errors='ignore')
        return isinstance(body, str) and body.lstrip('\ufeff\r\n ').startswith('#EXTM3U')
    return bool(body) and (content.startswith(('video/', 'audio/')) or 'octet-stream' in content
                           or path.endswith(('.mp4', '.mp3', '.mpd', '.ism')))
