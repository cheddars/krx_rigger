import re

import unittest

import logging

from cache import MemoryCache

from krx import KrxKindWeb, parse_corp_list

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s [%(levelname)s] %(message)s')
logger = logging.getLogger("krx_api")
logger.setLevel(logging.DEBUG)

class TestKrxKindWeb(unittest.TestCase):
    def test_list(self):
        web = KrxKindWeb(cache=MemoryCache())

        items = web.fetch_list("2023-01-03", time_sleep=0.5)

        print(items)

    def test_document_link(self):
        web = KrxKindWeb(cache=MemoryCache())
        links = web.get_document_link("20230310000434")
        print(links)

    def test_corp_list(self):
        web = KrxKindWeb(cache=MemoryCache())
        soup = web._corp_list()

        table = soup.find("table")
        tbody = table.find("tbody")
        trs = tbody.select("tr")
        for tr in trs:
            tds = tr.select("td")
            company = tds[0].text.strip()
            market = tds[0].find("img")["alt"]
            onclick = tds[0].find("a")["onclick"]

            match = re.search(r"\('(\d+)'\)", onclick)
            code = match.group(1) if match else None
            kind = tds[1].text.strip()
            major_product = tds[2].text.strip()
            listing_date = tds[3].text.strip()
            finclosing_month = tds[4].text.strip()
            ceo = tds[5].text.strip()
            location = tds[7].text.strip()
            print(f"company : {company}, market : {market}, code : {code}, kind : {kind}, major_product : {major_product}, "
                  f"listing_date : {listing_date}, finclosing_month : {finclosing_month}, ceo : {ceo}, location : {location}")

        paging_section = soup.select("section.paging-group")[0]
        total_count = int(paging_section.select("em")[0].text.replace(",", ""))
        section_text = paging_section.text
        total_row = list(filter(lambda x: "전체" in x.strip(), section_text.split("\n")))[0]
        current_per_total = total_row.split(":")[-1].strip()
        current_page, total_page = map(lambda x: int(x.strip()), current_per_total.split("/"))
        print(f"total : {total_count}, pages : {current_page}/{total_page}")


    def test_corp_list_all(self):
        web = KrxKindWeb(cache=MemoryCache())
        all_corps = web.corp_list()

        for corp in all_corps:
            print(corp)