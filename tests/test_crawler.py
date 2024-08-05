import shutil
import sys
import time
import unittest
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from unittest.mock import call

import freezegun
import orjson
from mock import MagicMock, patch

from media_gathering.crawler import Crawler, MediaSaveResult
from media_gathering.model import ExternalLink
from media_gathering.tac.tweet_info import TweetInfo
from media_gathering.util import Result


class ConcreteCrawler(Crawler):
    """テスト用の具体化クローラー

    Crawler.Crawler()の抽象クラスメソッドを最低限実装したテスト用の派生クラス
    """

    def __init__(
        self,
        config_file_name: str = "./config/config_sample.json",
    ) -> None:
        Crawler.CONFIG_FILE_NAME = config_file_name
        super().__init__()

    def is_post(self) -> bool:
        return self.config["notification"]["is_post_fav_done_reply"]

    def make_done_message(self) -> str:
        return "ConcreteCrawler.make_done_message : done"

    def crawl(self) -> Result:
        return Result.success


class TestCrawler(unittest.TestCase):
    def setUp(self) -> None:
        mock_logger = self.enterContext(patch("media_gathering.crawler.logger"))
        self.config_file_path = Path("./config/config_sample.json")
        self.base_path = Path("./tests/save/")
        self._init_directory(self.base_path)
        return super().setUp()

    def tearDown(self) -> None:
        self._delete_directory(self.base_path)
        return super().tearDown()

    def _init_directory(self, path: Path) -> None:
        self._delete_directory(path)
        path.mkdir(parents=True, exist_ok=True)

    def _delete_directory(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(path)

    def _get_instance(self) -> ConcreteCrawler:
        self.mock_notification = self.enterContext(patch("media_gathering.crawler.notification"))
        self.mock_validate_config_file = self.enterContext(
            patch("media_gathering.crawler.Crawler.validate_config_file")
        )
        self.mock_lsr = self.enterContext(patch("media_gathering.crawler.Crawler.link_search_register"))
        return ConcreteCrawler()

    def _make_tweet_info(self, i: int) -> TweetInfo:
        arg_dict = {
            "media_filename": f"sample_photo_{i:02}.jpg",
            "media_url": f"sample_photo_{i:02}_media_url",
            "media_thumbnail_url": f"sample_photo_{i:02}_media_thumbnail_url",
            "tweet_id": f"{i:05}",
            "tweet_url": f"{i:05}_tweet_url",
            "created_at": f"2022-10-21 10:00:{i:02}",
            "user_id": f"{i // 2:03}",
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
            "user_id": f"{i // 2:03}",
            "user_name": f"user_{i:02}",
            "screan_name": f"user_{i:02}_screan_name",
            "tweet_text": f"tweet_text_{i:02}",
            "tweet_via": "sample via",
            "saved_created_at": f"2022-10-21 10:22:{i:02}",
            "link_type": f"pixiv",
        }
        return ExternalLink.create(arg_dict)

    def test_init(self):
        mock_notification = self.enterContext(patch("media_gathering.crawler.notification"))
        mock_validate_config_file = self.enterContext(patch("media_gathering.crawler.Crawler.validate_config_file"))
        mock_lsr = self.enterContext(patch("media_gathering.crawler.Crawler.link_search_register"))
        Params = namedtuple("Params", ["is_keyerror", "is_valueerror", "is_exception", "result", "msg"])

        def pre_run(params: Params) -> None:
            mock_validate_config_file.reset_mock()
            if params.is_keyerror:
                mock_validate_config_file.side_effect = KeyError
            if params.is_valueerror:
                mock_validate_config_file.side_effect = ValueError("value error")
            if params.is_exception:
                mock_validate_config_file.side_effect = Exception
            mock_lsr.reset_mock()
            mock_notification.reset_mock()

        def post_run(params: Params, instance: ConcreteCrawler) -> None:
            mock_validate_config_file.assert_called_once_with(Crawler.CONFIG_FILE_NAME)
            if not params.result:
                config = orjson.loads(self.config_file_path.read_bytes())
                self.assertEqual(config, instance.config)
                self.assertEqual(None, instance.db_cont)
                self.assertEqual(Path(), instance.save_path)
                self.assertEqual("", instance.type)
                self.assertEqual(0, instance.add_cnt)
                self.assertEqual(0, instance.del_cnt)
                self.assertEqual([], instance.add_url_list)
                self.assertEqual([], instance.del_url_list)
                mock_lsr.assert_called_once_with()
                mock_notification.assert_not_called()
            else:
                mock_lsr.assert_not_called()
                error_message = ""
                if params.is_keyerror:
                    error_message = "invalid config file error."
                if params.is_valueerror:
                    error_message = "value error"
                if params.is_exception:
                    error_message = "unknown error."
                mock_notification.notify.assert_called_once_with(
                    title="media-gathering 実行エラー", message=error_message, app_name="media-gathering", timeout=10
                )

        params_list = [
            Params(False, False, False, None, "positive case"),
            Params(True, False, False, KeyError, "key error case"),
            Params(False, True, False, ValueError, "value error case"),
            Params(False, False, True, Exception, "unknown error case"),
        ]
        for params in params_list:
            with self.subTest(params.msg):
                instance = None
                pre_run(params)
                if not params.result:
                    instance = ConcreteCrawler(str(self.config_file_path))
                else:
                    with self.assertRaises(params.result):
                        instance = ConcreteCrawler(str(self.config_file_path))
                post_run(params, instance)

    def test_validate_config_file(self):
        mock_notification = self.enterContext(patch("media_gathering.crawler.notification"))
        mock_lsr = self.enterContext(patch("media_gathering.crawler.Crawler.link_search_register"))
        Params = namedtuple("Params", ["is_permanent", "config_file_path", "error_kind", "result", "msg"])
        config_file_path = self.base_path / "config_sample.json"

        def pre_run(params: Params) -> None:
            mock_lsr.reset_mock()
            mock_notification.reset_mock()

            config_file_path.unlink(missing_ok=True)
            config_dict = orjson.loads(self.config_file_path.read_bytes())
            config_dict["save_permanent"]["save_permanent_media_flag"] = params.is_permanent
            config_dict["twitter_api_client"]["ct0"] = "ct0"
            config_dict["twitter_api_client"]["auth_token"] = "auth_token"
            config_dict["twitter_api_client"]["target_screen_name"] = "target_screen_name"
            config_dict["twitter_api_client"]["target_id"] = 11111
            match params.error_kind:
                case None:
                    pass
                case "key_error":
                    del config_dict["twitter_api_client"]
                case "ct0_error":
                    config_dict["twitter_api_client"]["ct0"] = "dummy_ct0"
                case "auth_token_error":
                    config_dict["twitter_api_client"]["auth_token"] = "dummy_auth_token"
                case "target_screen_name_error":
                    config_dict["twitter_api_client"]["target_screen_name"] = "dummy_target_screen_name"
                case "target_id_error":
                    config_dict["twitter_api_client"]["target_id"] = -1
            config_file_path.write_bytes(orjson.dumps(config_dict))

        params_list = [
            Params(True, str(config_file_path), None, Result.success, "Positive case, permanent is True"),
            Params(False, str(config_file_path), None, Result.success, "Positive case, permanent is False"),
            Params(True, config_file_path, None, ValueError, "Argument type error case"),
            Params(
                True, str(config_file_path.with_name("invalid")), None, ValueError, "Argument invalid path str case"
            ),
            Params(True, str(config_file_path), "ct0_error", ValueError, "ct0 error case"),
            Params(True, str(config_file_path), "auth_token_error", ValueError, "auth_token error case"),
            Params(
                True, str(config_file_path), "target_screen_name_error", ValueError, "target_screen_name error case"
            ),
            Params(True, str(config_file_path), "target_id_error", ValueError, "target_id error case"),
        ]
        for params in params_list:
            with self.subTest(params.msg):
                pre_run(params)
                if params.result == Result.success:
                    instance = ConcreteCrawler(params.config_file_path)
                    self.assertEqual(params.result, instance.validate_config_file(params.config_file_path))
                else:
                    with self.assertRaises(params.result):
                        instance = ConcreteCrawler(params.config_file_path)

    def test_link_search_register(self):
        mock_notification = self.enterContext(patch("media_gathering.crawler.notification"))
        mock_validate_config_file = self.enterContext(patch("media_gathering.crawler.Crawler.validate_config_file"))
        mock_lsr_create = self.enterContext(patch("media_gathering.crawler.LinkSearcher.create"))
        instance = ConcreteCrawler()
        mock_lsr_create.assert_called_once_with(instance.config)
        self.assertEqual(mock_lsr_create.return_value, instance.lsb)

    def test_get_exist_filelist(self):
        instance = self._get_instance()
        instance.save_path = self.base_path / "exist"

        self._init_directory(instance.save_path)
        actual = instance.get_exist_filelist()
        self.assertEqual([], actual)

        self._init_directory(instance.save_path)
        expect = [str(instance.save_path / f"testfile_{index}.txt") for index in range(5)]
        for path_str in expect:
            Path(path_str).touch()
        actual = instance.get_exist_filelist()
        expect.reverse()
        self.assertEqual(expect, actual)

    def test_shrink_folder(self):
        mock_get_exist_filelist = self.enterContext(patch("media_gathering.crawler.Crawler.get_exist_filelist"))
        mock_get_media_url = self.enterContext(patch("media_gathering.crawler.Crawler.get_media_url"))
        mock_update_db_exist_mark = self.enterContext(patch("media_gathering.crawler.Crawler.update_db_exist_mark"))

        mock_get_media_url.side_effect = lambda filename: f"http://video.url.sample/{filename}"
        save_path = self.base_path / "exist"
        Params = namedtuple("Params", ["photo_num", "video_num", "holding_file_num", "result", "msg"])

        def pre_run(params: Params) -> None:
            self._init_directory(save_path)
            mock_get_exist_filelist.reset_mock()
            photo_file = [save_path / f"photo_{index:02}.jpeg" for index in range(params.photo_num)]
            video_file = [save_path / f"video_{index:02}.mp4" for index in range(params.video_num)]
            prepared_file = photo_file + video_file
            for path in prepared_file:
                path.touch()
            mock_get_exist_filelist.side_effect = lambda: prepared_file

            mock_get_media_url.reset_mock()
            mock_update_db_exist_mark.reset_mock()

        def post_run(params: Params, instance: ConcreteCrawler) -> None:
            photo_file = [save_path / f"photo_{index:02}.jpeg" for index in range(params.photo_num)]
            video_file = [save_path / f"video_{index:02}.mp4" for index in range(params.video_num)]
            prepared_file = photo_file + video_file

            expect_del_cnt = 0
            expect_del_url_list = []
            expect_add_img_filename = []
            expect_get_media_url_call = []
            for i, file in enumerate(prepared_file):
                url = ""
                file_path = Path(file)

                if ".mp4" == file_path.suffix:
                    # media_type == "video":
                    expect_get_media_url_call.append(call(file_path.name))
                    url = f"http://video.url.sample/{file_path.name}"
                else:
                    # media_type == "photo":
                    image_base_url = "http://pbs.twimg.com/media/{}:orig"
                    url = image_base_url.format(file_path.name)

                if i > params.holding_file_num:
                    self.assertFalse(file_path.exists())
                    expect_del_cnt += 1
                    expect_del_url_list.append(url)
                else:
                    # self.add_url_list.append(url)
                    expect_add_img_filename.append(file_path.name)
            self.assertEqual(expect_del_cnt, instance.del_cnt)
            self.assertEqual(expect_del_url_list, instance.del_url_list)
            mock_update_db_exist_mark.assert_called_once_with(expect_add_img_filename)
            self.assertEqual(expect_get_media_url_call, mock_get_media_url.mock_calls)

        params_list = [
            Params(5, 0, 5, Result.success, "All photo, no shrink"),
            Params(0, 5, 5, Result.success, "All video, no shrink"),
            Params(2, 3, 5, Result.success, "Mix, no shrink"),
            Params(10, 0, 5, Result.success, "All photo, shrink done"),
            Params(0, 10, 5, Result.success, "All video, shrink done"),
            Params(5, 5, 5, Result.success, "Mix, shrink done"),
        ]
        for params in params_list:
            with self.subTest(params.msg):
                instance = self._get_instance()
                pre_run(params)
                actual = instance.shrink_folder(params.holding_file_num)
                self.assertEqual(params.result, actual)
                post_run(params, instance)

    def test_update_db_exist_mark(self):
        instance = self._get_instance()
        instance.db_cont = MagicMock()

        photo_file = [f"photo_{index:02}.jpeg" for index in range(5)]
        actual = instance.update_db_exist_mark(photo_file)
        self.assertEqual(Result.success, actual)
        instance.db_cont.clear_flag.assert_called_once_with()
        instance.db_cont.update_flag.assert_called_once_with(photo_file, 1)

    def test_get_media_url(self):
        instance = self._get_instance()
        instance.db_cont = MagicMock()

        def select_from_media_url(filename):
            if not filename:
                return ""
            return [{"url": f"http://video.url.sample/{filename}"}]

        instance.db_cont.select_from_media_url.side_effect = select_from_media_url

        video_file = "video_01.mp4"
        actual = instance.get_media_url(video_file)
        self.assertEqual(f"http://video.url.sample/{video_file}", actual)
        instance.db_cont.select_from_media_url.assert_called_once_with(video_file)

        instance.db_cont.reset_mock()
        actual = instance.get_media_url("")
        self.assertEqual("", actual)
        instance.db_cont.select_from_media_url.assert_called_once_with("")

    def test_end_of_process(self):
        mock_html_writer = self.enterContext(patch("media_gathering.crawler.HtmlWriter"))
        mock_discord_notify = self.enterContext(patch("media_gathering.crawler.Crawler.post_discord_notify"))
        mock_line_notify = self.enterContext(patch("media_gathering.crawler.Crawler.post_line_notify"))
        mock_slack_notify = self.enterContext(patch("media_gathering.crawler.Crawler.post_slack_notify"))
        mock_twitter = self.enterContext(patch("media_gathering.crawler.TwitterAPIClientAdapter"))

        Params = namedtuple(
            "Params",
            [
                "add_url_list",
                "del_url_list",
                "notification",
                "discord_notify",
                "line_notify",
                "slack_notify",
                "error_occur",
                "result",
                "msg",
            ],
        )

        def pre_run(params: Params, instance: ConcreteCrawler) -> ConcreteCrawler:
            instance.add_cnt = len(params.add_url_list)
            instance.add_url_list = params.add_url_list
            instance.del_cnt = len(params.del_url_list)
            instance.del_url_list = params.del_url_list
            instance.config["discord_webhook_url"]["is_post_discord_notify"] = params.discord_notify
            instance.config["line_token_keys"]["is_post_line_notify"] = params.line_notify
            instance.config["slack_webhook_url"]["is_post_slack_notify"] = params.slack_notify
            instance.config["notification"]["is_post_fav_done_reply"] = params.notification

            mock_html_writer.reset_mock()
            mock_discord_notify.reset_mock(side_effect=True)
            mock_line_notify.reset_mock(side_effect=True)
            mock_slack_notify.reset_mock(side_effect=True)
            mock_twitter.reset_mock(side_effect=True)

            if params.error_occur:
                if params.discord_notify:
                    mock_discord_notify.side_effect = ValueError
                elif params.line_notify:
                    mock_line_notify.side_effect = ValueError
                elif params.slack_notify:
                    mock_slack_notify.side_effect = ValueError

            return instance

        def post_run(params: Params, instance: ConcreteCrawler):
            self.assertEqual(
                [call(instance.type, instance.db_cont), call().write_result_html()], mock_html_writer.mock_calls
            )
            done_msg = instance.make_done_message()
            add_cnt = len(params.add_url_list)
            del_cnt = len(params.del_url_list)
            if add_cnt != 0 or del_cnt != 0:
                if params.notification:
                    ct0 = instance.config["twitter_api_client"]["ct0"]
                    auth_token = instance.config["twitter_api_client"]["auth_token"]
                    target_screen_name = instance.config["twitter_api_client"]["target_screen_name"]
                    target_id = int(instance.config["twitter_api_client"]["target_id"])
                    reply_to_user_name = instance.config["notification"]["reply_to_user_name"]
                    msg = f"@{reply_to_user_name} {done_msg}"
                    self.assertEqual(
                        [call(ct0, auth_token, target_screen_name, target_id), call().account.tweet(msg)],
                        mock_twitter.mock_calls,
                    )
                if params.discord_notify:
                    mock_discord_notify.assert_called_once_with(done_msg)
                if params.line_notify:
                    mock_line_notify.assert_called_once_with(done_msg)
                if params.slack_notify:
                    mock_slack_notify.assert_called_once_with(done_msg)

        params_list = [
            Params([], [], False, False, False, False, False, Result.success, "add and del is nothing case"),
            Params(["add_url_1"], [], False, False, False, False, False, Result.success, "one add case"),
            Params(
                ["add_url_1", "add_url_2"], [], False, False, False, False, False, Result.success, "multi add case"
            ),
            Params([], ["del_url_1"], False, False, False, False, False, Result.success, "one del case"),
            Params(
                [], ["del_url_1", "del_url_2"], False, False, False, False, False, Result.success, "multi del case"
            ),
            Params(["add_url_1"], [], False, True, False, False, False, Result.success, "discord_notify case"),
            Params(["add_url_1"], [], False, False, True, False, False, Result.success, "line_notify case"),
            Params(["add_url_1"], [], False, False, False, True, False, Result.success, "slack_notify case"),
            Params(["add_url_1"], [], False, True, True, True, False, Result.success, "all notify case"),
            Params(["add_url_1"], [], False, True, False, False, True, Result.success, "discord_notify error case"),
            Params(["add_url_1"], [], False, False, True, False, True, Result.success, "line_notify error case"),
            Params(["add_url_1"], [], False, False, False, True, True, Result.success, "slack_notify error case"),
            Params(["add_url_1"], [], True, False, False, False, False, Result.success, "tweet notification case"),
        ]
        for params in params_list:
            instance = pre_run(params, self._get_instance())
            actual = instance.end_of_process()
            self.assertEqual(params.result, actual)
            post_run(params, instance)

    def test_post_discord_notify(self):
        mock_req = self.enterContext(patch("media_gathering.crawler.httpx.post"))

        instance = self._get_instance()
        url = instance.config["discord_webhook_url"]["webhook_url"]
        headers = {"Content-Type": "application/json"}

        message = """Retweet MediaGathering run.
        2023/11/23 12:34:56 Process Done !!
        add 4 new images. delete 4 old images.
        https://pbs.twimg.com/media/photo_01.jpg
        https://pbs.twimg.com/media/photo_02.jpg
        https://pbs.twimg.com/media/video_01.mp4
        https://pbs.twimg.com/media/video_02.mp4"""
        description_msg = ""
        media_links = []
        lines = message.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("http"):
                media_links.append(line)
            else:
                description_msg += line + "\n"
        embeds = []
        if len(media_links) > 0:
            key_url = media_links[0]
            embeds.append({"description": description_msg, "url": key_url, "image": {"url": key_url}})
            for media_link_url in media_links[1:]:
                embeds.append({"url": key_url, "image": {"url": media_link_url}})
        payload = {"embeds": embeds}
        actual = instance.post_discord_notify(message, True)
        self.assertEqual(Result.success, actual)
        mock_req.assert_called_once_with(url, headers=headers, data=orjson.dumps(payload).decode())
        mock_req.reset_mock()

        no_media_message = """Retweet MediaGathering run.
        2023/11/23 12:34:56 Process Done !!
        add 0 new images. delete 0 old images."""
        description_msg = ""
        lines = no_media_message.split("\n")
        for line in lines:
            line = line.strip()
            description_msg += line + "\n"
        embeds = [{"description": description_msg}]
        payload = {"embeds": embeds}
        actual = instance.post_discord_notify(no_media_message, True)
        self.assertEqual(Result.success, actual)
        mock_req.assert_called_once_with(url, headers=headers, data=orjson.dumps(payload).decode())
        mock_req.reset_mock()

        payload = {"content": message}
        actual = instance.post_discord_notify(message, False)
        self.assertEqual(Result.success, actual)
        mock_req.assert_called_once_with(url, headers=headers, data=orjson.dumps(payload).decode())
        mock_req.reset_mock()

    def test_post_line_notify(self):
        mock_req = self.enterContext(patch("media_gathering.crawler.httpx.post"))

        instance = self._get_instance()

        url = "https://notify-api.line.me/api/notify"
        token = instance.config["line_token_keys"]["token_key"]
        headers = {"Authorization": "Bearer " + token}
        str = "text"
        payload = {"message": str}
        actual = instance.post_line_notify(str)
        self.assertEqual(Result.success, actual)
        mock_req.assert_called_once_with(url, headers=headers, params=payload)

    def test_post_slack_notify(self):
        mock_ssl = self.enterContext(patch("media_gathering.crawler.ssl"))
        mock_certifi = self.enterContext(patch("media_gathering.crawler.certifi"))
        mock_slack = self.enterContext(patch("media_gathering.crawler.WebhookClient"))

        instance = self._get_instance()

        str = "text"
        mock_slack.return_value.send.return_value.status_code = 200
        self.assertEqual(Result.success, instance.post_slack_notify(str))
        mock_slack.return_value.send.assert_called_once_with(text="<!here> " + str)

        mock_slack.return_value.send.return_value.status_code = 503
        self.assertEqual(Result.failed, instance.post_slack_notify(str))

    def test_tweet_media_saver(self):
        mock_freezegun = freezegun.freeze_time("2024-06-23 12:34:56")
        mock_client = self.enterContext(patch("media_gathering.crawler.httpx.Client"))
        atime = 1719107372
        mtime = 1719107372

        Params = namedtuple(
            "Params",
            [
                "session",
                "is_skip",
                "is_exist",
                "is_fetch_error",
                "is_save_blob",
                "is_valid_size",
                "is_permanent",
                "result",
                "msg",
            ],
        )

        def pre_run(instance: ConcreteCrawler, params: Params) -> tuple[TweetInfo, ConcreteCrawler, Params]:
            tweet_info = self._make_tweet_info(1)
            instance.save_path = Path(instance.config["save_directory"]["save_fav_path"])
            self._init_directory(instance.save_path)

            instance.config["db"]["save_blob"] = params.is_save_blob
            instance.config["save_permanent"]["save_permanent_media_flag"] = params.is_permanent
            permanent_save_path = Path(instance.config["save_permanent"]["save_permanent_media_path"])
            self._init_directory(permanent_save_path)

            if params.session:
                params = params._replace(session=mock_client.return_value)

            instance.db_cont = MagicMock()
            if params.is_skip:
                instance.db_cont.select_from_media_url.side_effect = lambda file_name: [file_name]
            else:
                instance.db_cont.select_from_media_url.side_effect = lambda file_name: []

            if params.is_exist:
                (instance.save_path / tweet_info.media_filename).write_bytes(tweet_info.media_filename.encode())

            if params.is_fetch_error:
                mock_client.return_value.get.side_effect = ValueError
            else:

                def return_get(url_orig: str, timeout: int) -> MagicMock:
                    r = MagicMock()
                    r.content = url_orig.encode() if params.is_valid_size else bytes()
                    return r

                mock_client.return_value.get.side_effect = return_get
            mock_client.reset_mock()
            return tweet_info, instance, params

        def post_run(instance: ConcreteCrawler, params: Params) -> None:
            tweet_info = self._make_tweet_info(1)
            url_orig = tweet_info.media_url
            url_thumbnail = tweet_info.media_thumbnail_url
            file_name = tweet_info.media_filename
            save_file_path = Path(instance.save_path) / file_name
            save_file_fullpath = save_file_path.absolute()

            instance.db_cont.select_from_media_url.assert_called_once_with(file_name)
            if params.is_skip or params.is_exist:
                mock_client.return_value.get.assert_not_called()
                instance.db_cont.upsert.assert_not_called()
                return

            mock_client.return_value.get.assert_called_once_with(url_orig, timeout=60)
            if params.is_fetch_error:
                instance.db_cont.upsert.assert_not_called()
                return
            self.assertEqual([url_orig], instance.add_url_list)

            dts_format = "%Y-%m-%d %H:%M:%S"
            params_dict = {
                "is_exist_saved_file": True,
                "img_filename": file_name,
                "url": url_orig,
                "url_thumbnail": url_thumbnail,
                "tweet_id": tweet_info.tweet_id,
                "tweet_url": tweet_info.tweet_url,
                "created_at": tweet_info.created_at,
                "user_id": tweet_info.user_id,
                "user_name": tweet_info.user_name,
                "screan_name": tweet_info.screan_name,
                "tweet_text": tweet_info.tweet_text,
                "tweet_via": tweet_info.tweet_via,
                "saved_localpath": str(save_file_fullpath),
                "saved_created_at": datetime.now().strftime(dts_format),
            }
            media_size = -1
            save_blob_flag = params.is_save_blob
            if save_blob_flag:
                params_dict["media_blob"] = save_file_fullpath.read_bytes()
                media_size = len(params_dict["media_blob"])
                params_dict["media_size"] = media_size
            else:
                params_dict["media_blob"] = None
                media_size = save_file_fullpath.stat().st_size
                params_dict["media_size"] = media_size

            if media_size <= 0:
                instance.db_cont.upsert.assert_not_called()
                return
            instance.db_cont.upsert.assert_called_once_with(params_dict)

            self.assertEqual(1, instance.add_cnt)

            self.assertTrue(save_file_fullpath.is_file())
            dst_path = Path(instance.config["save_permanent"]["save_permanent_media_path"])
            dst_path = dst_path / save_file_fullpath.name
            self.assertEqual(params.is_permanent, dst_path.is_file())

        params_list = [
            Params(None, False, False, False, False, True, True, MediaSaveResult.success, "success case"),
            Params("use session", False, False, False, False, True, True, MediaSaveResult.success, "use session"),
            Params(None, True, False, False, False, True, True, MediaSaveResult.past_done, "skip case"),
            Params(None, False, True, False, False, True, True, MediaSaveResult.now_exist, "file exist case"),
            Params(None, False, False, True, False, True, True, MediaSaveResult.failed, "fetch error case"),
            Params(None, False, False, False, True, True, True, MediaSaveResult.success, "save blob case"),
            Params(None, False, False, False, False, False, True, MediaSaveResult.failed, "invalid size case"),
            Params(None, False, False, False, False, True, False, MediaSaveResult.success, "permanent false case"),
        ]
        for params in params_list:
            with self.subTest(params.msg):
                instance = self._get_instance()
                tweet_info, instance, params = pre_run(instance, params)
                actual = instance.tweet_media_saver(tweet_info, atime, mtime, params.session)
                self.assertEqual(params.result, actual)
                post_run(instance, params)

    def test_interpret_tweets(self):
        mock_freezegun = freezegun.freeze_time("2024-06-23 12:34:56")
        mock_tweet_media_saver = self.enterContext(patch("media_gathering.crawler.Crawler.tweet_media_saver"))
        mock_client = self.enterContext(patch("media_gathering.crawler.httpx.Client"))

        crawler = self._get_instance()

        session = mock_client.return_value
        tweet_info_list = [self._make_tweet_info(i) for i in range(1, 5)]
        expect_args_list = []
        for tweet_info in tweet_info_list:
            dts_format = "%Y-%m-%d %H:%M:%S"
            media_tweet_created_time = tweet_info.created_at
            created_time = time.strptime(media_tweet_created_time, dts_format)
            atime = mtime = time.mktime((
                created_time.tm_year,
                created_time.tm_mon,
                created_time.tm_mday,
                created_time.tm_hour,
                created_time.tm_min,
                created_time.tm_sec,
                0,
                0,
                -1,
            ))
            expect_args_list.append(call(tweet_info, atime, mtime, session))

        actual = crawler.interpret_tweets(tweet_info_list)
        self.assertEqual(Result.success, actual)
        self.assertEqual(expect_args_list, mock_tweet_media_saver.mock_calls[: len(expect_args_list)])

        mock_tweet_media_saver.side_effect = lambda tweet_info, atime, mtime, session: MediaSaveResult.failed
        actual = crawler.interpret_tweets(tweet_info_list)
        self.assertEqual(Result.failed, actual)

    def test_trace_external_link(self):
        Params = namedtuple("Params", ["is_skip", "can_fetch", "result", "msg"])

        def pre_run(instance: ConcreteCrawler, params: Params) -> tuple[ConcreteCrawler, list[ExternalLink]]:
            instance.db_cont = MagicMock()
            instance.lsb = MagicMock()
            if params.is_skip:
                instance.db_cont.select_external_link.side_effect = lambda url: [url]
            else:
                instance.db_cont.select_external_link.side_effect = lambda url: []
            instance.lsb.can_fetch.side_effect = lambda url: params.can_fetch

            external_link_list = [self._make_external_link(i) for i in range(1, 5)]
            return instance, external_link_list

        def post_run(instance: ConcreteCrawler, params: Params) -> None:
            external_link_list = [self._make_external_link(i) for i in range(1, 5)]
            expect_url_list = []
            expect_external_link_list = []
            for external_link in external_link_list:
                url = external_link.external_link_url
                expect_url_list.append(call(url))
                expect_external_link_list.append(call([external_link]))
            self.assertEqual(expect_url_list, instance.db_cont.select_external_link.mock_calls)

            if params.is_skip:
                instance.lsb.can_fetch.assert_not_called()
                instance.lsb.fetch.assert_not_called()
                instance.db_cont.upsert_external_link.assert_not_called()
                return

            self.assertEqual(expect_url_list, instance.lsb.can_fetch.mock_calls)
            if params.can_fetch:
                self.assertEqual(expect_url_list, instance.lsb.fetch.mock_calls)
                self.assertEqual(expect_external_link_list, instance.db_cont.upsert_external_link.mock_calls)
            else:
                instance.lsb.fetch.assert_not_called()
                instance.db_cont.upsert_external_link.assert_not_called()

        params_list = [
            Params(False, False, Result.success, "nothing fetch"),
            Params(False, True, Result.success, "can fetch"),
            Params(True, False, Result.success, "all skip"),
        ]
        for params in params_list:
            with self.subTest(params.msg):
                instance = self._get_instance()
                instance, external_link_list = pre_run(instance, params)
                actual = instance.trace_external_link(external_link_list)
                self.assertEqual(params.result, actual)
                post_run(instance, params)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
