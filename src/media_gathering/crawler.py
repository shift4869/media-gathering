import configparser
import enum
import logging.config
import os
import shutil
import ssl
import time
from abc import ABCMeta, abstractmethod
from datetime import datetime
from logging import INFO, getLogger
from pathlib import Path

import certifi
import httpx
import orjson
from plyer import notification
from slack_sdk.webhook import WebhookClient

from media_gathering.db_controller_base import DBControllerBase
from media_gathering.html_writer.html_writer import HtmlWriter
from media_gathering.link_search.link_searcher import LinkSearcher
from media_gathering.log_message import MSG
from media_gathering.model import ExternalLink
from media_gathering.tac.tweet_info import TweetInfo
from media_gathering.util import Result

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    # 自分以外のすべてのライブラリのログ出力を抑制
    if "media_gathering" not in name:
        getLogger(name).disabled = True
logger = getLogger(__name__)
logger.setLevel(INFO)


class MediaSaveResult(enum.Enum):
    success = enum.auto()  # 成功（現在存在せず、過去にも取得したことが無い→今回でDLを実際に実行した）
    now_exist = enum.auto()  # 現在存在している
    past_done = enum.auto()  # 過去に取得済
    failed = enum.auto()  # 失敗（メディア辞書構造がエラー、urlが取得できない）


