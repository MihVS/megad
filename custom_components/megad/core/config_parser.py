import re

import aiohttp
import asyncio


async def async_fetch_page(url: str, session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as e:
        print(f"Error fetching {url}: {e}")


async def async_parse_pages(url: str, session: aiohttp.ClientSession):
    pages = ["cf=1", "cf=2", "cf=7", "cf=8"]

    first_page = await async_fetch_page(url, session)
    if first_page and "IN/OUT" in first_page:
        ports = 45 if "[44," in first_page else 37
    else:
        ports_match = re.findall(r'/sec/\?pt=(\d+)', first_page or "")
        if ports_match:
            ports = max(
                map(int, ports_match))
        else:
            ports = 0

    pages.extend(f"pt={i}" for i in range(ports + 1))
    pages.extend(f"cf=10&prn={i}" for i in range(10))
    pages.extend(f"cf=11&pid={i}" for i in range(5))
    pages.extend(f"cf=6&sc={i}" for i in range(5))
    pages.extend(f"cf=6&el={i}" for i in range(16))

    return url, pages


# async def async_process_page(base_url, page, dom, fh):
#     url = ""
#     page_content = await async_fetch_page(f"{base_url}?{page}")
#     if not page_content:
#         return
#
#     soup = BeautifulSoup(page_content, 'lxml')
#     for inp in soup.find_all('input'):
#         if inp.get('type') != "submit":
#             name = inp.get('name')
#             value = inp.get('value', '')
#             if inp.get('type') == "checkbox":
#                 value = 'on' if inp.has_attr('checked') else ''
#             url += f"{name}={urllib.parse.quote(value)}&"
#
#     for select in soup.find_all('select'):
#         name = select.get('name')
#         selected_option = select.find('option', selected=True)
#         if selected_option:
#             value = selected_option.get('value', '')
#             url += f"{name}={urllib.parse.quote(value)}&"
#
#     url = url.rstrip('&')
#     if url and url != 'cf=<br':
#         fh.write(url + "\n")
#
#
# def read_configuration(options):
#     base_url, pages = parse_pages(options['ip'], options['p'])
#     output_file = options['read-conf']
#
#     with open(output_file, 'w', encoding='utf-8') as fh:
#         for page in pages:
#             process_page(base_url, page, BeautifulSoup, fh)
#             time.sleep(0.02)
