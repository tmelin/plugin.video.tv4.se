#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Based on code by:
#      Tommy Winther
#      Anders Norman
#
#  (c) Tomas Melin 2016
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import os
import sys
import urlparse
import re
import urllib

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

from playapi import tv4PlayApi, tv4PlayApiException

class TV4PlayAddon():
    def __init__(self):
        self.api = tv4PlayApi()

    def _build_url(self, query):
        return PATH + '?' + urllib.urlencode(query)

    def list_programs(self):
        xbmcplugin.setContent(HANDLE, 'movies')
        programs = self.api.get_programs()
        if not programs:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            self.display_error(30000)
            return

        items = list()
        for program in programs:
            fanart = ''
            if 'program_image' in program:
                fanart = program['program_image']
            infoLabels = {
                'title': program['name'],
                'plot' : program['description'],
                'genre' : program['category']['name']
            }
            item = xbmcgui.ListItem(program['name'], iconImage=fanart)
            item.setProperty('Fanart_Image', fanart)
            item.setInfo('video', infoLabels)
            url = self._build_url({'episodes_nid': program['nid'].encode('utf-8')})
            items.append((url, item, True))

        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(HANDLE)

    def list_episodes(self, program_nid):
        xbmcplugin.setContent(HANDLE, 'episodes')
        items = []
        episodes = self.api.get_episodes(program_nid)

        for episode in episodes:
            fanart = episode['image']

            info_labels = {
                'title': episode['title'],
                'plot' : episode['description'],
                'aired' : episode['broadcast_date_time'],
                'genre' : episode['program']['category']['name']
            }

            item = xbmcgui.ListItem(episode['title'], iconImage=fanart)
            item.setInfo('video', info_labels)
            item.setProperty('Fanart_Image', fanart)
            url = self._build_url({'play_video': episode['id']})
            item.setProperty('IsPlayable', 'true')
            items.append((url, item))

        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def display_error(self, message='N/A', extra_info=''):
        heading = ADDON.getLocalizedString(30001)
        line1 = ADDON.getLocalizedString(30003)
        if str(message).isdigit():
           message = ADDON.getLocalizedString(int(message))
        xbmcgui.Dialog().ok(heading, line1, unicode(message), extra_info)

    def play_video(self, url):
        try:
            videodata = self.api.get_videodata(url)
            player = xbmc.Player()
            item = xbmcgui.ListItem('Video', path=videodata['videourl'])
            xbmcplugin.setResolvedUrl(HANDLE, True, item)

            if videodata['subtitleurl'] != "":
                xbmc.log('setting_subtitles: {0}'.format(videodata['subtitleurl']))
                player.setSubtitles(videodata['subtitleurl'])

                xbmc.log('subtitle-stream: {0}'.format(player.getAvailableSubtitleStreams()))

        except tv4PlayApiException as code:
            if 'SESSION_NOT_AUTHENTICATED' in code:
                self.display_error(30004)
            elif 'ASSET_PLAYBACK_INVALID_GEO_LOCATION' in code:
                self.display_error(30005)
            elif 'DRM_PROTECTED' in code:
                self.display_error(30007)
            elif 'PLAYBACKSTATUS' in code:
                self.display_error(30008, self.api.get_start_time())
            elif 'NO_URL_FOUND' in code:
                self.display_error(30009)
            else:
                self.display_error('{0}'.format(code))

if __name__ == '__main__':
    ADDON = xbmcaddon.Addon()
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = urlparse.parse_qs(sys.argv[2][1:])

    ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')
    FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')

    CACHE_PATH = xbmc.translatePath(ADDON.getAddonInfo('Profile'))
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    tv4playAddon = TV4PlayAddon()
    try:
        if 'play_video' in PARAMS:
            tv4playAddon.play_video(PARAMS['play_video'][0])
        elif 'episodes_nid' in PARAMS:
            tv4playAddon.list_episodes(PARAMS['episodes_nid'][0])
        else:
            tv4playAddon.list_programs()

    except Exception as ex:
        tv4playAddon.display_error(str(ex))
