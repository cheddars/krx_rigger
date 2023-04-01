
python : 3.6+

# Usage

Fetch KRX List

```python
from krx import KrxKindWeb
krxweb = KrxKindWeb()

r = krxweb.fetch_list('2021-03-31', time_sleep=0.1)

print(r)
```
Output
```python
[{'dt': '2023-03-31',
  'time': '20:17',
  'company': '엘아이에스',
  'company_id': '13869',
  'doc_id': '20230331003752',
  'title': '주권매매거래정지기간변경(상장폐지 사유 발생)',
  'org': '코스닥시장본부'},
 {'dt': '2023-03-31',
  'time': '20:16',
  'company': '엘아이에스',
  'company_id': '13869',
  'doc_id': '20230331003755',
  'title': '기타시장안내(상장폐지 관련)',
  'org': '코스닥시장본부'},
...
]
```