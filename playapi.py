#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Tomas Melin 2016
#  Basic tv4play API implementation.
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
from datetime import datetime
import time
import re
import xml.etree.ElementTree as ET
from urlparse import urlparse
import json
import os
import sys
import urllib
import urllib2
try:
    import xbmc
except:
    class xbmc(object):
        @staticmethod
        def log(message):
            sys.stdout.write(message)
            sys.stdout.write('\n')

class tv4PlayApi():
    USER_AGENT = 'Mozilla/5.0(iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) ' \
                 'AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10'
    PROGRAMS = 'http://webapi.tv4play.se/play/programs?is_active=true&per_page=550&fl=name,nid,program_image,description,category&start=0'
    EPISODES_BASEURL = 'http://webapi.tv4play.se/play/video_assets?sort_order=desc&start=0&'
    VIDEO_BASEURL = 'http://prima.tv4play.se/api/web/asset/{0}/play'
    MOST_VIEWEDURL = 'http://webapi.tv4play.se/play/video_assets/most_viewed?type=episode&platform=web&is_live=false&per_page=32&start=0'
    LIVE_SHOWSURL = 'http://webapi.tv4play.se/play/video_assets?platform=web&is_live=true&per_page=100&sort_order=asc&sort=broadcast_date_time'

    def __init__(self):
        xbmc.log('Starting tv4PlayApi')

    def _get_jsondata(self, url):
        content = self._http_request(url)
        if content is not None and content != '':
            try:
                data = json.loads(content)
                return data
            except Exception as ex:
                raise tv4PlayApiException(ex)
        else:
            return []

    def _http_request(self, url):
        xbmc.log('Requesting URL: {0}'.format(url))
        request = urllib2.Request(url, headers={
            'user-agent': tv4PlayApi.USER_AGENT,
            'Content-Type': 'application/vnd.api+json'
        })
        connection = urllib2.urlopen(request)
        content = connection.read()
        connection.close()
        return content

    def _get_media_format_url(self, data, field):
        xml = ET.XML(data)
        ss = xml.find('items')
        sa = list(ss.iter('item'))
        for i in sa:
            if i.find('mediaFormat').text == field:
                url = i.find('url').text
                return url
        return ''

    def _get_shows(self, type):
        if type == 'most_viewed':
            shows = self._get_jsondata(tv4PlayApi.MOST_VIEWEDURL)
        elif type == 'live_shows':
            shows = self._get_jsondata(tv4PlayApi.LIVE_SHOWSURL)
        showlist = []
        for show in shows['results']:
            # Append only 'program' section for compatibility, but
            # grab 'title', which is more elaborate
            show['program']['name'] = show['title']
            show['program']['id'] = show['id']
            showlist.append(show['program'])
        return showlist

    def get_program_list(self, type):
        if type == 'all':
            programs = self._get_jsondata(tv4PlayApi.PROGRAMS)
            if programs['total_hits'] == '0':
                return []
            return programs['results']
        elif type == 'most_viewed' or type == 'live_shows':
            return self._get_shows(type)
        else:
            return []

    def get_episodes(self, program):
        program_url = tv4PlayApi.EPISODES_BASEURL + urllib.urlencode({'type': 'episode','q': program})
        data = self._get_jsondata(program_url)
        return data['results']

    def get_videodata(self, vid):
        url = tv4PlayApi.VIDEO_BASEURL.format(vid)
        try:
            data = self._http_request(url)
        except urllib2.HTTPError, e:
            data = e.read()
            xml = ET.XML(data)
            code = xml.find('code').text
            raise tv4PlayApiException(code)

        xml = ET.XML(data)
        ss = xml.find('items')
        sa = list(ss.iter('item'))

        if xml.find('drmProtected').text == 'true':
            msg = 'DRM_PROTECTED'
            raise tv4PlayApiException(msg)
        if xml.find('playbackStatus').text == 'NOT_STARTED':
            msg = 'PLAYBACKSTATUS'
            broadcast_time = xml.find('liveBroadcastTime').text
            format = '%Y-%m-%dT%H:%M:%S+02:00'
            #Workarond for strange TypeError
            #These are equivalent according to https://docs.python.org/2/library/datetime.html
            try:
                broadcast_time = datetime.strptime(broadcast_time, format).strftime('%c')
            except TypeError:
                broadcast_time = datetime(*(time.strptime(broadcast_time, format)[0:6])).strftime('%c')

            self.live_broadcast_time = broadcast_time
            raise tv4PlayApiException(msg)

        if xml.find('live').text == 'true':
            self.video_format = 'livehls'
        else:
            self.video_format = 'mp4'

        urls = self.get_videourls(vid)
        return urls

    def get_videourls(self, vid):
        url = tv4PlayApi.VIDEO_BASEURL.format(vid) + '?' + urllib.urlencode({'protocol': 'hls3'})
        data = self._http_request(url)

        videourl = self._get_media_format_url(data, self.video_format)
        if videourl == '':
            msg = "NO_URL_FOUND"
            raise tv4PlayApiException(msg)

        subtitleurl = self._get_media_format_url(data, 'smi')
        return {'videourl' : videourl, 'subtitleurl' : subtitleurl}

    def get_start_time(self):
        return self.live_broadcast_time

    def search(self, search_str):
        search_url = tv4PlayApi.EPISODES_BASEURL + urllib.urlencode({'type': 'episode','q': search_str})
        data = self._get_jsondata(search_url)
        return data['results']

class tv4PlayApiException(Exception):
    pass

if __name__ == '__main__':
    sys.exit(0)
