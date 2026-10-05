Scraper regression tests

From the repository root:
  python3 -m venv .venv
  .venv/bin/python -m pip install -r tests/requirements.txt
  .venv/bin/python -m unittest discover -s tests -v

The tests stub Kodi APIs and network requests. BeautifulSoup 4.12.2 matches
Kodi's parser version used during live validation. Tests cover current site
markup, player metadata, relative links, pagination, stale categories, and
missing/invalid responses. They do not exercise Kodi playback or accounts.

Live validation of version 2.2.2 (2026-10-04 Pacific / 2026-10-05 UTC):
- Audited all 33 scraper modules, including 20 visible sources.
- Checked 14 mirror probes and 305 source entry/menu URLs.
- Exercised 218 active menu listings: 179 returned items, one was correctly
  filtered by the default mature-content setting, and 38 were unavailable
  through four network-blocked sources. No accessible active listing was
  empty or raised a parser error.
- Sampled TamilGun, DesiTellyBox and YoDesi direct HLS playlists returned 200
  and valid manifests. TodayPK's PkSpeed direct MP4 samples returned 200.
- Followed Hindi Geetmala singer/song pages to YouTube and ARY programmes to
  public official Dailymotion episodes.
- Verified package CRC, source/ZIP equality, Python syntax, manifest version
  and MD5. 23 regression tests passed.

Availability limits:
TamilYogi, 0GoMovies, HindiLinks4U Pro and Watch Movies PK were blocked by a
SafeBrowse network filter. Some individual player hosts were also blocked
or returned access errors. No substitute mirrors were verified for them.
Thirteen previously disabled sources remain disabled. Per-title hosts and
expiring stream links were sampled; all videos cannot be exhaustively
validated. No playback on a TV or debrid authorization was tested.

To publish, merge the source changes, mirrors.json, versioned ZIP, manifest,
checksum and index files together. Older installed versions need an add-on
upgrade; changing mirrors.json alone cannot repair their parser layouts.
