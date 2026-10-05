Scraper and application regression tests

From the repository root:
  python3 -m venv .venv
  .venv/bin/python -m pip install -r tests/requirements.txt
  .venv/bin/python -m unittest discover -s tests -v

50 tests cover current site markup, player extraction, URL handling, pagination,
missing responses, home/collection routes, smart-server fallback, bounded workers,
thread-safe cache behavior and scoped HTTP/cookies. Kodi UI APIs are stubbed;
HTTP integration tests use a local server. BeautifulSoup 4.12.2 matches Kodi.
Offline tests do not establish native playback or debrid authorization.

Live validation of version 2.3.0 (2026-10-04 Pacific / 2026-10-05 UTC):
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
  and MD5. 50 regression tests passed.

Availability limits:
TamilYogi, 0GoMovies, HindiLinks4U Pro and Watch Movies PK were blocked by a
SafeBrowse network filter. Some individual player hosts were also blocked
or returned access errors. No substitute mirrors were verified for them.
Thirteen previously disabled sources remain disabled. Per-title hosts and
expiring stream links were sampled; all videos cannot be exhaustively
validated. Debrid authorization was not tested.

Native Kodi validation:
- Installed 2.3.0 on a Fire TV Cube (Kodi 21.1) and Hisense (Kodi 21.2), retaining
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
- The source-availability tool returned 16 available and the four known blocked
  providers. A saved stable TamilGun title page reopened from the watchlist.
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
