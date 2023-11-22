"""LinkSearcher のテスト

外部リンク探索クラスをテストする
"""
import configparser
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger

from mock import MagicMock, patch

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher

logger = getLogger("PictureGathering.LinkSearch.LinkSearcher")
logger.setLevel(WARNING)


class TestLinkSearcher(unittest.TestCase):
    def test_LinkSearcher(self):
        lsc = LinkSearcher()
        self.assertEqual([], lsc.fetcher_list)

    def test_register(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "info"))
            lsc = LinkSearcher()

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
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "info"))
            lsc = LinkSearcher()

            # 正常系
            url_str = "https://www.pixiv.net/artworks/86704541"
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
                invalid_url_str = "https://invalid/artworks/86704541"
                actual = lsc.fetch(invalid_url_str)

    def test_can_fetch(self):
        lsc = LinkSearcher()

        # 正常系
        url_str = "https://www.pixiv.net/artworks/86704541"
        fake_fetcher = MagicMock()
        fake_fetcher.is_target_url = lambda url: url.non_query_url == url_str
        fake_fetcher.fetch = MagicMock()
        lsc.register(fake_fetcher)

        actual = lsc.can_fetch(url_str)
        self.assertEqual(True, actual)

        # 異常系
        invalid_url_str = "https://invalid/artworks/86704541"
        actual = lsc.can_fetch(invalid_url_str)
        self.assertEqual(False, actual)

    def test_create(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "info"))
            mock_notification = stack.enter_context(patch("PictureGathering.LinkSearch.LinkSearcher.notification.notify"))
            mock_pixiv_fetcher = stack.enter_context(patch("PictureGathering.LinkSearch.LinkSearcher.PixivFetcher"))
            mock_pixiv_novel_fetcher = stack.enter_context(patch("PictureGathering.LinkSearch.LinkSearcher.PixivNovelFetcher"))
            mock_nijie_fetcher = stack.enter_context(patch("PictureGathering.LinkSearch.LinkSearcher.NijieFetcher"))
            mock_nico_seiga_fetcher = stack.enter_context(patch("PictureGathering.LinkSearch.LinkSearcher.NicoSeigaFetcher"))

            CONFIG_FILE_NAME = "./config/config.ini"
            config = configparser.ConfigParser()
            if not config.read(CONFIG_FILE_NAME, encoding="utf8"):
                raise IOError

            lsc = LinkSearcher.create(config)

            register_num = [
                config["pixiv"].getboolean("is_pixiv_trace"),
                config["pixiv"].getboolean("is_pixiv_trace"),
                config["nijie"].getboolean("is_nijie_trace"),
                config["nico_seiga"].getboolean("is_seiga_trace"),
            ].count(True)
            self.assertEqual(register_num, len(lsc.fetcher_list))

            def make_branch(config, is_pixiv, is_pixiv_novel, is_nijie, is_seiga, error_occur):
                mock_notification.reset_mock(side_effect=True)
                mock_pixiv_fetcher.reset_mock(side_effect=True)
                mock_pixiv_novel_fetcher.reset_mock(side_effect=True)
                mock_nijie_fetcher.reset_mock(side_effect=True)
                mock_nico_seiga_fetcher.reset_mock(side_effect=True)

                config["pixiv"]["is_pixiv_trace"] = "True" if (is_pixiv or is_pixiv_novel) else "False"
                config["nijie"]["is_nijie_trace"] = "True" if is_nijie else "False"
                config["nico_seiga"]["is_seiga_trace"] = "True" if is_seiga else "False"

                if error_occur:
                    if is_pixiv:
                        mock_pixiv_fetcher.side_effect = ValueError
                    if is_pixiv_novel:
                        mock_pixiv_novel_fetcher.side_effect = ValueError
                    if is_nijie:
                        mock_nijie_fetcher.side_effect = ValueError
                    if is_seiga:
                        mock_nico_seiga_fetcher.side_effect = ValueError
                return config

            def check_branch(lsc, is_pixiv, is_pixiv_novel, is_nijie, is_seiga, error_occur):
                register_num = 0 if error_occur else [
                    is_pixiv,
                    is_pixiv_novel,
                    is_nijie,
                    is_seiga,
                ].count(True)
                self.assertEqual(register_num, len(lsc.fetcher_list))

                def check_notify_call(mock_notify, fetcher_kind):
                    mock_notify.assert_any_call(
                        title="Picture Gathering 実行エラー",
                        message=f"LinkSearcher: {fetcher_kind} register failed.",
                        app_name="Picture Gathering",
                        timeout=10
                    )

                if is_pixiv:
                    mock_pixiv_fetcher.assert_called_once()
                    if error_occur:
                        check_notify_call(mock_notification, "pixiv")
                else:
                    mock_pixiv_fetcher.assert_not_called()

                if is_pixiv_novel:
                    mock_pixiv_novel_fetcher.assert_called_once()
                    if error_occur:
                        check_notify_call(mock_notification, "pixiv novel")
                else:
                    mock_pixiv_novel_fetcher.assert_not_called()

                if is_nijie:
                    mock_nijie_fetcher.assert_called_once()
                    if error_occur:
                        check_notify_call(mock_notification, "nijie")
                else:
                    mock_nijie_fetcher.assert_not_called()

                if is_seiga:
                    mock_nico_seiga_fetcher.assert_called_once()
                    if error_occur:
                        check_notify_call(mock_notification, "niconico seiga")
                else:
                    mock_nico_seiga_fetcher.assert_not_called()
                return

            params_list = [
                (True, True, True, True, False),
                (True, True, False, False, False),
                (False, False, True, False, False),
                (False, False, False, True, False),
                (True, True, True, True, True),
                (True, True, False, False, True),
                (False, False, True, False, True),
                (False, False, False, True, True),
            ]
            for params in params_list:
                config = make_branch(
                    config,
                    params[0], params[1], params[2], params[3],
                    params[4]
                )
                actual = LinkSearcher.create(config)
                check_branch(
                    actual,
                    params[0], params[1], params[2], params[3],
                    params[4]
                )

if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
