import re

'''
What's wrong with match1?

1. Being too different from re.search from python stdlib.
In re, match checks if a string follows certain pattern.
What match1 does names re.search and params comes in reverse order,
patterns first.

2. List version of match1 tends to produce long lines of code
'''

b64_patt = r'([A-Za-z0-9/=\+]+)'
dqt_patt = r'\"([^\"]+)\"'
sqt_patt = r"\'([^\']+)\'"
eql_patt = r'\s*[=:]\s*'
#use it with care
tag_patt = r'([^\<]+)'

def first_hit(pattns, text):
    '''find one value from bulks of info with multi patterns. F.I. search title from html with <h1> tags or <og:title> tags. '''
    for patt in pattns:
        hit = re.search(patt, text)
        if hit is not None:
            return hit.group(1)
    return None

def first_hit_multi(pattns_list, text_list):
    '''multi source version of first_hit.
    F.I. search vid from both url and html'''
    for idx in range(len(text_list)):
        text = text_list[idx]
        pattns = pattns_list[idx]
        hit = first_hit(pattns, text)
        if hit is not None:
            return hit
    return None

#multi vals, multi source, multi patterns ver? That dooms to produce long lines.
