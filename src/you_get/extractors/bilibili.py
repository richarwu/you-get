#!/usr/bin/env python

__all__ = ['bilibili_download']

import hashlib
import re
import time
import json
import http.cookiejar
import urllib.request
from xml.dom.minidom import parseString

from ..patt import *
from ..common import *
from ..util.log import *
from ..extractor import *

from .qq import qq_download_by_vid
from .sina import sina_download_by_vid
from .tudou import tudou_download_by_id
from .youku import youku_download_by_vid


SECRETKEY_MINILOADER = '1c15888dc316e05a15fdd0a02ed6584f'
SEC2 = '9b288147e5474dd2aa67085f716c560d'

class Bilibili(VideoExtractor):
    name = 'Bilibili'
    live_api = 'http://live.bilibili.com/api/playurl?cid={}&otype=json'
    api_url = 'http://interface.bilibili.com/playurl?'
    bangumi_api_url = 'http://bangumi.bilibili.com/player/web_api/playurl?'
    
    SEC1 = '1c15888dc316e05a15fdd0a02ed6584f'
    SEC2 = '9b288147e5474dd2aa67085f716c560d'
    stream_types = [
            {'id': 'hdflv'},
            {'id': 'flv'},
            {'id': 'hdmp4'},
            {'id': 'mp4'},
            {'id': 'live'}
    ]
    fmt2qlt = dict(hdflv=4, flv=3, hdmp4=2, mp4=1)

    @staticmethod
    def bilibili_stream_type(urls):
        url = urls[0]
        if 'hd.flv?' in url:
            return 'hdflv', 'flv'
        if '.flv?' in url:
            return 'flv', 'flv'
        if 'hd.mp4?' in url:
            return 'hdmp4', 'mp4'
        if '.mp4?' in url:
            return 'mp4', 'mp4'
        raise Exception('Unknown stream type')

    def api_req(self, cid, quality, bangumi):
        ts = str(int(time.time()))
        if not bangumi:
            params_str = 'cid={}&player=1&quality={}&ts={}'.format(cid, quality, ts)
            chksum = hashlib.md5(bytes(params_str+self.SEC1, 'utf8')).hexdigest()
            api_url = self.api_url + params_str + '&sign=' + chksum
        else:
            params_str = 'cid={}&module=bangumi&player=1&quality={}&ts={}'.format(cid, quality, ts)
            chksum = hashlib.md5(bytes(params_str+self.SEC2, 'utf8')).hexdigest()
            api_url = self.bangumi_api_url + params_str + '&sign=' + chksum

        xml_str = get_content(api_url)
        return xml_str

    def parse_bili_xml(self, xml_str):
        urls_list = []
        total_size = 0
        doc = parseString(xml_str.encode('utf8'))
        durls = doc.getElementsByTagName('durl')
        for durl in durls:
            size = durl.getElementsByTagName('size')[0]
            total_size += int(size.firstChild.nodeValue)
            url = durl.getElementsByTagName('url')[0]
            urls_list.append(url.firstChild.nodeValue)
        stream_type, container = self.bilibili_stream_type(urls_list)
        if stream_type not in self.streams:
            self.streams[stream_type] = {}
            self.streams[stream_type]['src'] = urls_list
            self.streams[stream_type]['size'] = total_size
            self.streams[stream_type]['container'] = container

    def download_by_vid(self, cid, bangumi, **kwargs):
        stream_id = kwargs.get('stream_id')
#guard here. if stream_id invalid, fallback as not stream_id
        if stream_id and stream_id in self.fmt2qlt:
            quality = stream_id
        else:
            quality = 'hdflv' if bangumi else 'flv'

        info_only = kwargs.get('info_only')
        if not info_only or stream_id:
