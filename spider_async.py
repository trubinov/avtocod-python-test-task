import asyncio
import sys
from time import time
import re
import tracemalloc
import aiohttp


headers = {'accept': 'text/html'}
ready_links = dict()
bad_links = list()


async def load_page_links(url, current_depth):
    url = url.rstrip('/')
    if not url.startswith('http'):
        return None
    if url in ready_links or url in bad_links:
        return None
    print(f'{current_depth} ... {url}')
    async with aiohttp.ClientSession() as client:
        try:
            async with client.get(url, timeout=5, headers=headers) as req:
                if req.status == 200 and 'html' in req.headers['content-type']:
                    text = await req.text()
                    titles = re.findall('\<title\>(.*)\<\/title\>', text)
                    if len(titles) > 0:
                        ready_links[url] = titles[0]
                    else:
                        bad_links.append(url)
                    if current_depth == 0:
                        req.close()
                        await client.close()
                        return None
                    links = re.findall('\<a.*href=\"(\S*)\"', text)
                    tasks = []
                    for item in links:
                        if item.startswith('http'):
                            href = item.split('#')[0]
                        elif item.startswith('/'):
                            href = url + item.split('#')[0]
                        else:
                            continue
                        if href not in ready_links or href not in bad_links:
                            tasks.append(asyncio.create_task(
                                load_page_links(href, current_depth - 1)))
                    await asyncio.gather(*tasks)
                else:
                    bad_links.append(url)
        except asyncio.exceptions.TimeoutError as ex:
            bad_links.append(url)


async def load_main_page(url, current_depth):
    tracemalloc.start()
    start_time = time()

    await load_page_links(url, current_depth)
    print(ready_links)
    print(len(ready_links))
    print(bad_links)

    exec_time = time() - start_time
    _, m_peak = tracemalloc.get_traced_memory()
    print(f"ok, execution time {exec_time} s, peak memory usage is {m_peak / 10 ** 6}MB")
    tracemalloc.stop()


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
        loop = asyncio.get_event_loop()
        loop.run_until_complete(load_main_page(sys.argv[2], depth))
    elif action == 'get':
        get_links(sys.argv[1])
    else:
        print(f'Wrong action {action}')
