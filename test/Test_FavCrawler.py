# coding: utf-8
"""Favクローラーのテスト

FavCrawler.FavCrawler()の各種機能をテストする
"""

import configparser
import random
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger
from pathlib import Path

from freezegun import freeze_time
from mock import MagicMock, patch

from PictureGathering.FavCrawler import FavCrawler

logger = getLogger("PictureGathering.FavCrawler")
logger.setLevel(WARNING)


class TestFavCrawler(unittest.TestCase):
    """FavCrawlerテストメインクラス
    """

    def setUp(self):
        pass

    def _get_instance(self) -> FavCrawler:
        with ExitStack() as stack:
            mock_logger_fc = stack.enter_context(patch.object(getLogger("PictureGathering.FavCrawler"), "info"))
            mock_logger_cr = stack.enter_context(patch.object(getLogger("PictureGathering.Crawler"), "info"))
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_fav_db_controller = stack.enter_context(patch("PictureGathering.FavCrawler.FavDBController"))
            fc = FavCrawler()
            fc.lsb = MagicMock()
            return fc

    def test_FavCrawlerInit(self):
        """FavCrawlerの初期状態のテスト
        
        Note:
            FavCrawler()内で初期化されたconfigと、configparser.ConfigParser()で取得したconfigを比較する
            どちらのconfigも設定元は"./config/config.ini"である
            FavCrawlerで利用する設定値のみテストする（基底クラスのテストは別ファイル）
        """
        fc = self._get_instance()

        # expect_config読み込みテスト
        CONFIG_FILE_NAME = "./config/config.ini"
        expect_config = configparser.ConfigParser()
        self.assertTrue(Path(CONFIG_FILE_NAME).is_file())
        self.assertFalse(expect_config.read("ERROR_PATH" + CONFIG_FILE_NAME, encoding="utf8"))
        expect_config.read(CONFIG_FILE_NAME, encoding="utf8")

        # 存在しないキーを指定するテスト
        with self.assertRaises(KeyError):
            print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

        # 設定値比較
        expect = Path(expect_config["save_directory"]["save_fav_path"])
        actual = fc.save_path
        self.assertEqual(expect, actual)

        self.assertEqual("Fav", fc.type)

    def test_make_done_message(self):
        """終了メッセージ作成機能をチェックする
        """
        with ExitStack() as stack:
            mock_freeze_gun = stack.enter_context(freeze_time("2022-10-22 10:30:20"))

            fc = self._get_instance()

            s_add_url_list = ["http://pbs.twimg.com/media/add_sample{0}.jpg:orig".format(i) for i in range(5)]
            s_del_url_list = ["http://pbs.twimg.com/media/del_sample{0}.jpg:orig".format(i) for i in range(5)]
            s_pickup_url_list = random.sample(s_add_url_list, min(4, len(s_add_url_list)))
            mock_random = stack.enter_context(patch("PictureGathering.FavCrawler.random.sample"))
            mock_random.return_value = s_pickup_url_list

            s_now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            s_done_msg = "Fav PictureGathering run.\n"
            s_done_msg += s_now_str
            s_done_msg += " Process Done !!\n"
            s_done_msg += "add {0} new images. ".format(len(s_add_url_list))
            s_done_msg += "delete {0} old images.".format(len(s_del_url_list))
            s_done_msg += "\n"

            random_pickup = True
            if random_pickup:
                # pickup_url_list = random.sample(self.add_url_list, min(4, len(self.add_url_list)))
                for pickup_url in s_pickup_url_list:
                    pickup_url = str(pickup_url).replace(":orig", "")
                    s_done_msg += pickup_url + "\n"
            expect = s_done_msg

            fc.add_url_list = s_add_url_list
            fc.add_cnt = len(s_add_url_list)
            fc.del_url_list = s_del_url_list
            fc.del_cnt = len(s_del_url_list)
            actual = fc.make_done_message()

            self.assertEqual(expect, actual)

    def test_crawl(self):
        """全体クロールの呼び出しをチェックする
        """
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "info"))
            mock_noapi_like_fetcher = stack.enter_context(patch("PictureGathering.FavCrawler.NoAPILikeFetcher"))
            mock_interpret_tweets = stack.enter_context(patch("PictureGathering.FavCrawler.FavCrawler.interpret_tweets_v2"))
            mock_trace_external_link = stack.enter_context(patch("PictureGathering.FavCrawler.FavCrawler.trace_external_link"))
            mock_shrink_folder = stack.enter_context(patch("PictureGathering.FavCrawler.FavCrawler.shrink_folder"))
            mock_end_of_process = stack.enter_context(patch("PictureGathering.FavCrawler.FavCrawler.end_of_process"))

            fc = self._get_instance()

            # No API use mode
            mock_like_instance = MagicMock()
            mock_like_instance.fetch.side_effect = lambda: ["fetched_tweets"]
            mock_like_instance.to_convert_TweetInfo.side_effect = lambda ft: ["to_convert_TweetInfo"]
            mock_like_instance.to_convert_ExternalLink.side_effect = lambda ft, lsb: ["to_convert_ExternalLink"]

            mock_noapi_like_fetcher.side_effect = lambda username, password, target_username: mock_like_instance

            fc.config["twitter_noapi"]["username"] = "dummy_username"
            fc.config["twitter_noapi"]["password"] = "dummy_password"
            fc.config["twitter_noapi"]["target_username"] = "dummy_target_username"

            res = fc.crawl()

            mock_noapi_like_fetcher.assert_called_once_with("dummy_username", "dummy_password", "dummy_target_username")
            mock_like_instance.fetch.assert_called_once_with()

            mock_like_instance.to_convert_TweetInfo.assert_called_once_with(["fetched_tweets"])
            mock_interpret_tweets.assert_called_once_with(["to_convert_TweetInfo"])

            mock_like_instance.to_convert_ExternalLink.assert_called_once_with(["fetched_tweets"], fc.lsb)
            mock_trace_external_link.assert_called_once_with(["to_convert_ExternalLink"])

            mock_shrink_folder.assert_called_once_with(int(fc.config["holding"]["holding_file_num"]))
            mock_end_of_process.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
