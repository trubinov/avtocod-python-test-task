import sys
from time import time
import requests
import re
import tracemalloc


def load_page_links(url, current_depth, ready_links, bad_links):
    url = url.rstrip('/')
    if not url.startswith('http') or url in ready_links or url in bad_links:
        return None
    try:
        req = requests.get(url=url, timeout=3, headers={'accept': 'text/html'})
        req.raise_for_status()
        if 'html' not in req.headers['content-type']:
            raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as ex:
        bad_links.append(url)
        return None
    titles = re.findall('\<title\>(.*)\<\/title\>', req.text)
    if len(titles) > 0:
        ready_links[url] = titles[0]
    else:
        bad_links.append(url)
    if current_depth == 0:
        return None
    links = re.findall('\<a.*href=\"(\S*)\"', req.text)
    for item in links:
        if item.startswith('http'):
            href = item
        elif item.startswith('/'):
            href = url + item
        else:
            continue
        href = href.split('#')[0]
        href = href.rstrip('/')
        if href not in ready_links or href not in bad_links:
            load_page_links(href, current_depth - 1, ready_links, bad_links)
    return None


def load_main_page(url, current_depth):
    tracemalloc.start()
    start_time = time()

    ready_links = dict()
    bad_links = list()
    load_page_links(url, current_depth, ready_links, bad_links)
    print(f"Ready links count: {len(ready_links)}")
    print(f"Bad links count: {len(bad_links)}")

    exec_time = round(time() - start_time, 2)
    _, m_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    m_peak = round(m_peak / 10 ** 6, 2)
    print(f"ok, execution time {exec_time} s, peak memory usage is {m_peak} MB")


def get_links(url):
    pass


if __name__ == '__main__':
    action = sys.argv[1].lower()
    if action == 'load':
        depth = 0
        depth_key = '--depth'
        if depth_key in sys.argv:
            depth_arg = sys.argv[sys.argv.index(depth_key) + 1]
            depth = int(depth_arg) if depth_arg.isdigit() else 0
        load_main_page(sys.argv[2], depth)
    elif action == 'get':
        get_links(sys.argv[1])
    else:
        print(f'Wrong action {action}')