#won't be None
            qlt = self.fmt2qlt.get(quality)
            api_xml = self.api_req(cid, qlt, bangumi)
            self.parse_bili_xml(api_xml)
            self.danmuku = get_danmuku_xml(cid)
        else:
            for qlt in range(4, 0, -1):
                api_xml = self.api_req(cid, qlt, bangumi)
                self.parse_bili_xml(api_xml)

    def prepare(self, **kwargs):
        self.ua = fake_headers['User-Agent']
        self.url = url_locations([self.url])[0]
        self.referer = self.url
        self.page = get_content(self.url)
        self.title = first_hit([r'<h1\s*title='+dqt_patt], self.page)
        if 'subtitle' in kwargs:
            subtitle = kwargs['subtitle']
            self.title = '{} {}'.format(self.title, subtitle)

        if 'bangumi.bilibili.com' in self.url:
            self.bangumi_entry(**kwargs)
        elif 'live.bilibili.com' in self.url:
            self.live_entry(**kwargs)
        else:
            self.entry(**kwargs)

    def entry(self, **kwargs):
#tencent player
        tc_flashvars = first_hit([r'"bili-cid=\d+&bili-aid=\d+&vid=([^"]+)"'], self.page)
        if tc_flashvars is not None:
            self.out = True
            qq_download_by_vid(tc_flashvars, self.title, output_dir=kwargs['output_dir'], merge=kwargs['merge'], info_only=kwargs['info_only'])
            return

        cid = first_hit([r'cid=(\d+)'], self.page)
        if cid is not None:
            self.download_by_vid(cid, False, **kwargs)
        else:
#flashvars?
            flashvars = first_hit([r'flashvars='+dqt_patt], self.page)
            if flashvars is None:
                raise Exception('Unsupported page {}'.format(self.url))
            param = flashvars.split('&')[0]
            t, cid = param.split('=')
            t = t.strip()
            cid = cid.strip()
            if t == 'vid':
                sina_download_by_vid(cid, self.title, output_dir=kwargs['output_dir'], merge=kwargs['merge'], info_only=kwargs['info_only'])
            elif t == 'ykid':
                youku_download_by_vid(cid, self.title, output_dir=kwargs['output_dir'], merge=kwargs['merge'], info_only=kwargs['info_only'])
            elif t == 'uid':
                tudou_download_by_id(cid, self.title, output_dir=kwargs['output_dir'], merge=kwargs['merge'], info_only=kwargs['info_only'])
            else:
                raise NotImplementedError('Unknown flashvars {}'.format(flashvars))
            return

    def live_entry(self, **kwargs):
        self.title = first_hit([r'<title>'+tag_patt], self.page)
        self.room_id = first_hit([r'ROOMID'+eql_patt+r'(\d+)'], self.page)
        api_url = self.live_api.format(self.room_id)
        json_data = json.loads(get_content(api_url))
        urls = [json_data['durl'][0]['url']]

        self.streams['live'] = {}
        self.streams['live']['src'] = urls
        self.streams['live']['container'] = 'flv'
        self.streams['live']['size'] = 0

    def bangumi_entry(self, **kwargs):
        bangumi_id = first_hit([r'(\d+)'], self.url)
        bangumi_data = get_bangumi_info(bangumi_id)
        bangumi_payment = bangumi_data.get('payment')
        if bangumi_payment and bangumi_payment['price'] != '0':
            log.w("It's a paid item")
        ep_ids = collect_bangumi_epids(bangumi_data)
        episode_id = first_hit_multi([[r'#(\d+)$'], [r'first_ep_id\s*=\s*"(\d+)"']], [self.url, self.page])
        cont = post_content('http://bangumi.bilibili.com/web_api/get_source', post_data=dict(episode_id=episode_id))
        cid = json.loads(cont)['result']['cid']
        cont = get_content('http://bangumi.bilibili.com/web_api/episode/{}.json'.format(episode_id))
        ep_info = json.loads(cont)['result']['currentEpisode']

        long_title = ep_info['longTitle']
        aid = ep_info['avId']

        idx = 0
        while ep_ids[idx] != episode_id:
            idx += 1

        self.title = '{} [{} {}]'.format(self.title, idx+1, long_title)
        self.download_by_vid(cid, bangumi=True, **kwargs)


def check_oversea():
    url = 'https://interface.bilibili.com/player?id=cid:17778881'
    xml_lines = get_content(url).split('\n')
    for line in xml_lines:
        key = line.split('>')[0][1:]
        if key == 'country':
            value = line.split('>')[1].split('<')[0]
            if value != '中国':
                return True
            else:
                return False
    return False

