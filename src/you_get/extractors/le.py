#!/usr/bin/env python

__all__ = ['letv_download', 'letvcloud_download', 'letvcloud_download_by_vu']

import json
import random
import urllib.parse
import xml.etree.ElementTree as ET
import base64, hashlib, urllib, time, re

from ..common import *

def r_shuffle(val, shift):
    shift &= 31
    less_sig = (val & 0xffffffff) >> shift
    more_sig = (val << (32 - shift)) & 0xffffffff
    return less_sig | more_sig

def tkey(t=None):
    if not t:
        t = int(time.time())
    magic = 185025305
    return r_shuffle(t, magic % 17) ^ magic

def decode(data):
    version = data[0:5]
    if version.lower() == b'vc_01':
        #get real m3u8
        loc2 = data[5:]
        length = len(loc2)
        loc4 = [0]*(2*length)
        for i in range(length):
            loc4[2*i] = loc2[i] >> 4
            loc4[2*i+1]= loc2[i] & 15;
        loc6 = loc4[len(loc4)-11:]+loc4[:len(loc4)-11]
        loc7 = [0]*length
        for i in range(length):
            loc7[i] = (loc6[2 * i] << 4) +loc6[2*i+1]
        return ''.join([chr(i) for i in loc7])
    else:
        # directly return
        return data

def create_guid():
    ran = str(random.randint(0, 0xffffffff)).encode('utf8')
    return hashlib.md5(ran).hexdigest()

def video_info(vid, **kwargs):
    flash = False
    flash_params = dict(platid=1, splatid=101, source=1000)
    html5_params = dict(platid=3, splatid=304, source=1001)
    base_url = 'http://player-pc.le.com/mms/out/video/playJson.json?'
    params = dict(id=vid, devid=create_guid(), tkey=tkey())
    params_fixed = {'dvtype': 1000, 'domain': 'www.le.com', 'region':'cn', 'accesyx': 1}

    params.update(params_fixed)
    if flash:
        params.update(flash_params)
    else:
        params.update(html5_params)
    url = base_url + urllib.parse.urlencode(params)
    info = json.loads(get_content(url))['msgs']

    stream_id = None
    stream_seq = ['1080p', '720p', '1300', '1000', '350']
    support_stream_id = info["playurl"]["dispatch"].keys()
    if "stream_id" in kwargs:
        if kwargs["stream_id"].lower() in support_stream_id:
            stream_id = kwargs["stream_id"]
    else:
        print("Current Video Supports:")
        for stream in stream_seq:
            if stream in support_stream_id:
                print("\t--format {:>5} <URL>".format(stream))
                if stream_id is None:
                    stream_id = stream

    host = info['playurl']['domain'][0]
    path = info['playurl']['dispatch'][stream_id][0]
    url = host + path
    uuid = hashlib.sha1(url.encode('utf8')).hexdigest().upper() + '_0'
    ext = info["playurl"]["dispatch"][stream_id][1].split('.')[-1]

    if not flash:
        url = url.replace('tss=0', 'tss=no')
    else:
        url = url.replace('tss=0', 'tss=ios')
    url += "&m3v=1&termid=1&format=1&hwtype=un&ostype=MacOS10.12.4&p1=1&p2=10&p3=-&expect=3&tn={}&vid={}&uuid={}&sign=letv".format(random.random(), vid, uuid)

    info2 = json.loads(get_content(url))
    if not flash:
        return ext, [info2['location']], True
    suffix = '&r=' + str(int(time.time() * 1000)) + '&appid=500'
    m3u8 = get_content(info2["location"] + suffix)
    m3u8_list = decode(m3u8)
    urls = re.findall(r'^[^#][^\r]*', m3u8_list, re.MULTILINE)
    return ext, urls, False

