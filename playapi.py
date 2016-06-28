#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Tomas Melin 2016
#    Basic tv4play API implementation.
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

    def __init__(self):
        xbmc.log('Starting tv4PlayApi')

    def get_jsondata(self, url):

        content = self.http_request(url)
        if content is not None and content != '':
            try:
                data = json.loads(content)
                return data
            except Exception as ex:
                raise tv4PlayApiException(ex)
        else:
            return []

    def http_request(self, url):
        xbmc.log('Requesting URL: {0}'.format(url))
        request = urllib2.Request(url, headers={
            'user-agent': tv4PlayApi.USER_AGENT,
            'Content-Type': 'application/vnd.api+json'
        })
        connection = urllib2.urlopen(request)
        content = connection.read()
        connection.close()
        return content

    def get_programs(self):
        programs = self.get_jsondata(tv4PlayApi.PROGRAMS)
        if programs['total_hits'] == '0':
            return []

        return programs['results']

    def get_episodes(self, program):
        program_url = tv4PlayApi.EPISODES_BASEURL + urllib.urlencode({'type': 'episode','q': program})
        data = self.get_jsondata(program_url)

        return data['results']

    def get_videourl(self, vid):
        url = tv4PlayApi.VIDEO_BASEURL.format(vid)
        try:
            data = self.http_request(url)
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
            raise tv4PlayApiException(msg)

        url =  tv4PlayApi.VIDEO_BASEURL.format(vid) + '?' + urllib.urlencode({'protocol': 'hls'})
        data = self.http_request(url)
        xml = ET.XML(data)
        ss = xml.find('items')
        sa = list(ss.iter('item'))
        for i in sa:
            if i.find('mediaFormat').text == 'mp4':
                url = i.find('url').text
                return url

class tv4PlayApiException(Exception):
    pass

if __name__ == '__main__':
    sys.exit(0)
