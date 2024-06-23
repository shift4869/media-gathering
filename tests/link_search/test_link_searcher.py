import sys
import unittest
from collections import namedtuple
from pathlib import Path

import orjson
from mock import MagicMock, patch

from media_gathering.link_search.link_searcher import LinkSearcher


class TestLinkSearcher(unittest.TestCase):
    def _get_instance(self) -> LinkSearcher:
        mock_logger = self.enterContext(patch("media_gathering.link_search.link_searcher.logger"))
        return LinkSearcher()

    def test_init(self):
        lsc = LinkSearcher()
        self.assertEqual([], lsc.fetcher_list)

    def test_register(self):
        lsc = self._get_instance()

        # 正常系
        fake_fetcher = MagicMock()
        fake_fetcher.is_target_url = MagicMock()
        fake_fetcher.fetch = MagicMock()
        lsc.register(fake_fetcher)
        self.assertEqual(1, len(lsc.fetcher_list))
        self.assertEqual(fake_fetcher, lsc.fetcher_list[0])

        # 異常系
        fake_fetcher = MagicMock()
        del fake_fetcher.is_target_url
        del fake_fetcher.fetch
        with self.assertRaises(TypeError):
            lsc.register(fake_fetcher)

    def test_fetch(self):
        lsc = self._get_instance()

        # 正常系
        url_str = "https://www.pixiv.net/artworks/xxxxxxxx"
        fake_fetcher = MagicMock()
        fake_fetcher.is_target_url = lambda url: url.non_query_url == url_str
        fake_fetcher.fetch = MagicMock()
        lsc.register(fake_fetcher)

        actual = lsc.fetch(url_str)
        self.assertEqual(None, actual)
        fake_fetcher.fetch.assert_called_once_with(url_str)
        fake_fetcher.fetch.reset_mock()

        # 異常系
        with self.assertRaises(ValueError):
            invalid_url_str = "https://invalid/artworks/xxxxxxxx"
            actual = lsc.fetch(invalid_url_str)

    def test_can_fetch(self):
        lsc = self._get_instance()

        # 正常系
        url_str = "https://www.pixiv.net/artworks/xxxxxxxx"
        fake_fetcher = MagicMock()
        fake_fetcher.is_target_url = lambda url: url.non_query_url == url_str
        fake_fetcher.fetch = MagicMock()
        lsc.register(fake_fetcher)

        actual = lsc.can_fetch(url_str)
        self.assertEqual(True, actual)

        # 異常系
        invalid_url_str = "https://invalid/artworks/xxxxxxxx"
        actual = lsc.can_fetch(invalid_url_str)
        self.assertEqual(False, actual)

    def test_create(self):
        mock_logger = self.enterContext(patch("media_gathering.link_search.link_searcher.logger"))
        mock_notification = self.enterContext(patch("media_gathering.link_search.link_searcher.notification"))
        mock_pixiv_fetcher = self.enterContext(patch("media_gathering.link_search.link_searcher.PixivFetcher"))
        mock_pixiv_novel_fetcher = self.enterContext(
            patch("media_gathering.link_search.link_searcher.PixivNovelFetcher")
        )
        mock_nijie_fetcher = self.enterContext(patch("media_gathering.link_search.link_searcher.NijieFetcher"))
        mock_nico_seiga_fetcher = self.enterContext(
            patch("media_gathering.link_search.link_searcher.NicoSeigaFetcher")
        )

        CONFIG_FILE_NAME = "./config/config_sample.json"
        config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())
        Params = namedtuple("Params", ["is_pixiv", "is_pixiv_novel", "is_nijie", "is_seiga", "error_occur", "msg"])

        def pre_run(config: dict, params: Params) -> dict:
            mock_notification.reset_mock(side_effect=True)
            mock_pixiv_fetcher.reset_mock(side_effect=True)
            mock_pixiv_novel_fetcher.reset_mock(side_effect=True)
            mock_nijie_fetcher.reset_mock(side_effect=True)
            mock_nico_seiga_fetcher.reset_mock(side_effect=True)

            config["pixiv"]["is_pixiv_trace"] = params.is_pixiv or params.is_pixiv_novel
            config["nijie"]["is_nijie_trace"] = params.is_nijie
            config["nico_seiga"]["is_seiga_trace"] = params.is_seiga

            if params.error_occur:
                if params.is_pixiv:
                    mock_pixiv_fetcher.side_effect = ValueError
                if params.is_pixiv_novel:
                    mock_pixiv_novel_fetcher.side_effect = ValueError
                if params.is_nijie:
                    mock_nijie_fetcher.side_effect = ValueError
                if params.is_seiga:
                    mock_nico_seiga_fetcher.side_effect = ValueError
            return config

        def post_run(lsc: LinkSearcher, params: Params) -> None:
            self.assertIsInstance(lsc, LinkSearcher)
            register_num = (
                0
                if params.error_occur
                else [
                    params.is_pixiv or params.is_pixiv_novel,
                    params.is_pixiv or params.is_pixiv_novel,
                    params.is_nijie,
                    params.is_seiga,
                ].count(True)
            )
            self.assertEqual(register_num, len(lsc.fetcher_list))

            def check_notify_call(fetcher_kind):
                mock_notification.notify.assert_any_call(
                    title="Media Gathering 実行エラー",
                    message=f"LinkSearcher: {fetcher_kind} register failed.",
                    app_name="Media Gathering",
                    timeout=10,
                )

            if params.is_pixiv:
                mock_pixiv_fetcher.assert_called_once()
                if params.error_occur:
                    check_notify_call("pixiv")
            else:
                mock_pixiv_fetcher.assert_not_called()

            if params.is_pixiv_novel:
                mock_pixiv_novel_fetcher.assert_called_once()
                if params.error_occur:
                    check_notify_call("pixiv novel")
            else:
                mock_pixiv_novel_fetcher.assert_not_called()

            if params.is_nijie:
                mock_nijie_fetcher.assert_called_once()
                if params.error_occur:
                    check_notify_call("nijie")
            else:
                mock_nijie_fetcher.assert_not_called()

            if params.is_seiga:
                mock_nico_seiga_fetcher.assert_called_once()
                if params.error_occur:
                    check_notify_call("niconico seiga")
            else:
                mock_nico_seiga_fetcher.assert_not_called()

        params_list = [
            Params(True, True, True, True, False, "all true case"),
            Params(True, True, False, False, False, "pixiv, pixiv novel only"),
            Params(False, False, True, False, False, "nijie only"),
            Params(False, False, False, True, False, "seiga only"),
            Params(True, True, True, True, True, "all error case"),
            Params(True, True, False, False, True, "pixiv, pixiv novel error"),
            Params(False, False, True, False, True, "nijie only error"),
            Params(False, False, False, True, True, "seiga only error"),
        ]
        for params in params_list:
            with self.subTest(params.msg):
                config = pre_run(config, params)
                actual = LinkSearcher.create(config)
                post_run(actual, params)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
