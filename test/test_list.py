import logging

from cache import MemoryCache

from krx import KrxKindWeb

def test_list():
    web = KrxKindWeb(cache=MemoryCache())

    items = web.fetch_list("2023-01-03", time_sleep=0.5)

    print(items)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s [%(levelname)s] %(message)s')
    logger = logging.getLogger("krx_api")
    logger.setLevel(logging.DEBUG)
    test_list()