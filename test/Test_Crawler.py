"""クローラーのテスト

Crawler.Crawler()の各種機能をテストする
実際に使用する派生クラスのテストについてはそれぞれのファイルに記述する
設定ファイルとして {CONFIG_FILE_NAME} にあるconfig.iniファイルを使用する
各種トークン類もAPI利用のテストのために使用する
"""

import configparser
import os
import random
import sys
import time
import unittest
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path
from unittest.mock import call

from mock import MagicMock, PropertyMock, patch

from PictureGathering.Crawler import Crawler, MediaSaveResult
from PictureGathering.Model import ExternalLink
from PictureGathering.tac.TweetInfo import TweetInfo
from PictureGathering.Util import Result

logger = getLogger("PictureGathering.Crawler")
logger.setLevel(WARNING)


class ConcreteCrawler(Crawler):
    """テスト用の具体化クローラー

    Crawler.Crawler()の抽象クラスメソッドを最低限実装したテスト用の派生クラス

    Attributes:
        db_cont (MagicMock): DB操作用コントローラー（モック）
        save_path (Path): 画像保存先パス
        type (str): 継承先を表すタイプ識別子
    """
    def __init__(self, error_occur=""):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_logger_exception = stack.enter_context(patch.object(logger, "exception"))

            # Crawler.__init__()で意図的にエラーを起こすための設定
            if error_occur == "IOError":
                # configファイルのパスエラーは変数置き換えで自動的に処理される
                self.CONFIG_FILE_NAME = "error_file_path"
            elif error_occur == "KeyError":
                # link_search_register呼び出しを利用して例外を送出するモックを設定する
                mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
                mock_lsr.side_effect = KeyError()
            elif error_occur == "ValueError":
                # link_search_register呼び出しを利用して例外を送出するモックを設定する
                mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
                mock_lsr.side_effect = ValueError("ValueError")
            elif error_occur == "Exception":
                # link_search_register呼び出しを利用して例外を送出するモックを設定する
                mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
                mock_lsr.side_effect = Exception()

            super().__init__()

            self.db_cont = MagicMock()
            self.save_path = Path("./test")
            self.type = "Test Crawler"

    def make_done_message(self):
        return "Test Crawler : done"

    def crawl(self):
        return 0


