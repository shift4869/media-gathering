# coding: utf-8
"""NicoSeigaSaveDirectoryPath のテスト

NicoSeigaSaveDirectoryPathを表すクラスをテストする
"""
from pathlib import Path
import sys
import urllib.parse
import unittest

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSaveDirectoryPath import NicoSeigaSaveDirectoryPath


class TestNicoSeigaSaveDirectoryPath(unittest.TestCase):
    def test_NicoSeigaSaveDirectoryPath(self):
        return
        # 正常系
        # クエリなし
        url_str = "https://seiga.nicovideo.jp/seiga/im12345678"
        url = NicoSeigaSaveDirectoryPath.create(url_str)
        self.assertEqual(url_str, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # クエリなし
        url_str = "http://nico.ms/im12345678"
        url = NicoSeigaSaveDirectoryPath.create(url_str)
        self.assertEqual(url_str, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # クエリ付き
        url_str = "https://seiga.nicovideo.jp/seiga/im12345678?some_query=1"
        non_query_url = urllib.parse.urlunparse(
            urllib.parse.urlparse(str(url_str))._replace(query=None, fragment=None)
        )
        url = NicoSeigaSaveDirectoryPath.create(url_str)
        self.assertEqual(non_query_url, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # 異常系
        # NicoSeigaSaveDirectoryPathアドレスでない
        with self.assertRaises(ValueError):
            url_str = "https://www.google.co.jp/"
            url = NicoSeigaSaveDirectoryPath.create(url_str)

    def test_is_valid(self):
        illust_id = Illustid(12345678)
        illust_name = Illustname("作品名1")
        author_id = Authorid(1234567)
        author_name = Authorname("作者名1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        base_path = Path("./test/LinkSearch/NicoSeiga")
        save_directory_path = NicoSeigaSaveDirectoryPath.create(illust_info, base_path)
        self.assertEqual(True, save_directory_path._is_valid())

        save_directory_path = NicoSeigaSaveDirectoryPath(base_path)
        self.assertEqual(True, save_directory_path._is_valid())

        with self.assertRaises(TypeError):
            save_directory_path = NicoSeigaSaveDirectoryPath("invalid argument")
            self.assertEqual(True, save_directory_path._is_valid())


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