def check_sid():
    if not cookies:
        return False
    for cookie in cookies:
        if cookie.domain == '.bilibili.com' and cookie.name == 'sid':
            return True
    return False

def fetch_sid(cid, aid):
    url = 'http://interface.bilibili.com/player?id=cid:{}&aid={}'.format(cid, aid)
    cookies = http.cookiejar.CookieJar()
    req = urllib.request.Request(url)
    res = urllib.request.urlopen(url)
    cookies.extract_cookies(res, req)
    for c in cookies:
        if c.domain == '.bilibili.com' and c.name == 'sid':
            return c.value
    raise

def sign(cid, fallback=False, oversea=False):
    base_req = 'cid={}&player=1'.format(cid)
    if oversea:
        base_req = 'accel=1&' + base_req
    if fallback:
        base_req += '&quality=2'
    base_req = base_req + '&ts=' + str(int(time.time()))
    to_sign = (base_req + SECRETKEY_MINILOADER).encode('utf8')
    return base_req + '&sign=' + hashlib.md5(to_sign).hexdigest()

def sign_bangumi(cid, ts = None):
    if ts is None:
        ts = str(int(time.time()))
    base_req = 'cid={}&module=bangumi&player=1&quality=1&ts={}'.format(cid, ts)
    to_sign = (base_req + SEC2).encode('utf8')
    return base_req + '&sign=' + hashlib.md5(to_sign).hexdigest()

def collect_bangumi_epids(json_data):
    eps = json_data['result']['episodes']
    result = []
    for ep in eps:
        result.append(ep['episode_id'])
    return sorted(result)

def get_bangumi_info(bangumi_id):
    BASE_URL = 'http://bangumi.bilibili.com/jsonp/seasoninfo/'
    long_epoch = int(time.time() * 1000)
    req_url = BASE_URL + bangumi_id + '.ver?callback=seasonListCallback&jsonp=jsonp&_=' + str(long_epoch)
    season_data = get_content(req_url)
    season_data = season_data[len('seasonListCallback('):]
    season_data = season_data[: -1 * len(');')]
    json_data = json.loads(season_data)
    return json_data

def get_danmuku_xml(cid):
    return get_content('http://comment.bilibili.com/{}.xml'.format(cid))

def parse_cid_playurl(xml):
    from xml.dom.minidom import parseString
    try:
        urls_list = []
        total_size = 0
        doc = parseString(xml.encode('utf-8'))
        durls = doc.getElementsByTagName('durl')
        cdn_cnt = len(durls[0].getElementsByTagName('url'))
        for i in range(cdn_cnt):
            urls_list.append([])
        for durl in durls:
            size = durl.getElementsByTagName('size')[0]
            total_size += int(size.firstChild.nodeValue)
            cnt = len(durl.getElementsByTagName('url'))
            for i in range(cnt):
                u = durl.getElementsByTagName('url')[i].firstChild.nodeValue
                urls_list[i].append(u)
        return urls_list, total_size
    except Exception as e:
        log.w(e)
        return [], 0

def test_bili_cdns(urls_list):
    import urllib.error
    headers = {}
    headers['Referer'] = 'bilibili.com'
    headers['User-Agent'] = 'Mozilla/5.0'
    for pos, urls in enumerate(urls_list):
        try:
            _, t, size = url_info(urls[0], headers=headers)
        except urllib.error.HTTPError:
            log.w('HTTPError with url '+urls[0])
        else:
            return pos, t, size
    return -1, None, 0

