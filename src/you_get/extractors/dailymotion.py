#!/usr/bin/env python

__all__ = ['dailymotion_download']

from ..common import *
import urllib.parse as up

def extract_m3u(url):
    content = get_content(url)
    m3u_url = re.findall(r'http://.*', content)[0]
    return match1(m3u_url, r'([^#]+)')

def dailymotion_download(url, output_dir = '.', merge = True, info_only = False, **kwargs):
    """Downloads Dailymotion videos by URL.
    """
    url = up.quote(url, safe=':/?&#')

    html = get_content(url)
    info = json.loads(match1(html, r'qualities":({.+?}),"'))
    title = match1(html, r'"video_title"\s*:\s*"([^"]+)"') or \
            match1(html, r'"title"\s*:\s*"([^"]+)"')

    for quality in ['1080','720','480','380','240','144','auto']:
        try:
            stream_data = info[quality]
            m3u8_url = None
            mp4_url = None
            for stream in stream_data:
                if stream['type'] == 'application/x-mpegURL':
                    m3u8_url = stream['url']
                elif stream['type'] == 'video/mp4':
                    mp4_url = stream['url']
            if m3u8_url or mp4_url:
                break
        except KeyError:
            pass

    if mp4_url:
        mime, ext, size = url_info(mp4_url)
    elif m3u8_url:
        m3u_url = extract_m3u(m3u8_url)
        mime, ext, size = url_info(m3u_url) 

    print_info(site_info, title, mime, size)
    if not info_only:
        if mp4_url:
            donwload_urls(mp4_url, title, ext, size, output_dir=output_dir)
        elif m3u8_url:
            download_url_ffmpeg(m3u_url, title, ext, output_dir=output_dir, merge=merge, stream=False)

site_info = "Dailymotion.com"
download = dailymotion_download
download_playlist = playlist_not_supported('dailymotion')
