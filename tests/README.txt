Scraper and application regression tests

From the repository root:
  python3 -m venv .venv
  .venv/bin/python -m pip install -r tests/requirements.txt
  .venv/bin/python -m unittest discover -s tests -v

63 tests cover current site markup, player extraction, URL handling, pagination,
missing responses, home/collection routes, smart-server fallback, bounded workers,
thread-safe cache behavior and scoped HTTP/cookies. Kodi UI APIs are stubbed;
HTTP integration tests use a local server. BeautifulSoup 4.12.2 matches Kodi.
Offline tests do not establish native playback or debrid authorization.

Live validation of version 2.3.1 (2026-10-04 Pacific / 2026-10-05 UTC):
- Audited all 33 scraper modules, including 20 visible sources.
- Checked 14 mirror probes and 302 source entry/menu URLs.
- Exercised 215 active menu listings: 190 returned items, one was correctly
  filtered by the default mature-content setting, and 24 were unavailable
  through three providers excluded from the repair scope. No accessible active listing was
  empty or raised a parser error.
- Sampled TamilGun, DesiTellyBox and YoDesi direct HLS playlists returned 200
  and valid manifests. TodayPK's PkSpeed direct MP4 samples returned 200.
- Followed Hindi Geetmala singer/song pages to YouTube and ARY programmes to
  public official Dailymotion episodes.
- Verified package CRC, source/ZIP equality, Python syntax, manifest version
  and MD5. 63 regression tests passed.

0GoMovies validation:
- Its current .dev domain returns eleven working genres, lazy artwork and
  pagination. Search uses the public suggestion endpoint rather than a route
  that silently returns the homepage: "Vikram" returned four results.
- Series titles open ordered episode folders. A sampled series returned six
  episodes; resolving one selects only that episode's public server metadata.
- Native Cube smart-play resolved and advanced an H.264 movie at 656x272.
  This sample's supplied quality is low; quality preference cannot upscale it.

Availability limits:
TamilYogi, HindiLinks4U Pro and Watch Movies PK are excluded from this repair
scope. Current domains are blocked by SafeBrowse or replacement origins are
unavailable. No network-filter settings were changed. Some individual player
hosts also fail or are blocked. Thirteen previously disabled sources remain
disabled. Per-title hosts and expiring stream links were sampled; all videos
cannot be exhaustively validated. Debrid authorization was not tested.

Native Kodi validation:
- Installed 2.3.1 on a Fire TV Cube (Kodi 21.1) and Hisense (Kodi 21.2), retaining
  each original add-on/profile in private rollback backups. Profiles/accounts
  were not replaced. Tested home/provider directories through actual Kodi.
- Cube home renders the nine new cards in Arctic Fuse 2. Warm native home and
  tools calls completed in about 0.9 seconds; this is not a benchmark versus
  the old version. Initial startup while Kodi was loading was much slower.
- Cube TamilGun movie category returned 25 rows; TodayPK returned 17. Actual
  smart-play opened a TamilGun H.264 stream at 1280x544 and advanced to 15s.
- Hisense home cards were visually verified; the same native smart-play route
  opened H.264 at 1280x544 and advanced from 0.77s to 5.92s.
- Native GUI global search for "Vikram" returned 161 rows across providers.
- Version 2.3.0 native source availability showed 16 available before the new
  0GoMovies repair. The final live audit establishes 17 accessible providers.
  A saved stable TamilGun title page reopened from the watchlist.
- Native 2.3.1 Cube and Hisense listings each returned twelve 0GoMovies menu
  rows (including search), 41 Tamil-category rows (including next page), and
  six episodes. All 130 installed code files on each TV match source.
- Runtime validation does not establish that every hosted video works, that
  every quality choice is supplied, or that TorBox login succeeds.

Artwork:
- Authoring sources: plugin.video.deccandelight/resources/artwork/*.svg.
- Rebuild PNG/JPEG assets with scripts/build_artwork.py after installing
  scripts/requirements-artwork.txt in a development environment.
- Kodi does not require these development rendering libraries.

To publish, merge the source changes, mirrors.json, versioned ZIP, manifest,
checksum and index files together. Older installed versions need an add-on
upgrade; changing mirrors.json alone cannot repair their parser layouts.