def bilibili_download_by_cid(cid, title, output_dir='.', merge=True, info_only=False, is_bangumi=False, aid=None, oversea=False):
        endpoint = 'https://interface.bilibili.com/playurl?'
        endpoint_paid = 'https://bangumi.bilibili.com/player/web_api/playurl?'
        if is_bangumi:
            if not check_sid():
                sid_cstr = 'sid=' + fetch_sid(cid, aid)
                headers = dict(referer='bilibili.com', cookie=sid_cstr)
            else:
                headers = dict(referer='bilibili.com')
            url = endpoint_paid + sign_bangumi(cid)
        else:
            url = endpoint + sign(cid, oversea=oversea)
            headers = dict(referer='bilibili.com')
        content = get_content(url, headers)
        urls_list, size = parse_cid_playurl(content)
        pos, type_, mp4size = test_bili_cdns(urls_list)
        if pos == -1:
            if is_bangumi:
                log.wtf('All CDNs failed so You Can NOT Advance')
                raise
            else:
                log.w('CDNs failed. Trying fallback')
                url = endpoint + sign(cid, fallback=True, oversea=oversea)
                headers = dict(referer='bilibili.com')
                content = get_content(url, headers)
                urls_list, size = parse_cid_playurl(content)
                pos, type_, mp4size = test_bili_cdns(urls_list)
                if pos == -1:
                    log.wtf('Fallback tried but no luck')
                    raise
        if '.mp4' in urls_list[0]:
            size = mp4size
        urls = [i
                if not re.match(r'.*\.qqvideo\.tc\.qq\.com', i)
                else re.sub(r'.*\.qqvideo\.tc\.qq\.com', 'http://vsrc.store.qq.com', i)
                for i in urls_list[pos]]

        print_info(site_info, title, type_, size)
        if not info_only:
            while True:
                try:
                    headers = {}
                    headers['Referer'] = 'bilibili.com'
                    headers['User-Agent'] = 'Mozilla/5.0'
                    download_urls(urls, title, type_, total_size=size, output_dir=output_dir, merge=merge, timeout=15, headers=headers)
                except socket.timeout:
                    continue
                else:
                    break


def bilibili_live_download_by_cid(cid, title, output_dir='.', merge=True, info_only=False):
    api_url = 'http://live.bilibili.com/api/playurl?cid=' + cid + '&otype=json'
    json_data = json.loads(get_content(api_url))
    urls = [json_data['durl'][0]['url']]

    for url in urls:
        _, type_, _ = url_info(url)
        size = 0
        print_info(site_info, title, type_, size)
        if not info_only:
            download_urls([url], title, type_, total_size=None, output_dir=output_dir, merge=merge)