class Crawler(metaclass=ABCMeta):
    """クローラー

    Fav/Retweetクローラーのベースとなるクローラークラス

    Note:
        このクラスを継承するためには@abstractmethodデコレータつきのメソッドを実装する必要がある。

    Args:
        metaclass (metaclass): 抽象クラス指定

    Attributes:
        CONFIG_FILE_NAME (str): 設定ファイルパス
        config (ConfigParser): 設定ini構造体
        lsb (LinkSearcher): 外部リンク探索機構ベースクラス
        db_cont (DBControllerBase): DB操作用クラス（実体はCrawler派生クラスで規定）
        save_path (str): メディア保存先パス
        type (str): 継承先を表すタイプ識別{Fav, RT}
        add_cnt (int): 新規追加したメディアの数
        del_cnt (int): 削除したメディアの数
        add_url_list (list): 新規追加したメディアのURLリスト
        del_url_list (list): 削除したメディアのURLリスト
    """

    CONFIG_FILE_NAME = "./config/config.ini"

    def __init__(self) -> None:
        logger.info(MSG.CRAWLER_INIT_START.value)

        def notify(error_message: str):
            notification.notify(
                title="Media Gathering 実行エラー", message=error_message, app_name="Media Gathering", timeout=10
            )

        try:
            self.validate_config_file(self.CONFIG_FILE_NAME)

            self.config = configparser.ConfigParser()
            self.config.read(self.CONFIG_FILE_NAME, encoding="utf8")

            config = self.config["save_directory"]
            Path(config["save_fav_path"]).mkdir(parents=True, exist_ok=True)
            Path(config["save_retweet_path"]).mkdir(parents=True, exist_ok=True)

            config = self.config["save_permanent"]
            if config.getboolean("save_permanent_media_flag"):
                Path(config["save_permanent_media_path"]).mkdir(parents=True, exist_ok=True)

            # 外部リンク探索機構のセットアップ
            self.link_search_register()
        except KeyError as e:
            error_message = "invalid config file error."
            logger.exception(e)
            notify(error_message)
            raise
        except ValueError as e:
            error_message = e.args[0]
            logger.exception(e)
            notify(error_message)
            raise
        except Exception as e:
            error_message = "unknown error."
            logger.exception(e)
            notify(error_message)
            raise

        # 派生クラスで実体が代入されるメンバ
        # 情報保持DBコントローラー
        self.db_cont: DBControllerBase = None
        # 保存先パス
        self.save_path = Path()
        # クローラタイプ = ["Fav", "RT"]
        self.type = ""

        # 処理中～処理完了後に使用する追加削除カウント・リスト
        self.add_cnt = 0
        self.del_cnt = 0
        self.add_url_list = []
        self.del_url_list = []
        logger.info(MSG.CRAWLER_INIT_DONE.value)

    def validate_config_file(self, config_file_path: str) -> Result:
        """コンフィグファイルが正当な内容か簡易的に調べる

        Notes:
            このメソッドでエラーがraiseしなかったとしても、
            コンフィグファイルに必要なキーがすべて存在するかは保証されない。

        Args:
            config_file_path (str): コンフィグファイルパス

        Raise:
            コンフィグファイルが不正ならばValueError, またはKeyError
        """
        if not isinstance(config_file_path, str):
            raise ValueError("Argument 'config_file_path' must be str.")
        path: Path = Path(config_file_path)
        if not path.is_file():
            raise ValueError(f"{path.name} is not exist.")
        config = configparser.ConfigParser()
        config.read(path, encoding="utf8")

        ct0 = config["twitter_api_client"]["ct0"]
        auth_token = config["twitter_api_client"]["auth_token"]
        target_screen_name = config["twitter_api_client"]["target_screen_name"]
        target_id = config["twitter_api_client"]["target_id"]

        if ct0 == "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
            raise ValueError("'ct0' must be your account 'ct0' value.")
        if auth_token == "xxxxxxxxxxxxxxxxxxxxxxxxx":
            raise ValueError("'auth_token' must be your account 'auth_token' value.")
        if target_screen_name == "{your Twitter ID screen_name (exclude @)}":
            raise ValueError("'target_screen_name' must be target screen_name for crawl.")
        if target_id == "{your Twitter ID (numeric)}":
            raise ValueError("'target_id' must be target account id.")
        return Result.success

    def link_search_register(self) -> Result:
        """外部リンク探索機構のセットアップ

        Notes:
            self.lsbに設定する
        """
        # 外部リンク探索を登録
        self.lsb = LinkSearcher.create(self.config)
        return Result.success

    def get_exist_filelist(self) -> list[str]:
        """self.save_pathに存在するファイル名一覧を取得する

        Returns:
            list[str]: self.save_pathに存在するファイル名一覧
        """
        filelist = []
        save_path = Path(self.save_path)

        # save_path配下のファイルとサブディレクトリ内を捜査し、全てのファイルを収集する
        # (更新日時（mtime）, パス文字列)のタプルをリストに保持する
        filelist_tp = [(sp.stat().st_mtime, str(sp)) for sp in save_path.glob("**/*") if sp.is_file()]

        # 更新日時（mtime）でソートし、最新のものからfilelistに追加する
        for mtime, path in sorted(filelist_tp, reverse=True):
            filelist.append(path)
        return filelist

    def shrink_folder(self, holding_file_num: int) -> Result:
        """フォルダ内ファイルの数を一定にする

        Args:
            holding_file_num (int): フォルダ内に残すファイルの数
        """
        filelist = self.get_exist_filelist()

        # フォルダに既に保存しているファイルにはURLの情報がない
        # ファイル名とドメインを結びつけてURLを手動で生成する
        # twitterの画像URLの仕様が変わったらここも変える必要がある
        # http://pbs.twimg.com/media/{file.basename}.jpg:orig
        # 動画ファイルのURLはDBに問い合わせる
        add_img_filename = []
        for i, file in enumerate(filelist):
            url = ""
            file_path = Path(file)

            if ".mp4" == file_path.suffix:  # media_type == "video":
                url = self.get_media_url(file_path.name)
            else:  # media_type == "photo":
                image_base_url = "http://pbs.twimg.com/media/{}:orig"
                url = image_base_url.format(file_path.name)

            if i > holding_file_num:
                file_path.unlink(missing_ok=True)
                self.del_cnt += 1
                self.del_url_list.append(url)
            else:
                # self.add_url_list.append(url)
                add_img_filename.append(file_path.name)

        # 存在マーキングを更新する
        self.update_db_exist_mark(add_img_filename)
        return Result.success

    def update_db_exist_mark(self, add_img_filename) -> Result:
        # 存在マーキングを更新する
        self.db_cont.clear_flag()
        self.db_cont.update_flag(add_img_filename, 1)
        return Result.success

    def get_media_url(self, filename) -> str:
        # 'https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/b0ZDq8zG_HppFWb6.mp4?tag=10'
        response = self.db_cont.select_from_media_url(filename)
        url = response[0]["url"] if len(response) == 1 else ""
        return url

    @abstractmethod
    def make_done_message(self) -> str:
        """実行後の結果文字列を生成する"""
        return ""

    def end_of_process(self) -> Result:
        """実行後の後処理

        Returns:
            Result: 成功時Result.success
        """
        logger.info("")

        done_msg = self.make_done_message()
        config = self.config
        HtmlWriter(self.type, self.db_cont).write_result_html()

        logger.info("\t".join(done_msg.splitlines()))

        if self.add_cnt != 0 or self.del_cnt != 0:
            if self.add_cnt != 0:
                logger.debug("add url:")
                for url in self.add_url_list:
                    logger.debug(url)

            if self.del_cnt != 0:
                logger.debug("del url:")
                for url in self.del_url_list:
                    logger.debug(url)

            if config["discord_webhook_url"].getboolean("is_post_discord_notify"):
                try:
                    self.post_discord_notify(done_msg)
                    logger.info("Discord notify posted.")
                except Exception as e:
                    logger.exception(e)
                    logger.warn("Discord notify post failed.")

            if config["line_token_keys"].getboolean("is_post_line_notify"):
                try:
                    self.post_line_notify(done_msg)
                    logger.info("Line notify posted.")
                except Exception as e:
                    logger.exception(e)
                    logger.warn("Line notify post failed.")

            if config["slack_webhook_url"].getboolean("is_post_slack_notify"):
                try:
                    self.post_slack_notify(done_msg)
                    logger.info("Slack notify posted.")
                except Exception as e:
                    logger.exception(e)
                    logger.warn("Slack notify post failed.")

        logger.info("End Of " + self.type + " Crawl Process.")
        return Result.success

    def post_discord_notify(self, message: str, is_embed: bool = True) -> Result:
        """Discord通知ポスト

        Args:
            message (str): Discordに通知する文字列
            is_embed (bool): 埋め込んで投稿するかどうか

        Returns:
            Result: 成功時Result.success
        """
        url = self.config["discord_webhook_url"]["webhook_url"]
        headers = {"Content-Type": "application/json"}

        payload = {}
        if is_embed:
            # desc_msg = """Retweet MediaGathering run.
            # 2023/02/03 10:31:30 Process Done !!
            # add 4 new images. delete 4 old images."""
            # """https://pbs.twimg.com/media/Fn-iG41aYAAjYb7.jpg
            # https://pbs.twimg.com/media/Fn_OTxhXEAIMyb0.jpg
            # https://pbs.twimg.com/media/Fn4DUHSaIAM8Ehz.jpg
            # https://pbs.twimg.com/media/Fn-2N4UagAAlzEd.jpg"""

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
            else:
                embeds.append({"description": description_msg})

            payload = {"embeds": embeds}

        if not payload:
            payload = {"content": message}

        response = httpx.post(url, headers=headers, data=orjson.dumps(payload).decode())
        response.raise_for_status()

        # if response.status_code != 204:  # 成功すると204 No Contentが返ってくる
        #     logger.error("Error code: {0}".format(response.status_code))
        #     return Result.failed

        return Result.success

    def post_line_notify(self, str: str) -> Result:
        """LINE通知ポスト

        Args:
            str (str): LINEに通知する文字列

        Returns:
            Result: 成功時Result.success
        """
        url = "https://notify-api.line.me/api/notify"
        token = self.config["line_token_keys"]["token_key"]

        headers = {"Authorization": "Bearer " + token}
        payload = {"message": str}

        response = httpx.post(url, headers=headers, params=payload)
        response.raise_for_status()

        # if response.status_code != 200:
        #     logger.error("Error code: {0}".format(response.status_code))
        #     return -1

        return Result.success

    def post_slack_notify(self, str: str) -> Result:
        """Slack通知ポスト

        Args:
            str (str): Slackに通知する文字列

        Returns:
            Result: 成功時Result.success, 失敗時Result.failed
        """
        url = self.config["slack_webhook_url"]["webhook_url"]
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        webhook = WebhookClient(url, ssl=ssl_context)
        post_text = "<!here> " + str
        response = webhook.send(text=post_text)
        if response.status_code != 200:
            logger.error("Error code: {0}".format(response.status_code))
            return Result.failed
        return Result.success

    def tweet_media_saver(
        self, tweet_info: TweetInfo, atime: float, mtime: float, session: httpx.Client | None = None
    ) -> MediaSaveResult:
        """tweet_infoで指定されるツイートのメディアを保存する

        Args:
            tweet_info (TweetInfo): メディア含むツイート情報
            atime (float): 指定更新日時
            mtime (float): 指定更新日時
            session (httpx.Client | None): 保存時に使うセッション

        Returns:
            MediaSaveResult:
                success: 成功（現在存在せず、過去にも取得したことが無い→DLを実際に実行した）
                now_exist: 現在存在している
                past_done: 過去に取得済
                failed: 失敗（メディア辞書構造がエラー、urlが取得できない）
        """
        if not session:
            session = httpx.Client(follow_redirects=True)
        url_orig = tweet_info.media_url
        url_thumbnail = tweet_info.media_thumbnail_url
        file_name = tweet_info.media_filename
        save_file_path = Path(self.save_path) / file_name
        save_file_fullpath = save_file_path.absolute()

        # 過去に取得済かどうか調べる
        if self.db_cont.select_from_media_url(file_name) != []:
            logger.debug(save_file_fullpath.name + " -> skip")
            return MediaSaveResult.past_done

        if not save_file_fullpath.is_file():
            # URLからメディアを取得してローカルに保存
            try:
                response = session.get(url_orig, timeout=60)
                response.raise_for_status()
                save_file_fullpath.write_bytes(response.content)
            except Exception:
                # URLからのメディア取得に失敗
                # 削除されていた場合など
                logger.info(save_file_fullpath.name + " -> failed (maybe removed).")
                return MediaSaveResult.failed
            self.add_url_list.append(url_orig)

            # DB操作
            # db_cont.upsert 派生クラスによって呼び分けられる
            dts_format = "%Y-%m-%d %H:%M:%S"
            params = {
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
            save_blob_flag = self.config["db"].getboolean("save_blob")
            try:
                if save_blob_flag:
                    params["media_blob"] = save_file_fullpath.read_bytes()
                    media_size = len(params["media_blob"])
                    params["media_size"] = media_size
                else:
                    params["media_blob"] = None
                    media_size = save_file_fullpath.stat().st_size
                    params["media_size"] = media_size
            except Exception:
                params["media_blob"] = None
                params["media_size"] = -1

            if media_size <= 0:
                if media_size == 0:
                    logger.warning(save_file_fullpath.name + " -> failed (0 byte file).")
                else:
                    logger.warning(save_file_fullpath.name + " -> failed.")
                return MediaSaveResult.failed

            self.db_cont.upsert(params)

            # 更新日時を上書き
            os.utime(save_file_fullpath, (atime, mtime))

            # ログ書き出し
            logger.info(save_file_fullpath.name + " -> done")
            self.add_cnt += 1

            # 常に保存する設定の場合はコピーする
            config = self.config["save_permanent"]
            if config.getboolean("save_permanent_media_flag"):
                dst_path = Path(config["save_permanent_media_path"])
                shutil.copy2(save_file_fullpath, dst_path)
        else:
            # 既に存在している場合
            logger.debug(save_file_fullpath.name + " -> exist")
            return MediaSaveResult.now_exist
        return MediaSaveResult.success

    def interpret_tweets(self, tweet_info_list: list[TweetInfo]) -> Result:
        result_list: list[MediaSaveResult] = []
        session = httpx.Client(follow_redirects=True)
        for tweet_info in tweet_info_list:
            """タイムスタンプについて
                https://srbrnote.work/archives/4054
                作成日時:ctime, 更新日時:mtime, アクセス日時:atimeがある
                ctimeはOS依存のため設定には外部ライブラリが必要
                ここでは
                    Favならばatime=mtime=ツイート投稿日時 とする
                    RTならばatime=mtime=ツイート投稿日時 とする
                収集されたツイートの投稿日時はDBのcreated_at項目に保持される
            """
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

            # メディア保存
            result: MediaSaveResult = self.tweet_media_saver(tweet_info, atime, mtime, session)
            result_list.append(result)
        if [r for r in result_list if r == MediaSaveResult.failed]:
            return Result.failed
        return Result.success

    def trace_external_link(self, external_link_list: list[ExternalLink]) -> Result:
        # 外部リンク探索
        for external_link in external_link_list:
            url = external_link.external_link_url
            # 過去に取得済かどうか調べる
            if self.db_cont.select_external_link(url) != []:
                logger.debug(url + " : in DB exist -> skip")
                continue
            if self.lsb.can_fetch(url):
                # 外部リンク先を取得して保存
                self.lsb.fetch(url)
                # DBにアドレス情報を保存
                self.db_cont.upsert_external_link([external_link])
        return Result.success

    @abstractmethod
    def crawl(self) -> Result:
        """一連の実行メソッドをまとめる

        Returns:
            Result: 成功時Result.success
        """
        return Result.success


if __name__ == "__main__":
    import media_gathering.fav_crawler as FavCrawler

    c = FavCrawler.FavCrawler()
    c.crawl()
