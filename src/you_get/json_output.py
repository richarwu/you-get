import json

from .common import current_state

def output(ve, pretty_print=True):
    '''VideoExtractor.download output comes here directly'''
    out = dict(url=ve.url, title=ve.title, site=ve.name, streams=ve.streams)
    try:
        if ve.audiolang:
            out['audiolang'] = ve.audiolang
    except AttributeError:
        pass

    if pretty_print:
        print(json.dumps(out, indent=4, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(out))

# a fake VideoExtractor object to save info
class VideoExtractor(object):
    pass

def download_urls_entry(urls, title, ext, total_size=0, headers={}):
    '''A non-VideoExtractor comes to common.download_urls, then here'''

    stream = dict(container=ext, size=total_size, src=urls)
    if 'Referer' in headers:
        stream['referer'] = headers['Referer']

    if 'User-Agent' in headers:
        stream['user-agent'] = headers['User-Agent']

    ve = VideoExtractor()
    ve.title = title
    ve.url = current_state['url']
    ve.name = current_state['site']
    ve.streams = dict(_default=stream)
    output(ve)