class TestCrawler(unittest.TestCase):
    """テストメインクラス
    """
    def _make_tweet_info(self, i: int) -> TweetInfo:
        arg_dict = {
            "media_filename": f"sample_photo_{i:02}.mp4",
            "media_url": f"sample_photo_{i:02}_media_url",
            "media_thumbnail_url": f"sample_photo_{i:02}_media_thumbnail_url",
            "tweet_id": f"{i:05}",
            "tweet_url": f"{i:05}_tweet_url",
            "created_at": f"2022-10-21 10:00:{i:02}",
            "user_id": f"{i//2:03}",
            "user_name": f"user_{i:02}",
            "screan_name": f"user_{i:02}_screan_name",
            "tweet_text": f"tweet_text_{i:02}",
            "tweet_via": "sample via",
        }
        return TweetInfo.create(arg_dict)

    def _make_external_link(self, i: int) -> ExternalLink:
        arg_dict = {
            "external_link_url": f"external_link_{i:02}_url",
            "tweet_id": f"{i:05}",
            "tweet_url": f"{i:05}_tweet_url",
            "created_at": f"2022-10-21 10:11:{i:02}",
            "user_id": f"{i//2:03}",
            "user_name": f"user_{i:02}",
            "screan_name": f"user_{i:02}_screan_name",
            "tweet_text": f"tweet_text_{i:02}",
            "tweet_via": "sample via",
            "saved_created_at": f"2022-10-21 10:22:{i:02}",
            "link_type": f"pixiv",
        }
        return ExternalLink.create(arg_dict)

    def test_ConcreteCrawler(self):
        """ConcreteCrawlerのテスト
        """
        with ExitStack() as stack:
            mock_notification = stack.enter_context(patch("PictureGathering.Crawler.notification"))
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            crawler = ConcreteCrawler()

            self.assertIsInstance(crawler.db_cont, MagicMock)
            self.assertEqual(Path("./test"), crawler.save_path)
            self.assertEqual("Test Crawler", crawler.type)
            self.assertEqual("Test Crawler : done", crawler.make_done_message())
            self.assertEqual(0, crawler.crawl())

    def test_CrawlerInit(self):
        """Crawlerの初期状態のテスト

        Note:
            ConcreteCrawler()内で初期化されたconfigと、configparser.ConfigParser()で取得したconfigを比較する
            どちらのconfigも設定元は"./config/config.ini"である
            派生クラスで利用する設定値については別ファイルでテストする
        """
        with ExitStack() as stack:
            mock_notification = stack.enter_context(patch("PictureGathering.Crawler.notification"))
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            # 例外発生テスト
            with self.assertRaises(ValueError):
                crawler = ConcreteCrawler("IOError")
            with self.assertRaises(KeyError):
                crawler = ConcreteCrawler("KeyError")
            with self.assertRaises(ValueError):
                crawler = ConcreteCrawler("ValueError")
            with self.assertRaises(Exception):
                crawler = ConcreteCrawler("Exception")

            crawler = ConcreteCrawler()

            # expect_config読み込みテスト
            CONFIG_FILE_NAME = "./config/config.ini"
            expect_config = configparser.ConfigParser()
            self.assertTrue(Path(CONFIG_FILE_NAME).is_file())
            self.assertFalse(
                expect_config.read("ERROR_PATH" + CONFIG_FILE_NAME, encoding="utf8")
            )
            expect_config.read(CONFIG_FILE_NAME, encoding="utf8")

            # 存在しないキーを指定するテスト
            with self.assertRaises(KeyError):
                print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

            # 設定値比較
            self.assertIsInstance(crawler.config, configparser.ConfigParser)
            self.assertIsInstance(expect_config, configparser.ConfigParser)
            self.assertEqual(expect_config["twitter_api_client"]["ct0"],
                             crawler.config["twitter_api_client"]["ct0"])
            self.assertEqual(expect_config["twitter_api_client"]["auth_token"],
                             crawler.config["twitter_api_client"]["auth_token"])
            self.assertEqual(expect_config["twitter_api_client"]["target_screen_name"],
                             crawler.config["twitter_api_client"]["target_screen_name"])
            self.assertEqual(expect_config["twitter_api_client"]["target_id"],
                             crawler.config["twitter_api_client"]["target_id"])

            self.assertEqual(int(expect_config["tweet_timeline"]["likes_get_max_loop"]),
                             int(crawler.config["tweet_timeline"]["likes_get_max_loop"]))
            self.assertEqual(int(expect_config["tweet_timeline"]["likes_get_max_count"]),
                             int(crawler.config["tweet_timeline"]["likes_get_max_count"]))
            self.assertEqual(int(expect_config["tweet_timeline"]["retweet_get_max_loop"]),
                             int(crawler.config["tweet_timeline"]["retweet_get_max_loop"]))
            self.assertEqual(int(expect_config["tweet_timeline"]["retweet_get_max_count"]),
                             int(crawler.config["tweet_timeline"]["retweet_get_max_count"]))

            self.assertEqual(expect_config["save_directory"]["save_fav_path"],
                             crawler.config["save_directory"]["save_fav_path"])
            self.assertEqual(expect_config["save_directory"]["save_retweet_path"],
                             crawler.config["save_directory"]["save_retweet_path"])

            self.assertEqual(int(expect_config["holding"]["holding_file_num"]),
                             int(crawler.config["holding"]["holding_file_num"]))

            # dbはTest_DBControllerBaseで確認

            self.assertEqual(expect_config["notification"]["reply_to_user_name"],
                             crawler.config["notification"]["reply_to_user_name"])

            self.assertEqual(expect_config["discord_webhook_url"]["is_post_discord_notify"],
                             crawler.config["discord_webhook_url"]["is_post_discord_notify"])
            self.assertEqual(expect_config["discord_webhook_url"]["webhook_url"],
                             crawler.config["discord_webhook_url"]["webhook_url"])

            self.assertEqual(expect_config["line_token_keys"]["is_post_line_notify"],
                             crawler.config["line_token_keys"]["is_post_line_notify"])
            self.assertEqual(expect_config["line_token_keys"]["token_key"],
                             crawler.config["line_token_keys"]["token_key"])

            self.assertEqual(expect_config["slack_webhook_url"]["is_post_slack_notify"],
                             crawler.config["slack_webhook_url"]["is_post_slack_notify"])
            self.assertEqual(expect_config["slack_webhook_url"]["webhook_url"],
                             crawler.config["slack_webhook_url"]["webhook_url"])

            self.assertEqual(Path("./test"), crawler.save_path)
            self.assertEqual("Test Crawler", crawler.type)

            self.assertEqual(0, crawler.add_cnt)
            self.assertEqual(0, crawler.del_cnt)
            self.assertEqual([], crawler.add_url_list)
            self.assertEqual([], crawler.del_url_list)

    def test_link_search_register(self):
        """外部リンク探索機構のセットアップをチェックする
        """
        with ExitStack() as stack:
            mock_lsc = stack.enter_context(patch("PictureGathering.Crawler.LinkSearcher.create"))

            crawler = ConcreteCrawler()

            mock_lsc.assert_called_once_with(crawler.config)
            expect = mock_lsc(crawler.config)
            self.assertEqual(expect, crawler.lsb)

    def test_get_exist_filelist(self):
        """save_pathにあるファイル名一覧取得処理をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))

            crawler = ConcreteCrawler()

            # os.walkで収集した結果と比較する
            xs = []
            for root, dir, files in os.walk(crawler.save_path):
                for f in files:
                    path = os.path.join(root, f)
                    xs.append((os.path.getmtime(path), path))
            os.walk(crawler.save_path).close()

            expect_filelist = []
            for mtime, path in sorted(xs, reverse=True):
                expect_filelist.append(path)

            actual_filelist = crawler.get_exist_filelist()
            self.assertEqual(expect_filelist, actual_filelist)

    def test_shrink_folder(self):
        """フォルダ内ファイルの数を一定にする機能をチェックする
        """
        with ExitStack() as stack:
            mock_get_exist_filelist = stack.enter_context(patch("PictureGathering.Crawler.Crawler.get_exist_filelist"))
            mock_update_db_exist_mark = stack.enter_context(patch("PictureGathering.Crawler.Crawler.update_db_exist_mark"))
            mock_get_media_url = stack.enter_context(patch("PictureGathering.Crawler.Crawler.get_media_url"))
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_unlink = stack.enter_context(patch("pathlib.Path.unlink"))
            image_base_url = "http://pbs.twimg.com/media/{}:orig"
            video_base_url = "https://video.twimg.com/ext_tw_video/1144527536388337664/pu/vid/626x882/{}"

            crawler = ConcreteCrawler()
            holding_file_num = 10

            # フォルダ内に存在するファイルのサンプルを生成する
            # 保持すべきholding_file_numを超えるファイルがあるものとする
            # 画像と動画をそれぞれ作り、ランダムにピックアップする
            sample_num = holding_file_num * 2 // 3 * 2
            img_sample = ["sample_img_{}.png".format(i) for i in range(sample_num // 2 + 1)]
            video_sample = ["sample_video_{}.mp4".format(i) for i in range(sample_num // 2 + 1)]
            file_sample = random.sample(img_sample + video_sample, sample_num)  # 結合してシャッフル
            mock_get_exist_filelist.return_value = file_sample

            mock_update_db_exist_mark = None
            mock_get_media_url.side_effect = lambda name: [video_base_url.format(v) for v in video_sample if v == name][0]

            self.assertEqual(Result.success, crawler.shrink_folder(holding_file_num - 1))

            def MakeUrl(filename):
                if ".mp4" in filename:  # media_type == "video":
                    return video_base_url.format(filename)
                else:  # media_type == "photo":
                    return image_base_url.format(filename)

            expect_del_cnt = len(file_sample) - holding_file_num
            expect_del_url_list = file_sample[-expect_del_cnt:len(file_sample)]
            expect_del_url_list = list(map(MakeUrl, expect_del_url_list))
            expect_add_url_list = file_sample[0:holding_file_num]
            expect_add_url_list = list(map(MakeUrl, expect_add_url_list))

            self.assertEqual(expect_del_cnt, crawler.del_cnt)
            self.assertEqual(expect_del_url_list, crawler.del_url_list)

    def test_update_db_exist_mark(self):
        """存在マーキング更新をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))

            crawler = ConcreteCrawler()
            mock_db_cont = crawler.db_cont
            mock_db_cont.clear_flag = MagicMock()
            mock_db_cont.update_flag = MagicMock()

            img_sample = ["sample_img_{}.png".format(i) for i in range(5)]
            crawler.update_db_exist_mark(img_sample)
            mock_db_cont.clear_flag.assert_called_once_with()
            mock_db_cont.update_flag.assert_called_once_with(img_sample, 1)

    def test_get_media_url(self):
        """動画URL問い合わせをチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))

            video_base_url = "https://video.twimg.com/ext_tw_video/1144527536388337664/pu/vid/626x882/{}"

            crawler = ConcreteCrawler()
            mock_db_cont = crawler.db_cont
            mock_db_cont.select_from_media_url = MagicMock()

            def mock_select_from_media_url(filename):
                if "sample_video" in filename:
                    return [{"url": video_base_url.format(filename)}]
                else:
                    return []

            mock_db_cont.select_from_media_url.side_effect = mock_select_from_media_url

            video_sample_filename = "sample_video_1.mp4"
            expect = video_base_url.format(video_sample_filename)
            actual = crawler.get_media_url(video_sample_filename)
            self.assertEqual(expect, actual)

            expect = ""
            actual = crawler.get_media_url("invalid_filename")
            self.assertEqual(expect, actual)

    def test_end_of_process(self):
        """取得後処理をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_whtml = stack.enter_context(patch("PictureGathering.WriteHTML.WriteResultHTML"))
            mock_cplnotify = stack.enter_context(patch("PictureGathering.Crawler.Crawler.post_line_notify"))
            mock_cpsnotify = stack.enter_context(patch("PictureGathering.Crawler.Crawler.post_slack_notify"))
            mock_cpdnotify = stack.enter_context(patch("PictureGathering.Crawler.Crawler.post_discord_notify"))
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))

            crawler = ConcreteCrawler()

            dummy_id = "dummy_id"
            mock_db_cont = crawler.db_cont
            mock_db_cont.update_del = MagicMock()
            mock_db_cont.update_del.side_effect = lambda: [{"tweet_id": dummy_id}]

            crawler.add_cnt = 1
            crawler.type = "Fav"
            actual = crawler.end_of_process()
            self.assertEqual(Result.success, actual)

            mock_whtml.assert_called_once()
            mock_cplnotify.assert_called_once()
            mock_cpsnotify.assert_called_once()
            mock_cpdnotify.assert_called_once()

    def test_post_discord_notify(self):
        """Discord通知ポスト機能をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_req = stack.enter_context(patch("PictureGathering.Crawler.httpx.post"))

            crawler = ConcreteCrawler()

            # mock設定
            response = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 204  # 成功すると204 No Contentが返ってくる
            type(response).status_code = status_code
            mock_req.return_value = response

            str = "text"
            self.assertEqual(Result.success, crawler.post_discord_notify(str))
            mock_req.assert_called_once()

    def test_post_line_notify(self):
        """LINE通知ポスト機能をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_req = stack.enter_context(patch("PictureGathering.Crawler.httpx.post"))

            crawler = ConcreteCrawler()

            # mock設定
            response = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 200
            type(response).status_code = status_code
            mock_req.return_value = response

            str = "text"
            self.assertEqual(Result.success, crawler.post_line_notify(str))
            mock_req.assert_called_once()

    def test_post_slack_notify(self):
        """Slack通知ポスト機能をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_slack = stack.enter_context(patch("PictureGathering.Crawler.WebhookClient"))
            mock_logger_error = stack.enter_context(patch.object(logger, "error"))

            crawler = ConcreteCrawler()

            str = "text"
            mock_slack.return_value.send.return_value.status_code = 200
            self.assertEqual(Result.success, crawler.post_slack_notify(str))
            mock_slack.return_value.send.assert_called_once_with(text="<!here> " + str)

            mock_slack.return_value.send.return_value.status_code = 503
            self.assertEqual(Result.failed, crawler.post_slack_notify(str))

    def test_tweet_media_saver_v2(self):
        """指定URLのメディアを保存する機能をチェックする

            実際にファイル保存する
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_urlopen = stack.enter_context(patch("PictureGathering.Crawler.urllib.request.urlopen"))
            # mock_file_open: MagicMock = stack.enter_context(patch("PictureGathering.Crawler.Path.open", mock_open()))
            mock_shutil = stack.enter_context(patch("PictureGathering.Crawler.shutil.copy2"))
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_logger_debug = stack.enter_context(patch.object(logger, "debug"))

            def return_urlopen(url):
                r = MagicMock()
                r.read.side_effect = lambda: bytes(url.encode())
                return r
            mock_urlopen.side_effect = lambda url, timeout: return_urlopen(url)

            crawler = ConcreteCrawler()
            mock_db_cont = crawler.db_cont
            mock_db_cont.select_from_media_url = MagicMock()
            mock_db_cont.select_from_media_url.side_effect = lambda file_name: []
            mock_db_cont.upsert_v2 = MagicMock()

            tweet_info_list = [self._make_tweet_info(i) for i in range(1, 5)]
            atime = mtime = time.time()

            # テスト用ファイルが残っていたら削除する
            for tweet_info in tweet_info_list:
                file_name = tweet_info.media_filename
                save_file_path = Path(crawler.save_path) / file_name
                save_file_fullpath = save_file_path.absolute()
                save_file_fullpath.unlink(missing_ok=True)

            # 1回目DL
            for tweet_info in tweet_info_list:
                actual = crawler.tweet_media_saver(tweet_info, atime, mtime)
                self.assertEqual(MediaSaveResult.success, actual)

            # 2回目DL
            for tweet_info in tweet_info_list:
                actual = crawler.tweet_media_saver(tweet_info, atime, mtime)
                self.assertEqual(MediaSaveResult.now_exist, actual)

            # DB内にすでに蓄積されていた場合
            mock_db_cont.select_from_media_url.side_effect = lambda file_name: ["already_saved"]
            for tweet_info in tweet_info_list:
                actual = crawler.tweet_media_saver(tweet_info, atime, mtime)
                self.assertEqual(MediaSaveResult.past_done, actual)

            # テスト用ファイルを削除する
            for tweet_info in tweet_info_list:
                file_name = tweet_info.media_filename
                save_file_path = Path(crawler.save_path) / file_name
                save_file_fullpath = save_file_path.absolute()
                save_file_fullpath.unlink(missing_ok=True)

            # DL時に例外発生
            mock_db_cont.select_from_media_url.side_effect = lambda file_name: []
            mock_urlopen.side_effect = Exception()
            for tweet_info in tweet_info_list:
                actual = crawler.tweet_media_saver(tweet_info, atime, mtime)
                self.assertEqual(MediaSaveResult.failed, actual)

    def test_interpret_tweets(self):
        """ツイートオブジェクトの解釈をチェックする
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_tweet_media_saver = stack.enter_context(patch("PictureGathering.Crawler.Crawler.tweet_media_saver"))

            crawler = ConcreteCrawler()

            tweet_info_list = [self._make_tweet_info(i) for i in range(1, 5)]
            expect_args_list = []
            for tweet_info in tweet_info_list:
                dts_format = "%Y-%m-%d %H:%M:%S"
                media_tweet_created_time = tweet_info.created_at
                created_time = time.strptime(media_tweet_created_time, dts_format)
                atime = mtime = time.mktime(
                    (created_time.tm_year,
                     created_time.tm_mon,
                     created_time.tm_mday,
                     created_time.tm_hour,
                     created_time.tm_min,
                     created_time.tm_sec,
                     0, 0, -1)
                )
                expect_args_list.append((tweet_info, atime, mtime))

            actual = crawler.interpret_tweets(tweet_info_list)
            self.assertEqual(Result.success, actual)

            m_calls = mock_tweet_media_saver.mock_calls[:len(tweet_info_list)]
            self.assertEqual(len(tweet_info_list), len(m_calls))
            for expect, actual in zip(expect_args_list, m_calls):
                self.assertEqual(call(expect[0], expect[1], expect[2]), actual)

    def test_trace_external_link(self):
        """外部リンク探索をチェックする

            実際にはファイル保存はしない
        """
        with ExitStack() as stack:
            mock_lsr = stack.enter_context(patch("PictureGathering.Crawler.Crawler.link_search_register"))
            mock_logger_debug = stack.enter_context(patch.object(logger, "debug"))

            crawler = ConcreteCrawler()
            mock_db_cont = crawler.db_cont
            mock_db_cont.select_external_link = MagicMock()
            mock_db_cont.upsert_external_link = MagicMock()
            crawler.lsb = MagicMock()
            mock_lsb = crawler.lsb
            mock_lsb.can_fetch = MagicMock()
            mock_lsb.fetch = MagicMock()

            mock_db_cont.select_external_link.side_effect = lambda url: []
            mock_lsb.can_fetch.side_effect = lambda url: True

            external_link_list = [self._make_external_link(i) for i in range(1, 5)]
            expect_args_list = []
            for external_link in external_link_list:
                url = external_link.external_link_url
                expect_args_list.append(url)

            actual = crawler.trace_external_link(external_link_list)
            self.assertEqual(Result.success, actual)

            select_external_link_calls = mock_db_cont.select_external_link.mock_calls
            self.assertEqual(len(external_link_list), len(select_external_link_calls))
            for expect, actual in zip(expect_args_list, select_external_link_calls):
                self.assertEqual(call(expect), actual)
            mock_db_cont.select_external_link.reset_mock()

            upsert_external_link_calls = mock_db_cont.upsert_external_link.mock_calls
            self.assertEqual(len(external_link_list), len(upsert_external_link_calls))
            for expect, actual in zip(external_link_list, upsert_external_link_calls):
                self.assertEqual(call([expect]), actual)
            mock_db_cont.upsert_external_link.reset_mock()

            mock_lsb_can_fetch_calls = mock_lsb.can_fetch.mock_calls
            self.assertEqual(len(external_link_list), len(mock_lsb_can_fetch_calls))
            for expect, actual in zip(expect_args_list, mock_lsb_can_fetch_calls):
                self.assertEqual(call(expect), actual)
            mock_lsb.can_fetch.reset_mock()

            mock_lsb_fetch_calls = mock_lsb.fetch.mock_calls
            self.assertEqual(len(external_link_list), len(mock_lsb_fetch_calls))
            for expect, actual in zip(expect_args_list, mock_lsb_fetch_calls):
                self.assertEqual(call(expect), actual)
            mock_lsb.fetch.reset_mock()

            mock_lsb.can_fetch.side_effect = lambda url: False
            actual = crawler.trace_external_link(external_link_list)
            self.assertEqual(Result.success, actual)

            mock_db_cont.upsert_external_link.assert_not_called()
            mock_db_cont.upsert_external_link.reset_mock()
            mock_lsb.fetch.assert_not_called()
            mock_lsb.fetch.reset_mock()

            mock_lsb.can_fetch.reset_mock(side_effect=True)
            mock_lsb.fetch.reset_mock(side_effect=True)
            mock_db_cont.select_external_link.side_effect = lambda url: [url]
            actual = crawler.trace_external_link(external_link_list)
            self.assertEqual(Result.success, actual)

            mock_db_cont.upsert_external_link.assert_not_called()
            mock_db_cont.upsert_external_link.reset_mock()
            mock_lsb.can_fetch.assert_not_called()
            mock_lsb.can_fetch.reset_mock()
            mock_lsb.fetch.assert_not_called()
            mock_lsb.fetch.reset_mock()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