def bilibili_download(url, output_dir='.', merge=True, info_only=False, **kwargs):
    print(kwargs)
    print(kwargs['index'])
    #oversea = check_oversea()
    oversea = False
    url = url_locations([url])[0]
    html = get_content(url)

    title = r1_of([r'<meta name="title" content="\s*([^<>]{1,999})\s*" />',
                   r'<h1\s*title="([^\"]+)">.*</h1>'], html)
    if title:
        title = unescape_html(title)
        title = escape_file_path(title)

    if re.match(r'https?://bangumi\.bilibili\.com/', url):
        # quick hack for bangumi URLs
        bangumi_id = match1(url, r'(\d+)')
        bangumi_data = get_bangumi_info(bangumi_id)
        if bangumi_data['result'].get('payment') and bangumi_data['result']['payment']['price'] != '0':
            log.w("It's a paid item")
        ep_ids = collect_bangumi_epids(bangumi_data)
        episode_id = r1(r'#(\d+)$', url) or r1(r'first_ep_id = "(\d+)"', html)
        cont = post_content('http://bangumi.bilibili.com/web_api/get_source',
                            post_data={'episode_id': episode_id})
        cid = json.loads(cont)['result']['cid']
        cont = get_content('http://bangumi.bilibili.com/web_api/episode/' + episode_id + '.json')
        ep_info = json.loads(cont)
        long_title = ep_info['result']['currentEpisode']['longTitle']
        aid = ep_info['result']['currentEpisode']['avId']
        idx = 0
        while ep_ids[idx] != episode_id:
            idx += 1
        title = '%s [%s %s]' % (title, idx+1, long_title)
        bilibili_download_by_cid(str(cid), title, output_dir=output_dir, merge=merge, info_only=info_only, is_bangumi=True, aid=aid, oversea=oversea)

    else:
        tc_flashvars = match1(html, r'"bili-cid=\d+&bili-aid=\d+&vid=([^"]+)"')
        if tc_flashvars is not None:
            qq_download_by_vid(tc_flashvars, title, output_dir=output_dir, merge=merge, info_only=info_only)
            return

        flashvars = r1_of([r'(cid=\d+)', r'(cid: \d+)', r'flashvars="([^"]+)"',
                           r'"https://[a-z]+\.bilibili\.com/secure,(cid=\d+)(?:&aid=\d+)?"', r'(ROOMID\s*=\s*\d+)'], html)
        assert flashvars
        flashvars = flashvars.replace(': ', '=')
        t, cid = flashvars.split('=', 1)
        t = t.strip()
        cid = cid.split('&')[0].strip()
        if t == 'cid' or t == 'ROOMID':
            if re.match(r'https?://live\.bilibili\.com/', url):
                title = r1(r'<title>\s*([^<>]+)\s*</title>', html)
                bilibili_live_download_by_cid(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)

            else:
                # multi-P
                cids = []
                pages = re.findall('<option value=\'([^\']*)\'', html)
                titles = re.findall('<option value=.*>\s*([^<>]+)\s*</option>', html)
                for i, page in enumerate(pages):
                    html = get_html("http://www.bilibili.com%s" % page)
                    flashvars = r1_of([r'(cid=\d+)',
                                       r'flashvars="([^"]+)"',
                                       r'"https://[a-z]+\.bilibili\.com/secure,(cid=\d+)(?:&aid=\d+)?"'], html)
                    if flashvars:
                        t, cid = flashvars.split('=', 1)
                        cids.append(cid.split('&')[0])
                    if url.endswith(page):
                        cids = [cid.split('&')[0]]
                        titles = [titles[i]]
                        break

                # no multi-P
                if not pages:
                    cids = [cid]
                    titles = [r1(r'<option value=.* selected>\s*([^<>]+)\s*</option>', html) or title]
                for i in range(len(cids)):
                    completeTitle=None
                    if (title == titles[i]):
                        completeTitle=title
                    else:
                        completeTitle=title+"-"+titles[i]#Build Better Title
                    bilibili_download_by_cid(cids[i],
                                             completeTitle,
                                             output_dir=output_dir,
                                             merge=merge,
                                             info_only=info_only,
                                             oversea=oversea)

        elif t == 'vid':
            sina_download_by_vid(cid, title=title, output_dir=output_dir, merge=merge, info_only=info_only)
        elif t == 'ykid':
            youku_download_by_vid(cid, title=title, output_dir=output_dir, merge=merge, info_only=info_only)
        elif t == 'uid':
            tudou_download_by_id(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)
        else:
            raise NotImplementedError(flashvars)

    if not info_only and not dry_run:
        if not kwargs['caption']:
            print('Skipping danmaku.')
            return
        title = get_filename(title)
        print('Downloading %s ...\n' % (title + '.cmt.xml'))
        xml = get_srt_xml(cid)
        with open(os.path.join(output_dir, title + '.cmt.xml'), 'w', encoding='utf-8') as x:
            x.write(xml)

def bilibili_download_playlist_by_url(url, **kwargs):
    url = url_locations([url])[0]
    if 'live.bilibili' in url:
        site.download_by_url(url)
    elif 'bangumi.bilibili' in url:
        bangumi_id = first_hit([r'(\d+)'], url)
        bangumi_data = get_bangumi_info(bangumi_id)
        ep_ids = collect_bangumi_epids(bangumi_data)

        base_url = url.split('#')[0]
        for ep_id in ep_ids:
            ep_url = '#'.join([base_url, ep_id])
            Bilibili().download_by_url(ep_url, **kwargs)
    else:
        aid = first_hit([r'av(\d+)'], url)
        page_list = json.loads(get_content('http://www.bilibili.com/widget/getPageList?aid={}'.format(aid)))
        page_cnt = len(page_list)
        for no in range(1, page_cnt+1):
            page_url = 'http://www.bilibili.com/video/av{}/index_{}.html'.format(aid, no)
            subtitle = page_list[no-1]['pagename']
            Bilibili().download_by_url(page_url, subtitle=subtitle, **kwargs)

site = Bilibili()
'''
site_info = "bilibili.com"
download = bilibili_download
download_playlist = bilibili_download
'''
download = site.download_by_url
download_playlist = bilibili_download_playlist_by_url
