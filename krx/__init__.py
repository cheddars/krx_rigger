import requests
import time
import re
import logging
from bs4 import BeautifulSoup
from cache import AdtCache

HEADER = {
    "USER_AGENT" : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    "SEC_CH_UA": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"'
}

logger = logging.getLogger("krx_api")


class KrxKindWeb:
    def __init__(self, cache: AdtCache):
        self.session = requests.Session()
        self.cache = cache
        headers = {
            'authority': 'kind.krx.co.kr',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': HEADER["SEC_CH_UA"],
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': HEADER["USER_AGENT"],
        }

        self.session.get('https://kind.krx.co.kr/', headers=headers)

        time.sleep(0.3)

        self.session.headers.update({
            'referer': 'https://kind.krx.co.kr/',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': None,
        })

        params = {
            'method': 'loadInitPage',
            'scrnmode': '1',
        }

        response = self.session.get('https://kind.krx.co.kr/main.do', params=params)
        logger.info(response.status_code)

    def fetch_list(self, dt, time_sleep=0.3):

        results = []
        page = 1
        total_page = 1
        page_no = 0

        while page <= total_page:
            items = self._fetch_list(dt, page=page)

            if items is not None:
                total_count = items.get('total_count')
                total_page = items.get('total_page')
                page_no = items.get('page')
                page = page + 1

                logger.info(f"dt : {dt}, total_count : {total_count}, total_page : {total_page}, current_page : {page_no}")

                result = items.get("items")

                if self.cache is not None:
                    ## check cache
                    cache_key = f"krxweb_list_{dt}"
                    keys = [x.get("doc_id") for x in result]
                    diff = self.cache.differential(cache_key, keys)
                    logger.debug(f"diff : {diff}, cached keys : {len(self.cache.keys())}")
                    diff_ratio = float(len(diff)) / float(len(result)) * 100
                    if diff_ratio == float(0):
                        logger.info(f"diff ratio is {diff_ratio}% => break")
                        break
                    else:
                        logger.info(f"diff ratio is {diff_ratio}%")
                        results.extend([x for x in result if x.get("doc_id") in diff])
                        self.cache.push_values(cache_key, keys)

                        if diff_ratio < 80:
                            logger.info(f"break")
                            break
                        else:
                            logger.info(f"pause {time_sleep} sec...")
                            time.sleep(time_sleep)
                            continue
                else:
                    results.extend(result)

                if total_page == page_no:
                    logger.info(f"total page reached {total_page}")
                    break

        return results


    def _fetch_list(self, dt, page=1):
        headers = {
            'authority': 'kind.krx.co.kr',
            'accept': 'text/html, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://kind.krx.co.kr',
            'pragma': 'no-cache',
            'referer': 'https://kind.krx.co.kr/disclosure/todaydisclosure.do?method=searchTodayDisclosureMain',
            'sec-ch-ua': HEADER["SEC_CH_UA"],
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': HEADER["USER_AGENT"],
            'x-requested-with': 'XMLHttpRequest',
        }

        data = {
            'method': 'searchTodayDisclosureSub',
            'currentPageSize': '100',
            'pageIndex': page,
            'orderMode': '0',
            'orderStat': 'D',
            'marketType': '',
            'forward': 'todaydisclosure_sub',
            'searchMode': '',
            'searchCodeType': '',
            'chose': 'S',
            'todayFlag': 'N',
            'repIsuSrtCd': '',
            'kosdaqSegment': '',
            'selDate': dt,
            'searchCorpName': '',
            'copyUrl': '',
        }

        response = self.session.post('https://kind.krx.co.kr/disclosure/todaydisclosure.do', headers=headers, data=data)
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_list(soup, dt)

    def _parse_list(self, soup, dt):
        info_div = soup.select("div.info")
        if len(info_div) < 1:
            return None
        page_info = soup.select("div.info")[0].text.replace("\xa0", "").replace("\r", "").split("\n")
        current_page, total_page = map(lambda x: int(x), page_info[1].split(":")[1].strip().split("/"))
        total_count = soup.select("div.info")[0].select("em")[0].text
        trs = soup.find("table").select("tr")
        items = list(filter(lambda x: x is not None, [self._tr2dict(tr, dt) for tr in trs[1:]]))
        return {
            "page": current_page,
            "total_page": total_page,
            "total_count": total_count,
            "items": items
        }

    def _tr2dict(self, tr, dt):
        def extract_cid(text):
            matches = re.search(r"companysummary_open\('(\d*)'\);.*", text, re.MULTILINE)
            return matches.group(1) if matches is not None and len(matches.groups()) > 0 else None

        def extract_kid(text):
            matches = re.search(r"openDisclsViewer\('([0-9]*)',''\)", text, re.MULTILINE)
            return matches.group(1) if len(matches.groups()) > 0 else None

        links = tr.select("a", {"href": "#viewer"})
        if len(links) < 2:
            return None
        company = links[0].text.strip()
        c_link = links[0].get("onclick")
        company_id = extract_cid(c_link)
        title = links[1].text.strip()
        link_script = links[1].get("onclick")
        doc_id = extract_kid(link_script)
        tds = tr.select("td")
        time = tds[0].text
        org = tds[3].text
        return {
            "dt": dt,
            "time": time,
            "company": company,
            "company_id": company_id,
            "doc_id": doc_id,
            "title": title,
            "org": org
        }
