"""
    Deccan Delight Kodi Addon
    Copyright (C) 2016 gujal

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

from six.moves import urllib_parse


def routing(paramstring):
    # """
    # Router function that calls other functions
    # depending on the provided paramstring

    # :param paramstring:
    # Action Definitions:
    # 1 : List Site
    # 4 : List Top Menu (Channels, Languages)
    # 5 : List Secondary Menu (Shows, Categories)
    # 6 : List Third Menu
    # 7 : List Individual Items (Movies, Episodes)
    # 8 : List Playable Videos
    # 9 : Play Video
    # """
    # # Parse a URL-encoded paramstring to the dictionary of
    # # {<parameter>: <value>} elements
    # params = dict(urllib_parse.parse_qsl(paramstring))
    # # Check the parameters passed to the plugin

    params = dict(urllib_parse.parse_qsl(paramstring.lstrip('?')))
    # logger(f'routing params>>>> {params}')
    try:
        _dispatch(params)
    except Exception:
        import traceback
        from resources.lib import control
        control.log(traceback.format_exc(), 'info')
        site = params.get('site', '')
        msg = 'Site unreachable or page layout changed'
        if site:
            msg = '{0}: {1}'.format(site, msg)
        control.notify(msg)
        if params.get('action') in ('9', '14'):
            from resources.lib.deccandelight import make_listitem
            control.setResolvedUrl(control._handle, False, make_listitem())
        elif params.get('action') in ('1','4','5','6','7','8','13','15','16','20','21'):
            control.eod(control._handle, succeeded=False)


def _dispatch(params):
    if params:
        action = params.get('action', '')
        if action == '0':
            from resources.lib.deccandelight import clear_cache
            clear_cache()
        elif action == '1':
            from resources.lib.deccandelight import list_menu
            list_menu(params['site'])
        elif action == '4':
            from resources.lib.deccandelight import list_top
            list_top(params['site'], params['iurl'])
        elif action == '5':
            from resources.lib.deccandelight import list_second
            list_second(params['site'], params['iurl'])
        elif action == '6':
            from resources.lib.deccandelight import list_third
            list_third(params['site'], params['iurl'])
        elif action == '7':
            from resources.lib.deccandelight import list_items
            list_items(params['site'], params['iurl'])
        elif action == '8':
            from resources.lib.deccandelight import list_videos
            list_videos(params['site'], params['title'], params['iurl'], params['thumb'])
        elif action == '9':
            from resources.lib.deccandelight import play_video
            play_video(params['iurl'], title=params.get('title'))
        elif action == '10':
            from resources.lib.deccandelight import play_video
            play_video(params['iurl'], dl=True)
        elif action == '11':
            from resources.lib.tmdb import TMDB
            TMDB().clear_meta()
        elif action == '12':
            import resolveurl
            resolveurl.display_settings()
        elif action == '13':
            from resources.lib.deccandelight import global_search
            global_search()
        elif action == '14':
            from resources.lib.experience import smart_play
            smart_play(params['site'], params.get('title', 'Unknown'), params['iurl'], params.get('thumb', ''))
        elif action == '15':
            from resources.lib.experience import source_list
            source_list(params.get('group', 'all'))
        elif action == '16':
            from resources.lib.experience import list_collection
            list_collection(params.get('kind', 'watchlist'))
        elif action in ('17', '18', '19'):
            from resources.lib.experience import change_collection
            change_collection(params)
        elif action == '20':
            from resources.lib.experience import tools
            tools()
        elif action == '21':
            from resources.lib.experience import availability
            availability()
        elif action == '22':
            from resources.lib.experience import source_status
            source_status(params['site'])
        elif action == '23':
            from resources.lib.experience import refresh
            refresh(params['site'])
        elif action == '25':
            from resources.lib import control
            control._addon.openSettings()
    else:
        from resources.lib.deccandelight import list_sites
        list_sites()
