# coding: utf-8
"""クローラー

Fav/Retweetクローラーのベースとなるクローラークラス
設定ファイルとして {CONFIG_FILE_NAME} にあるconfig.iniファイルを使用する
"""
import configparser
import json
import logging.config
import os
import shutil
import ssl
import time
import urllib
from abc import ABCMeta, abstractmethod
from datetime import datetime
from logging import INFO, getLogger
from pathlib import Path

import certifi
import requests
from plyer import notification
from slack_sdk.webhook import WebhookClient

from PictureGathering import Archiver, GoogleDrive, WriteHTML
from PictureGathering.DBControllerBase import DBControllerBase
from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.LogMessage import MSG
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.TweetInfo import TweetInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI
from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    # 自分以外のすべてのライブラリのログ出力を抑制
    if "PictureGathering" not in name:
        getLogger(name).disabled = True
logger = getLogger(__name__)
logger.setLevel(INFO)


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
        TW_V2_API_KEY (str): TwitterAPI_v2利用APIキー
        TW_V2_API_KEY_SECRET (str): TwitterAPI_v2利用APIシークレットキー
        TW_V2_ACCESS_TOKEN (str): TwitterAPI_v2アクセストークンキー
        TW_V2_ACCESS_TOKEN_SECRET (str): TwitterAPI_v2アクセストークンシークレットキー
        DISCORD_WEBHOOK_URL (str): DiscordのWebhook URL
        LN_TOKEN_KEY (str): LINE notifyのトークン
        SLACK_WEBHOOK_URL (str): SlackのWebhook URL
        twitter (TwitterAPI): TwitterAPI利用クラス
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

    def __init__(self):
        logger.info(MSG.CRAWLER_INIT_START.value)

        def notify(error_message: str):
            notification.notify(
                title="Picture Gathering 実行エラー",
                message=error_message,
                app_name="Picture Gathering",
                timeout=10
            )

        self.config = configparser.ConfigParser()
        try:
            if not self.config.read(self.CONFIG_FILE_NAME, encoding="utf8"):
                raise IOError

            config = self.config["save_directory"]
            Path(config["save_fav_path"]).mkdir(parents=True, exist_ok=True)
            Path(config["save_retweet_path"]).mkdir(parents=True, exist_ok=True)

            if not self.config["twitter_noapi"].getboolean("is_twitter_noapi"):
                config = self.config["twitter_token_keys_v2"]
                self.TW_V2_API_KEY = config["api_key"]
                self.TW_V2_API_KEY_SECRET = config["api_key_secret"]
                self.TW_V2_ACCESS_TOKEN = config["access_token"]
                self.TW_V2_ACCESS_TOKEN_SECRET = config["access_token_secret"]
                self.twitter = TwitterAPI(
                    self.TW_V2_API_KEY,
                    self.TW_V2_API_KEY_SECRET,
                    self.TW_V2_ACCESS_TOKEN,
                    self.TW_V2_ACCESS_TOKEN_SECRET
                )
            else:
                self.twitter = None

            config = self.config["discord_webhook_url"]
            self.DISCORD_WEBHOOK_URL = config["webhook_url"]

            config = self.config["line_token_keys"]
            self.LN_TOKEN_KEY = config["token_key"]

            config = self.config["slack_webhook_url"]
            self.SLACK_WEBHOOK_URL = config["webhook_url"]

            # 外部リンク探索機構のセットアップ
            self.link_search_register()
        except IOError:
            error_message = self.CONFIG_FILE_NAME + " is not exist or cannot be opened."
            logger.exception(error_message)
            notify(error_message)
            exit(-1)
        except KeyError:
            error_message = "invalid config file error."
            logger.exception(error_message)
            notify(error_message)
            exit(-1)
        except ValueError as e:
            error_message = "Twitter API setup error."
            logger.exception(e)
            notify(error_message)
            exit(-1)
        except Exception:
            error_message = "unknown error."
            logger.exception(error_message)
            notify(error_message)
            exit(-1)

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

    def link_search_register(self) -> int:
        """外部リンク探索機構のセットアップ

        Notes:
            self.lsbに設定する

        Returns:
            int: 成功時0
        """
        # 外部リンク探索を登録
        self.lsb = LinkSearcher.create(self.config)
        return 0

    def get_exist_filelist(self) -> list:
        """self.save_pathに存在するファイル名一覧を取得する

        Returns:
            list: self.save_pathに存在するファイル名一覧
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

    def shrink_folder(self, holding_file_num: int) -> int:
        """フォルダ内ファイルの数を一定にする

        Args:
            holding_file_num (int): フォルダ内に残すファイルの数

        Returns:
            int: 0(成功)
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

        return 0

    def update_db_exist_mark(self, add_img_filename):
        # 存在マーキングを更新する
        self.db_cont.clear_flag()
        self.db_cont.update_flag(add_img_filename, 1)

    def get_media_url(self, filename):
        # 'https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/b0ZDq8zG_HppFWb6.mp4?tag=10'
        response = self.db_cont.select_from_media_url(filename)
        url = response[0]["url"] if len(response) == 1 else ""
        return url

    @abstractmethod
    def make_done_message(self) -> str:
        """実行後の結果文字列を生成する
        """
        pass

    def end_of_process(self) -> int:
        """実行後の後処理

        Returns:
            int: 成功時0
        """
        logger.info("")

        done_msg = self.make_done_message()

        logger.info("\t".join(done_msg.splitlines()))

        config = self.config["notification"]

        WriteHTML.WriteResultHTML(self.type, self.db_cont)
        if self.add_cnt != 0 or self.del_cnt != 0:
            if self.add_cnt != 0:
                logger.info("add url:")
                for url in self.add_url_list:
                    logger.info(url)

            if self.del_cnt != 0:
                logger.info("del url:")
                for url in self.del_url_list:
                    logger.info(url)

            if self.type == "Fav" and config.getboolean("is_post_fav_done_reply"):
                self.post_tweet(done_msg)
                logger.info("Reply posted.")

            if self.type == "RT" and config.getboolean("is_post_retweet_done_reply"):
                self.post_tweet(done_msg)
                logger.info("Reply posted.")

            if config.getboolean("is_post_discord_notify"):
                self.post_discord_notify(done_msg)
                logger.info("Discord Notify posted.")

            if config.getboolean("is_post_line_notify"):
                self.post_line_notify(done_msg)
                logger.info("Line Notify posted.")

            if config.getboolean("is_post_slack_notify"):
                self.post_slack_notify(done_msg)
                logger.info("Slack Notify posted.")

            # アーカイブする設定の場合
            config = self.config["archive"]
            if config.getboolean("is_archive"):
                zipfile_path = Archiver.MakeZipFile(config.get("archive_temp_path"), self.type)
                logger.info("Archive File Created.")
                if config.getboolean("is_send_google_drive") and zipfile_path != "":
                    GoogleDrive.UploadToGoogleDrive(zipfile_path, config.get("google_service_account_credentials"))
                    logger.info("Google Drive Send.")

        # 古い通知リプライを消す
        config = self.config["notification"]
        if config.getboolean("is_post_fav_done_reply") or config.getboolean("is_post_retweet_done_reply"):
            targets = self.db_cont.update_del()
            for target in targets:
                tweet_id = target.get("tweet_id")
                url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.DELETE_TWEET, tweet_id)
                response = self.twitter.delete(url)

        logger.info("End Of " + self.type + " Crawl Process.")
        return 0

    def post_tweet(self, tweet_str: str) -> int:
        """実行完了ツイートをポストする

        Args:
            str (str): ポストする文字列

        Returns:
            int: 成功時0、失敗時-1
        """
        reply_user_name = self.config["notification"]["reply_to_user_name"]
        url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.POST_TWEET)

        tweet_str = "@" + reply_user_name + " " + tweet_str
        params = {
            "text": tweet_str,
        }

        response = self.twitter.post(url, params)
        if not response:
            logger.error("post_tweet failed.")
            return -1

        # 削除用DBにUPSERTする
        # レスポンスは以下の形で返ってくる
        # {
        #     "data": {
        #         "id": {id},
        #         "text": {tweet_str}
        #     }
        # }
        tweet = response
        self.db_cont.upsert_del(tweet)

        return 0

    def post_discord_notify(self, str: str) -> int:
        """Discord通知ポスト

        Args:
            str (str): Discordに通知する文字列

        Returns:
            int: 0(成功)
        """
        url = self.DISCORD_WEBHOOK_URL

        headers = {
            "Content-Type": "application/json"
        }

        payload = {}
        is_embed = True
        if is_embed:
            # desc_msg = """Retweet PictureGathering run.
            # 2023/02/03 10:31:30 Process Done !!
            # add 4 new images. delete 4 old images."""
            # """https://pbs.twimg.com/media/Fn-iG41aYAAjYb7.jpg
            # https://pbs.twimg.com/media/Fn_OTxhXEAIMyb0.jpg
            # https://pbs.twimg.com/media/Fn4DUHSaIAM8Ehz.jpg
            # https://pbs.twimg.com/media/Fn-2N4UagAAlzEd.jpg"""

            description_msg = ""
            media_links = []
            lines = str.split("\n")
            for line in lines:
                if line.startswith("http"):
                    media_links.append(line)
                else:
                    description_msg += (line + "\n")
         
            embeds = []
            if len(media_links) > 0:
                key_url = media_links[0]
                embeds.append(
                    {
                        "description": description_msg,
                        "url": key_url,
                        "image": {"url": key_url}
                    }
                )
                for media_link_url in media_links[1:]:
                    embeds.append(
                        {
                            "url": key_url,
                            "image": {"url": media_link_url}
                        }
                    )

            if embeds:
                payload = {
                    "embeds": embeds
                }

        if not payload:
            payload = {
                "content": str
            }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code != 204:  # 成功すると204 No Contentが返ってくる
            logger.error("Error code: {0}".format(response.status_code))
            return -1

        return 0

    def post_line_notify(self, str: str) -> int:
        """LINE通知ポスト

        Args:
            str (str): LINEに通知する文字列

        Returns:
            int: 0(成功)
        """
        url = "https://notify-api.line.me/api/notify"
        token = self.LN_TOKEN_KEY

        headers = {"Authorization": "Bearer " + token}
        payload = {"message": str}

        response = requests.post(url, headers=headers, params=payload)

        if response.status_code != 200:
            logger.error("Error code: {0}".format(response.status_code))
            return -1

        return 0

    def post_slack_notify(self, str: str) -> int:
        """Slack通知ポスト

        Args:
            str (str): Slackに通知する文字列

        Returns:
            int: 0(成功)
        """
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        webhook = WebhookClient(self.SLACK_WEBHOOK_URL, ssl=ssl_context)
        post_text = "<!here> " + str
        response = webhook.send(text=post_text)
        if response.status_code != 200:
            logger.error("Error code: {0}".format(response.status_code))
            return -1
        return 0

    def tweet_media_saver_v2(self, tweet_info: TweetInfo, atime: float, mtime: float) -> int:
        """指定URLのメディアを保存する

        Args:
            tweet_info (TweetInfo): メディア含むツイート情報
            atime (float): 指定更新日時
            mtime (float): 指定更新日時

        Returns:
            int: 成功時0、既に存在しているメディアだった場合1、過去に取得済のメディアだった場合2、
                 失敗時（メディア辞書構造がエラー、urlが取得できない）-1
        """
        url_orig = tweet_info.media_url
        url_thumbnail = tweet_info.media_thumbnail_url
        file_name = tweet_info.media_filename
        save_file_path = Path(self.save_path) / file_name
        save_file_fullpath = save_file_path.absolute()

        # 過去に取得済かどうか調べる
        if self.db_cont.select_from_media_url(file_name) != []:
            logger.debug(save_file_fullpath.name + " -> skip")
            return 2

        if not save_file_fullpath.is_file():
            # URLからメディアを取得してローカルに保存
            # タイムアウトを設定するためにurlopenを利用
            # urllib.request.urlretrieve(url_orig, save_file_fullpath)
            try:
                data = urllib.request.urlopen(url_orig, timeout=60).read()
                with save_file_fullpath.open(mode="wb") as f:
                    f.write(data)
            except Exception:
                # URLからのメディア取得に失敗
                # 削除されていた場合など
                logger.info(save_file_fullpath.name + " -> failed.")
                return -1
            self.add_url_list.append(url_orig)

            # DB操作
            # db_cont.upsert_v2派生クラスによって呼び分けられる
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
            include_blob = self.config["db"].getboolean("save_blob")
            try:
                if include_blob:
                    with open(save_file_fullpath, "rb") as fout:
                        params["media_blob"] = fout.read()
                        params["media_size"] = len(params["media_blob"])
                else:
                    params["media_blob"] = None
                    params["media_size"] = Path(save_file_fullpath).stat().st_size
            except Exception:
                params["media_blob"] = None
                params["media_size"] = -1
            self.db_cont.upsert(params)

            # 更新日時を上書き
            config = self.config["timestamp"]
            if config.getboolean("timestamp_created_at"):
                os.utime(save_file_fullpath, (atime, mtime))

            # ログ書き出し
            logger.info(save_file_fullpath.name + " -> done")
            self.add_cnt += 1

            # 常に保存する設定の場合はコピーする
            config = self.config["db"]
            if config.getboolean("save_permanent_image_flag"):
                shutil.copy2(save_file_fullpath, config["save_permanent_image_path"])

            # アーカイブする設定の場合
            config = self.config["archive"]
            if config.getboolean("is_archive"):
                shutil.copy2(save_file_fullpath, config["archive_temp_path"])
        else:
            # 既に存在している場合
            logger.debug(save_file_fullpath.name + " -> exist")
            return 1
        return 0

    def interpret_tweets_v2(self, tweet_info_list: list[TweetInfo]) -> None:
        for tweet_info in tweet_info_list:
            """タイムスタンプについて
                https://srbrnote.work/archives/4054
                作成日時:ctime, 更新日時:mtime, アクセス日時:atimeがある
                ctimeはOS依存のため設定には外部ライブラリが必要
                ここでは
                    Favならばatime=mtime=ツイート投稿日時 とする
                    RTならばatime=mtime=ツイート投稿日時 とする
                    （IS_APPLY_NOW_TIMESTAMP == Trueならば収集時の時刻 とする？）
                収集されたツイートの投稿日時はDBのcreated_at項目に保持される
            """
            IS_APPLY_NOW_TIMESTAMP = False
            atime = mtime = -1
            if IS_APPLY_NOW_TIMESTAMP:
                atime = mtime = time.time()
            else:
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

            # メディア保存
            self.tweet_media_saver_v2(tweet_info, atime, mtime)

    def trace_external_link(self, external_link_list: list[ExternalLink]) -> None:
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

    @abstractmethod
    def crawl(self) -> int:
        """一連の実行メソッドをまとめる

        Returns:
            int: 0(成功)
        """
        return 0


if __name__ == "__main__":
    import PictureGathering.FavCrawler as FavCrawler
    c = FavCrawler.FavCrawler()
    c.crawl()