def build_url(segs_list):
    name_patt = r'ver_\d+_\d+_\d+_(\d+)_(\d+)_\d+_\d+_\d+\.ts'
    hit = re.search(name_patt, segs_list[-1])
    seg = int(hit.group(1)) + int(hit.group(2))

    first_fn = re.search(name_patt, segs_list[0]).group(0).split('_')
    first_fn[5] = str(seg)
    fn = '_'.join(first_fn)
    return re.sub(name_patt, fn, segs_list[0])

def letv_download_by_vid(vid,title, output_dir='.', merge=True, info_only=False, **kwargs):
    ext, urls, is_mp4 = video_info(vid, **kwargs)
    if not is_mp4:
        url = build_url(urls)
    else:
        url = urls[0]
    size = urls_size([url])
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls(urls, title, ext, size, output_dir=output_dir, merge=merge)

def letvcloud_download_by_vu(vu, uu, title=None, output_dir='.', merge=True, info_only=False):
    #ran = float('0.' + str(random.randint(0, 9999999999999999))) # For ver 2.1
    #str2Hash = 'cfflashformatjsonran{ran}uu{uu}ver2.2vu{vu}bie^#@(%27eib58'.format(vu = vu, uu = uu, ran = ran)  #Magic!/ In ver 2.1
    argumet_dict ={'cf' : 'flash', 'format': 'json', 'ran': str(int(time.time())), 'uu': str(uu),'ver': '2.2', 'vu': str(vu), }
    sign_key = '2f9d6924b33a165a6d8b5d3d42f4f987'  #ALL YOUR BASE ARE BELONG TO US
    str2Hash = ''.join([i + argumet_dict[i] for i in sorted(argumet_dict)]) + sign_key
    sign = hashlib.md5(str2Hash.encode('utf-8')).hexdigest()
    request_info = urllib.request.Request('http://api.letvcloud.com/gpc.php?' + '&'.join([i + '=' + argumet_dict[i] for i in argumet_dict]) + '&sign={sign}'.format(sign = sign))
    response = urllib.request.urlopen(request_info)
    data = response.read()
    info = json.loads(data.decode('utf-8'))
    type_available = []
    for video_type in info['data']['video_info']['media']:
        type_available.append({'video_url': info['data']['video_info']['media'][video_type]['play_url']['main_url'], 'video_quality': int(info['data']['video_info']['media'][video_type]['play_url']['vtype'])})
    urls = [base64.b64decode(sorted(type_available, key = lambda x:x['video_quality'])[-1]['video_url']).decode("utf-8")]
    size = urls_size(urls)
    ext = 'mp4'
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls(urls, title, ext, size, output_dir=output_dir, merge=merge)

def letvcloud_download(url, output_dir='.', merge=True, info_only=False):
    qs = parse.urlparse(url).query
    vu = match1(qs, r'vu=([\w]+)')
    uu = match1(qs, r'uu=([\w]+)')
    title = "LETV-%s" % vu
    letvcloud_download_by_vu(vu, uu, title=title, output_dir=output_dir, merge=merge, info_only=info_only)

def letv_download(url, output_dir='.', merge=True, info_only=False ,**kwargs):
    url = url_locations([url])[0]
    if re.match(r'http://yuntv.letv.com/', url):
        letvcloud_download(url, output_dir=output_dir, merge=merge, info_only=info_only)
    elif 'sports.le.com' in url:
        html = get_content(url)
        vid = match1(url, r'video/(\d+)\.html')
        title = match1(html, r'<h2 class="title">([^<]+)</h2>')
        letv_download_by_vid(vid, title=title, output_dir=output_dir, merge=merge, info_only=info_only,**kwargs)
    else:
        html = get_content(url)
        vid = match1(url, r'http://www.letv.com/ptv/vplay/(\d+).html') or \
            match1(url, r'http://www.le.com/ptv/vplay/(\d+).html') or \
            match1(html, r'vid="(\d+)"')
        title = match1(html,r'name="irTitle" content="(.*?)"')
        letv_download_by_vid(vid, title=title, output_dir=output_dir, merge=merge, info_only=info_only,**kwargs)

site_info = "Le.com"
download = letv_download
download_playlist = playlist_not_supported('letv')
