"""RTクローラーのテスト

RetweetCrawler.RetweetCrawler()の各種機能をテストする
"""

import configparser
import random
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import getLogger
from pathlib import Path

from freezegun import freeze_time
from mock import MagicMock, patch

from PictureGathering.RetweetCrawler import RetweetCrawler


class TestRetweetCrawler(unittest.TestCase):
    """RetweetCrawlerテストメインクラス
    """

    def setUp(self):
        pass

    def _get_instance(self) -> RetweetCrawler:
        with ExitStack() as stack:
            mock_logger_rc = stack.enter_context(patch.object(getLogger("PictureGathering.RetweetCrawler"), "info"))
            mock_logger_cr = stack.enter_context(patch.object(getLogger("PictureGathering.Crawler"), "info"))
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_rt_db_controller = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetDBController"))
            rc = RetweetCrawler()
            rc.lsb = MagicMock()
            return rc

    def test_RetweetCrawlerInit(self):
        """RetweetCrawlerの初期状態のテスト
        
        Note:
            RetweetCrawler()内で初期化されたconfigと、configparser.ConfigParser()で取得したconfigを比較する
            どちらのconfigも設定元は"./config/config.ini"である
            RetweetCrawlerで利用する設定値のみテストする（基底クラスのテストは別ファイル）
        """
        rc = self._get_instance()

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
        expect = Path(expect_config["save_directory"]["save_retweet_path"])
        actual = rc.save_path
        self.assertEqual(expect, actual)

        self.assertEqual("RT", rc.type)

    def test_make_done_message(self):
        """終了メッセージ作成機能をチェックする
        """
        with ExitStack() as stack:
            mock_freeze_gun = stack.enter_context(freeze_time("2022-10-22 10:30:20"))

            rc = self._get_instance()

            s_add_url_list = ["http://pbs.twimg.com/media/add_sample{0}.jpg:orig".format(i) for i in range(5)]
            s_del_url_list = ["http://pbs.twimg.com/media/del_sample{0}.jpg:orig".format(i) for i in range(5)]
            s_pickup_url_list = random.sample(s_add_url_list, min(4, len(s_add_url_list)))
            mock_random = stack.enter_context(patch("PictureGathering.RetweetCrawler.random.sample"))
            mock_random.return_value = s_pickup_url_list

            s_now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            s_done_msg = "Retweet PictureGathering run.\n"
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

            rc.add_url_list = s_add_url_list
            rc.add_cnt = len(s_add_url_list)
            rc.del_url_list = s_del_url_list
            rc.del_cnt = len(s_del_url_list)
            actual = rc.make_done_message()

            self.assertEqual(expect, actual)

    def test_crawl(self):
        """全体クロールの呼び出しをチェックする
        """
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch("PictureGathering.RetweetCrawler.logger.info"))
            mock_tac_like_fetcher = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetFetcher"))
            mock_interpret_tweets = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetCrawler.interpret_tweets"))
            mock_trace_external_link = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetCrawler.trace_external_link"))
            mock_shrink_folder = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetCrawler.shrink_folder"))
            mock_end_of_process = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetCrawler.end_of_process"))

            rc = self._get_instance()

            # No API use mode
            mock_rt_instance = MagicMock()
            mock_rt_instance.fetch.side_effect = lambda: ["fetched_tweets"]
            mock_rt_instance.to_convert_TweetInfo.side_effect = lambda ft: ["to_convert_TweetInfo"]
            mock_rt_instance.to_convert_ExternalLink.side_effect = lambda ft, lsb: ["to_convert_ExternalLink"]

            mock_tac_like_fetcher.side_effect = lambda ct0, auth_token, target_screen_name, target_id: mock_rt_instance

            rc.config["twitter_api_client"]["ct0"] = "dummy_ct0"
            rc.config["twitter_api_client"]["auth_token"] = "dummy_auth_token"
            rc.config["twitter_api_client"]["target_screen_name"] = "dummy_target_screen_name"
            rc.config["twitter_api_client"]["target_id"] = "99999999"  # dummy_target_id

            res = rc.crawl()

            mock_tac_like_fetcher.assert_called_once_with("dummy_ct0", "dummy_auth_token", "dummy_target_screen_name", 99999999)
            mock_rt_instance.fetch.assert_called_once_with()

            mock_rt_instance.to_convert_TweetInfo.assert_called_once_with(["fetched_tweets"])
            mock_interpret_tweets.assert_called_once_with(["to_convert_TweetInfo"])

            mock_rt_instance.to_convert_ExternalLink.assert_called_once_with(["fetched_tweets"], rc.lsb)
            mock_trace_external_link.assert_called_once_with(["to_convert_ExternalLink"])

            mock_shrink_folder.assert_called_once_with(int(rc.config["holding"]["holding_file_num"]))
            mock_end_of_process.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
