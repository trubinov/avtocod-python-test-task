import asyncio
import sys
from time import time
import re
import tracemalloc
import aiohttp
from aioredis.client import Redis
import json

headers = {'accept': 'text/html'}
ready_links = dict()
bad_links = list()


def parse_page(url, html, need_links=False):
    links = []
    titles = re.search('\<title\>(.*)\<\/title\>', html)
    title = titles[titles.lastindex]
    if need_links:
        page_links = re.findall('\<a.*href=\"(\S*)\"', html)
        for item in page_links:
            if item.startswith('http'):
                links.append(item.split('#')[0].rstrip('/'))
            elif item.startswith('/'):
                links.append(url + item.split('#')[0].rstrip('/'))
    return title, links


async def load_page(redis, client, url, current_depth):
    result = []
    if url in ready_links or url in bad_links:
        return result
    try:
        async with client.get(url, timeout=5, headers=headers) as r:
            if not (r.status == 200 and 'html' in r.headers['content-type']):
                bad_links.append(url)
            else:
                p_res = parse_page(url, await r.text(), current_depth > 0)
                if p_res is not None:
                    await redis.append(url, p_res[0])
                    ready_links[url] = p_res[0]
                    result.extend(p_res[1])
                else:
                    bad_links.append(url)
    except Exception as ex:
        bad_links.append(url)
    return result


async def load_main_page(url, current_depth):
    tracemalloc.start()
    start_time = time()

    urls = [url]
    redis = Redis()
    async with aiohttp.ClientSession() as c:
        for d in range(current_depth, -1, -1):
            tasks = [asyncio.create_task(load_page(redis, c, u, d)) for u in
                     urls]
            next_level_urls = await asyncio.gather(*tasks)
            urls.clear()
            for item in next_level_urls:
                urls.extend(item)
    await redis.append(f'url:{url}', json.dumps(ready_links))
    await redis.close()
    print(f"Ready links count: {len(ready_links)}")
    print(f"Bad links count: {len(bad_links)}")

    exec_time = round(time() - start_time, 2)
    _, m_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    m_peak = round(m_peak / 10 ** 6, 2)
    print(f"ok, execution time {exec_time} s, peak memory usage is {m_peak} MB")


async def get_links(url, n):
    redis = Redis()
    links = await redis.get(f'url:{url}')
    if links is not None:
        for link, title in json.loads(links).items():
            print(f'{link}: {title}')
            n -= 1
            if n == 0:
                break
    await redis.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    action = sys.argv[1].lower()
    if action == 'load':
        depth = 0
        depth_key = '--depth'
        if depth_key in sys.argv:
            depth_arg = sys.argv[sys.argv.index(depth_key) + 1]
            depth = int(depth_arg) if depth_arg.isdigit() else 0
        loop.run_until_complete(load_main_page(sys.argv[2], depth))
    elif action == 'get':
        n = 2
        n_key = '-n'
        if n_key in sys.argv:
            n_arg = sys.argv[sys.argv.index(n_key) + 1]
            n = int(n_arg) if n_arg.isdigit() else 2
        loop.run_until_complete(get_links(sys.argv[2], n))
    else:
        print(f'Wrong action {action}')
