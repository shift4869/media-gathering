"""FetcherBase のテスト

外部リンク探索の基底クラスをテストする
"""
import re
import sys
import unittest

from media_gathering.link_search.fetcher_base import FetcherBase
from media_gathering.link_search.url import URL


class ConcreteFetcher(FetcherBase):
    """具体的な担当者
    """
    def __init__(self):
        super().__init__()

    def is_target_url(self, url: URL) -> bool:
        pattern = r"^https://www.anyurl/sample/index.html$"
        is_target = re.search(pattern, url.original_url) is not None
        return is_target

    def fetch(self, url: URL) -> None:
        pass


class TestFetcherBase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_LinkSearcher(self):
        fetcher = ConcreteFetcher()

        # 正常系
        url_str = "https://www.anyurl/sample/index.html"
        actual = fetcher.is_target_url(URL(url_str))
        self.assertEqual(True, actual)
        actual = fetcher.fetch(URL(url_str))
        self.assertEqual(None, actual)

        # 異常系
        url_str = "https://invalid/sample/index.html"
        actual = fetcher.is_target_url(URL(url_str))
        self.assertEqual(False, actual)
        actual = fetcher.fetch(URL(url_str))
        self.assertEqual(None, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
