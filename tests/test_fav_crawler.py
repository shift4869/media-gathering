import sys
import unittest
from datetime import datetime
from pathlib import Path

import orjson
from freezegun import freeze_time
from mock import MagicMock, patch

from media_gathering.fav_crawler import FavCrawler
from media_gathering.util import Result


class TestFavCrawler(unittest.TestCase):
    def _get_instance(self) -> FavCrawler:
        mock_logger_fav_crawler = self.enterContext(patch("media_gathering.fav_crawler.logger"))
        mock_logger_crawler = self.enterContext(patch("media_gathering.crawler.logger"))
        mock_validate_config_file = self.enterContext(patch("media_gathering.crawler.Crawler.validate_config_file"))
        mock_lsr = self.enterContext(patch("media_gathering.crawler.Crawler.link_search_register"))
        mock_fav_db_controller = self.enterContext(patch("media_gathering.fav_crawler.FavDBController"))
        FavCrawler.CONFIG_FILE_NAME = "./config/config_sample.json"
        instance = FavCrawler()
        instance.lsb = MagicMock()
        return instance

    def test_init(self):
        mock_logger_fav_crawler = self.enterContext(patch("media_gathering.fav_crawler.logger"))
        mock_logger_crawler = self.enterContext(patch("media_gathering.crawler.logger"))
        mock_validate_config_file = self.enterContext(patch("media_gathering.crawler.Crawler.validate_config_file"))
        mock_lsr = self.enterContext(patch("media_gathering.crawler.Crawler.link_search_register"))
        mock_fav_db_controller = self.enterContext(patch("media_gathering.fav_crawler.FavDBController"))

        FavCrawler.CONFIG_FILE_NAME = "./config/config_sample.json"
        instance = FavCrawler()

        CONFIG_FILE_NAME = "./config/config_sample.json"
        expect_config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())

        config = expect_config["db"]
        save_path = Path(config["save_path"])
        self.assertTrue(save_path.is_dir())
        db_fullpath = save_path / config["save_file_name"]
        mock_fav_db_controller.assert_called_once_with(db_fullpath)
        self.assertEqual(mock_fav_db_controller.return_value, instance.db_cont)

        config = expect_config["save_permanent"]
        if config["save_permanent_media_flag"]:
            self.assertTrue(Path(config["save_permanent_media_path"]).is_dir())

        self.assertEqual(Path(expect_config["save_directory"]["save_fav_path"]), instance.save_path)
        self.assertEqual("Fav", instance.type)

        mock_fav_db_controller.side_effect = KeyError
        with self.assertRaises(KeyError):
            instance = FavCrawler()

    def test_make_done_message(self):
        mock_freeze_gun = self.enterContext(freeze_time("2022-10-22 10:30:20"))
        mock_random = self.enterContext(patch("media_gathering.fav_crawler.random.sample"))

        instance = self._get_instance()

        add_url_list = [f"http://pbs.twimg.com/media/add_sample{i}.jpg:orig" for i in range(5)]
        del_url_list = [f"http://pbs.twimg.com/media/del_sample{i}.jpg:orig" for i in range(5)]
        pickup_url_list = add_url_list[1:5]
        mock_random.return_value = pickup_url_list

        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Fav MediaGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += f"add {len(add_url_list)} new images. "
        done_msg += f"delete {len(del_url_list)} old images."
        done_msg += "\n"

        for pickup_url in pickup_url_list:
            pickup_url = str(pickup_url).replace(":orig", "")
            done_msg += pickup_url + "\n"
        expect = done_msg

        instance.add_url_list = add_url_list
        instance.add_cnt = len(add_url_list)
        instance.del_url_list = del_url_list
        instance.del_cnt = len(del_url_list)
        actual = instance.make_done_message()

        self.assertEqual(expect, actual)

    def test_crawl(self):
        mock_tac_like_fetcher = self.enterContext(patch("media_gathering.fav_crawler.LikeFetcher"))
        mock_parser = self.enterContext(patch("media_gathering.fav_crawler.LikeParser"))
        mock_interpret_tweets = self.enterContext(patch("media_gathering.fav_crawler.FavCrawler.interpret_tweets"))
        mock_trace_external_link = self.enterContext(
            patch("media_gathering.fav_crawler.FavCrawler.trace_external_link")
        )
        mock_shrink_folder = self.enterContext(patch("media_gathering.fav_crawler.FavCrawler.shrink_folder"))
        mock_end_of_process = self.enterContext(patch("media_gathering.fav_crawler.FavCrawler.end_of_process"))

        instance = self._get_instance()

        mock_fav_instance = MagicMock()
        mock_fav_instance.fetch.side_effect = lambda limit: ["fetched_tweets"]
        mock_tac_like_fetcher.side_effect = lambda ct0, auth_token, target_screen_name, target_id: mock_fav_instance

        mock_parser().parse_to_TweetInfo.side_effect = lambda: ["to_convert_TweetInfo"]
        mock_parser().parse_to_ExternalLink.side_effect = lambda: ["to_convert_ExternalLink"]

        instance.config["twitter_api_client"]["ct0"] = "dummy_ct0"
        instance.config["twitter_api_client"]["auth_token"] = "dummy_auth_token"
        instance.config["twitter_api_client"]["target_screen_name"] = "dummy_target_screen_name"
        instance.config["twitter_api_client"]["target_id"] = 99999999
        instance.config["tweet_timeline"]["likes_get_max_count"] = 400

        res = instance.crawl()
        self.assertEqual(Result.success, res)

        mock_tac_like_fetcher.assert_called_once_with(
            "dummy_ct0", "dummy_auth_token", "dummy_target_screen_name", 99999999
        )
        mock_fav_instance.fetch.assert_called_once_with(400)

        mock_parser.assert_any_call(["fetched_tweets"], instance.lsb)
        mock_parser().parse_to_TweetInfo.assert_called_once_with()
        mock_interpret_tweets.assert_called_once_with(["to_convert_TweetInfo"])

        mock_parser().parse_to_ExternalLink.assert_called_once_with()
        mock_trace_external_link.assert_called_once_with(["to_convert_ExternalLink"])

        mock_shrink_folder.assert_called_once_with(int(instance.config["holding"]["holding_file_num"]))
        mock_end_of_process.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
