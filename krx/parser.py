import re


def parse_corp_list(soup):
    table = soup.find("table")
    tbody = table.find("tbody")
    trs = tbody.select("tr")
    items = []
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
        items.append({
            "company": company,
            "market": market,
            "code": code,
            "kind": kind,
            "major_product": major_product,
            "listing_date": listing_date,
            "finclosing_month": finclosing_month,
            "ceo": ceo,
            "location": location
        })

    paging_section = soup.select("section.paging-group")[0]
    total_count = int(paging_section.select("em")[0].text.replace(",", ""))
    section_text = paging_section.text
    total_row = list(filter(lambda x: "전체" in x.strip(), section_text.split("\n")))[0]
    current_per_total = total_row.split(":")[-1].strip()
    current_page, total_page = map(lambda x: int(x.strip()), current_per_total.split("/"))

    return {
        "total_count": total_count,
        "page": current_page,
        "total_page": total_page,
        "items": items
    }