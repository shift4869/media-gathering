# coding: utf-8
import sys
import unittest

from mock import MagicMock

from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.Skeb.SkebSession import SkebSession
from PictureGathering.LinkSearch.Skeb.SkebSourceInfo import SkebSourceInfo
from PictureGathering.LinkSearch.Skeb.SkebSourceList import SkebSourceList
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL


class TestSkebSourceList(unittest.TestCase):
    def test_SkebSourceList(self):
        url = URL("https://skeb.jp/source_link/dummy01?query=1")
        ext = Extension.WEBP
        source_info = SkebSourceInfo(url, ext)
        source_list = SkebSourceList([source_info])

        expect = [source_info]
        self.assertEqual(expect, source_list._list)
        self.assertTrue(hasattr(source_list, "__iter__"))
        self.assertTrue(hasattr(source_list, "__len__"))
        self.assertEqual(len(expect), len(source_list))
        self.assertTrue(hasattr(source_list, "__getitem__"))
        self.assertEqual(expect.__getitem__(0), source_list.__getitem__(0))

        source_list = SkebSourceList([])
        self.assertEqual([], source_list._list)

        with self.assertRaises(ValueError):
            source_list = SkebSourceList(["invalid_arg"])
        with self.assertRaises(TypeError):
            source_list = SkebSourceList("invalid_arg")

    def test_create(self):
        skeb_url = SkebURL.create("https://skeb.jp/@author1/works/1")
        session = MagicMock(spec=SkebSession)

        def find_tag(match_key: str, key: str, src_url: str) -> MagicMock:
            r = MagicMock()
            if match_key != key:
                return []
            match match_key:
                case "img":
                    img_tag = MagicMock()
                    img_tag.attrs = {
                        "src": src_url
                    }
                    r = [img_tag]
                case "video":
                    src_tags = MagicMock()
                    src_tags.attrs = {
                        "preload": "auto",
                        "autoplay": "autoplay",
                        "muted": "muted",
                        "loop": "loop",
                        "src": src_url,
                    }
                    r = [src_tags]
                case "source":
                    src_tags = MagicMock()
                    src_tags.attrs = {
                        "type": "video/mp4",
                        "src": src_url,
                    }
                    r = [src_tags]
                case ".p":
                    src_tags = MagicMock()
                    src_tags.full_text = "dummy_full_text"
                    r = [src_tags]
            return r

        def make_mock_session(match_key: str) -> MagicMock:
            mock_session = MagicMock()

            def return_session(request_url_str: str) -> MagicMock:
                request_skeb_url = SkebURL.create(request_url_str)
                author_name = request_skeb_url.author_name.name
                work_id = request_skeb_url.work_id.id
                base_url = "https://si.imgix.net/direct_link/"
                src_url = f"{base_url}{author_name}/works/{work_id:003}"
                r_session = MagicMock()

                def return_find(key: str) -> MagicMock:
                    r_find = find_tag(match_key, key, src_url)
                    return r_find
                r_session.html.find.side_effect = return_find
                return r_session
            mock_session.get.side_effect = return_session
            return mock_session
        # イラスト
        session = make_mock_session("img")
        actual = SkebSourceList.create(skeb_url, session)
        url = URL("https://si.imgix.net/direct_link/author1/works/001?query=1")
        ext = Extension.WEBP
        source_info = SkebSourceInfo(url, ext)
        expect = [source_info]
        self.assertEqual(expect, actual._list)

        # gif
        session = make_mock_session("video")
        actual = SkebSourceList.create(skeb_url, session)
        url = URL("https://si.imgix.net/direct_link/author1/works/001?query=1")
        ext = Extension.MP4
        source_info = SkebSourceInfo(url, ext)
        expect = [source_info]
        self.assertEqual(expect, actual._list)

        # 動画
        session = make_mock_session("source")
        actual = SkebSourceList.create(skeb_url, session)
        url = URL("https://si.imgix.net/direct_link/author1/works/001?query=1")
        ext = Extension.MP4
        source_info = SkebSourceInfo(url, ext)
        expect = [source_info]
        self.assertEqual(expect, actual._list)

        # 小説
        session = make_mock_session(".p")
        actual = SkebSourceList.create(skeb_url, session)
        has_text_url = URL(skeb_url.non_query_url + "?p=dummy_full_text")
        ext = Extension.TXT
        source_info = SkebSourceInfo(has_text_url, ext)
        expect = [source_info]
        self.assertEqual(expect, actual._list)

        # 解析失敗
        with self.assertRaises(ValueError):
            session = make_mock_session("invalid_tag")
            actual = SkebSourceList.create(skeb_url, session)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
