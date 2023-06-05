from typing import Tuple
import os
import requests
import time
import re
import logging
from bs4 import BeautifulSoup
from cache import AdtCache, MemoryCache

from krx.parser import parse_corp_list

HEADER = {
    "USER_AGENT" : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    "SEC_CH_UA": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"'
}



def _extract_digit(value):
    return re.sub(r'[^\d]', '', value)


class KrxKindWeb:
    def __init__(self, cache: AdtCache = None, file_cache_dir: str = None):
        self.logger = logging.getLogger("krx_api")
        self.session = requests.Session()
        if cache is None:
            self.logger.info("Cache is not provided. Use MemoryCache")
            cache = MemoryCache()

        self.cache = cache
        self.file_cache_dir = file_cache_dir
        if file_cache_dir is not None:
            self.logger.info(f"File cache is enabled. Cache directory: {file_cache_dir}")

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
        self.logger.info(response.status_code)

    def corp_list(self, time_sleep=0.6):
        """
        KIND > 상장법인상세정보 > 상장법인목록 전체 페이지 가져옴
        :param time_sleep:
        :return:
        """
        results = []
        page = 1
        total_page = 1

        while page <= total_page:
            items = self._corp_list(page=page)

            if items is not None:
                total_count = items.get('total_count')
                total_page = items.get('total_page')
                page_no = items.get('page')
                page = page + 1

                self.logger.info(f"total_count : {total_count}, total_page : {total_page}, current_page : {page_no}")

                result = items.get("items")
                results.extend(result)

                if total_page == page_no:
                    self.logger.info(f"total page reached {total_page}")
                    break

                self.logger.info(f"pause {time_sleep} sec...")
                time.sleep(time_sleep)
                continue
        return results

    def fetch_list(self, dt, time_sleep=0.3):

        results = []
        page = 1
        total_page = 1

        while page <= total_page:
            items = self._fetch_list(dt, page=page)

            if items is not None:
                total_count = items.get('total_count')
                total_page = items.get('total_page')
                page_no = items.get('page')
                page = page + 1

                self.logger.info(f"dt : {dt}, total_count : {total_count}, total_page : {total_page}, current_page : {page_no}")

                result = items.get("items")

                if self.cache is not None:
                    ## check cache
                    cache_key = f"krxweb_list_{dt}"
                    keys = [x.get("doc_id") for x in result]
                    diff = self.cache.differential(cache_key, keys)
                    self.logger.debug(f"diff : {diff}, cached keys : {len(self.cache.keys())}")
                    diff_ratio = float(len(diff)) / float(len(result)) * 100 if len(result) > 0 else float(0)

                    if diff_ratio == float(0):
                        self.logger.info(f"diff ratio is {diff_ratio}% => break")
                        break
                    else:
                        self.logger.info(f"diff ratio is {diff_ratio}%")
                        results.extend([x for x in result if x.get("doc_id") in diff])
                        self.cache.push_values(cache_key, keys)

                        if diff_ratio < 80:
                            self.logger.info(f"break")
                            break
                        else:
                            self.logger.info(f"pause {time_sleep} sec...")
                            time.sleep(time_sleep)
                            continue
                else:
                    results.extend(result)

                if total_page == page_no:
                    self.logger.info(f"total page reached {total_page}")
                    break

        return results

    def get_document_link(self, doc_id):
        cache_dir_prefix = "links"
        text = self._read_cache(cache_file_name="link_{}.html", dir_prefix=cache_dir_prefix, doc_id=doc_id)

        if text is None:
            viewport_url = f'https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno={doc_id}&docno=&viewerhost=&viewerport='
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
            response = self.session.get(viewport_url, headers=headers)
            self.logger.debug("status : " + str(response.status_code))
            text = response.text
            self._write_cache(cache_file_name="link_{}.html", dir_prefix=cache_dir_prefix, doc_id=doc_id, text=text)

        self.logger.debug("text : " + text)
        soup = BeautifulSoup(text, 'lxml')
        doc_elem = soup.find(attrs={'selected': 'selected'})

        documents = []

        if '[정정]' in doc_elem.text:
            options = [opt for opt in soup.select('select#mainDoc option') if opt['value']]
            # 최신순 정렬
            options.reverse()

            for opt in options:
                # 제일 최신 보고서 (순서상 제일 앞 위치)
                doc_code = _extract_digit(opt['value'])
                link = self._get_docurl(doc_code)
                category = '정정' if options[0] == opt else '정정전'
                documents.append({"link": link, "category": category })
        else:
            doc_code = doc_elem['value'].split('|')[0]
            link = self._get_docurl(doc_code)
            documents.append({"link": link, "category": "신규"})
        return documents

    def _write_cache(self, cache_file_name, dir_prefix, doc_id, text):
        if self.file_cache_dir is not None:
            yyyy = doc_id[0:4]
            mm = doc_id[4:6]
            dd = doc_id[6:8]

            cache_base_dir = os.path.join(self.file_cache_dir, dir_prefix, yyyy, mm, dd)
            os.makedirs(cache_base_dir, exist_ok=True)
            file_path = os.path.join(cache_base_dir, cache_file_name.format(doc_id))
            self.logger.debug(f"write cache file : {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)

    def _read_cache(self, cache_file_name, dir_prefix, doc_id):
        yyyy = doc_id[0:4]
        mm = doc_id[4:6]
        dd = doc_id[6:8]

        text = None
        if self.file_cache_dir is not None:
            cache_base_dir = os.path.join(self.file_cache_dir, dir_prefix, yyyy, mm, dd)
            file_path = os.path.join(cache_base_dir, cache_file_name.format(doc_id))
            self.logger.debug(f"check cached file exists : {file_path}")
            if os.path.exists(file_path):
                self.logger.info(f"{doc_id} file exists, use cache : {file_path}")
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
        return text

    def get_document_html(self, doc_id, link=None) -> Tuple[str, str]:
        """
        해당 doc_id 에 연결된 link 중 첫번째 링크의 html과 link 를 반환한다
        :param doc_id:
        :param link: link_url 을 이미 알고 있는 경우엔 link 전달
        :return:
        """
        cache_dir_prefix = "docs"
        html_link = link
        if html_link is None:
            documents = self.get_document_link(doc_id)
            if documents is None or len(documents) == 0:
                return None, None
            first_doc = documents[0]
            html_link = first_doc.get("link")
            self.logger.info(f"doc_id : {doc_id}, link : {html_link}")

        text = self._read_cache(cache_file_name="html_{}.html", dir_prefix=cache_dir_prefix, doc_id=doc_id)
        if text is not None:
            return text, link

        response = self.session.get(html_link)

        if response.status_code != 200:
            self.logger.error(f"doc_id : {doc_id}, link : {html_link}, status_code : {response.status_code}")
            return None, html_link

        response.encoding = 'utf-8'
        text = response.text
        self._write_cache(cache_file_name="html_{}.html", dir_prefix=cache_dir_prefix, doc_id=doc_id, text=text)
        return text, html_link

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
        status = response.status_code
        if status != 200:
            self.logger.error(f"status : {status}, response : {response.text}")
            raise Exception(f"status : {status}, response : {response.text}")
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_list(soup, dt)

    def _corp_list(self, page=1):
        headers = {
            'authority': 'kind.krx.co.kr',
            'accept': 'text/html, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9,ko;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://kind.krx.co.kr',
            'pragma': 'no-cache',
            'referer': 'https://kind.krx.co.kr/corpgeneral/corpList.do?method=loadInitPage',
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
            'method': 'searchCorpList',
            'pageIndex': page,
            'currentPageSize': '100',
            'comAbbrv': '', 'beginIndex': '',
            'orderMode': '3',
            'orderStat': 'D',
            'isurCd': '', 'repIsuSrtCd': '', 'searchCodeType': '', 'marketType': '',
            'searchType': '13',
            'industry': '',
            'fiscalYearEnd': 'all',
            'comAbbrvTmp': '',
            'location': 'all',
        }

        response = self.session.post('https://kind.krx.co.kr/corpgeneral/corpList.do', headers=headers, data=data)
        status = response.status_code
        if status != 200:
            self.logger.error(f"status : {status}, response : {response.text}")
            raise Exception(f"status : {status}, response : {response.text}")

        soup = BeautifulSoup(response.text, "html.parser")
        return parse_corp_list(soup)


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
        company_id = company_id.ljust(6, "0") if company_id is not None else None
        title = links[1].text.strip()
        link_script = links[1].get("onclick")
        doc_id = extract_kid(link_script)
        tds = tr.select("td")
        time = tds[0].text
        org = tds[3].text
        imgs = tds[1].select("img")
        remarks = [img['alt'] for img in imgs]

        if "코스닥" in remarks:
            market = "K"
        elif "유가증권" in remarks:
            market = "Y"
        elif "코넥스" in remarks:
            market = "N"
        else:
            market = "E"

        fonts = tds[2].select("font")
        etcs = [font.text for font in fonts]

        ## extract viewer ids
        ids = []
        clicks = None
        try:
            clicks = tr.select('a[onclick^=openDisclsViewer]')
            links = [click["onclick"] for click in clicks]
            for link in links:
                matches = re.finditer(r"('[\d\w.]*')", link)
                acptno, docno = [match.group(1).replace("'", "") for _, match in enumerate(matches, start=1)]
                ids.append({
                    "acptno": acptno, # 접수번호
                    "docno": docno    # 문서번호
                })
        except Exception as e:
            self.logger.error(f"failed to parse [{clicks}]")
            self.logger.error(e)

        return {
            "dt": dt,
            "time": time,
            "company": company,
            "company_id": company_id,
            "doc_id": doc_id,
            "title": title,
            "market": market,
            "org": org,
            "remarks": remarks,
            "etcs": etcs,
            "ids": ids
        }

    def _get_docurl(self, doc_id):
        url = f'https://kind.krx.co.kr/common/disclsviewer.do?method=searchContents&docNo={doc_id}'
        response = requests.get(url)
        return re.findall("(?=https)(.*?)(?=')", response.text)[-1]


