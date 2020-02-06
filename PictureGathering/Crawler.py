# coding: utf-8
"""クローラー

Fav/Retweetクローラーのベースとなるクローラークラス
API呼び出しなど共通処理はこのクローラークラスに記述する
設定ファイルとして {CONFIG_FILE_NAME} にあるconfig.iniファイルを使用する
"""

import configparser
import json
import logging.config
import os
import random
import sys
import time
import traceback
import urllib
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta, timezone
from logging import DEBUG, INFO, getLogger
from pathlib import Path

import requests
import slackweb
from requests_oauthlib import OAuth1Session

from PictureGathering import DBController, WriteHTML

logging.config.fileConfig("./log/logging.ini")
logger = getLogger("root")
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
        db_cont (DBController): DB操作用クラス実体
        TW_CONSUMER_KEY (str): TwitterAPI利用キー
        TW_CONSUMER_SECRET (str): TwitterAPI利用シークレットキー
        TW_ACCESS_TOKEN_KEY (str): TwitterAPIアクセストークンキー
        TW_ACCESS_TOKEN_SECRET (str): TwitterAPIアクセストークンシークレットキー
        LN_TOKEN_KEY (str): LINE notifyのトークン
        SLACK_WEBHOOK_URL (str): SlackのWebhook URL
        DISCORD_WEBHOOK_URL (str): DiscordのWebhook URL
        user_name (str): Twitterのユーザーネーム
        count (int): 一度に取得するFav/Retweetの数
        save_path (str): 画像保存先パス
        type (str): 継承先を表すタイプ識別{Fav, RT}
        oath (OAuth1Session): TwitterAPI利用セッション
        add_cnt (int): 新規追加した画像の数
        del_cnt (int): 削除した画像の数
        add_url_list (list): 新規追加した画像のURLリスト
        del_url_list (list): 削除した画像のURLリスト
    """

    CONFIG_FILE_NAME = "./config/config.ini"

    def __init__(self):
        self.config = configparser.ConfigParser()
        try:
            self.db_cont = DBController.DBController()
            if not self.config.read(self.CONFIG_FILE_NAME, encoding="utf8"):
                raise IOError

            config = self.config["twitter_token_keys"]
            self.TW_CONSUMER_KEY = config["consumer_key"]
            self.TW_CONSUMER_SECRET = config["consumer_secret"]
            self.TW_ACCESS_TOKEN_KEY = config["access_token"]
            self.TW_ACCESS_TOKEN_SECRET = config["access_token_secret"]

            config = self.config["line_token_keys"]
            self.LN_TOKEN_KEY = config["token_key"]

            config = self.config["slack_webhook_url"]
            self.SLACK_WEBHOOK_URL = config["webhook_url"]

            config = self.config["discord_webhook_url"]
            self.DISCORD_WEBHOOK_URL = config["webhook_url"]

            self.user_name = self.config["tweet_timeline"]["user_name"]
            self.count = int(self.config["tweet_timeline"]["count"])

            self.save_path = ""
            self.type = ""
        except IOError:
            logger.exception(self.CONFIG_FILE_NAME + " is not exist or cannot be opened.")
            exit(-1)
        except KeyError:
            logger.exception("invalid config file eeror.")
            exit(-1)
        except Exception:
            logger.exception("unknown error.")
            exit(-1)

        self.oath = OAuth1Session(
            self.TW_CONSUMER_KEY,
            self.TW_CONSUMER_SECRET,
            self.TW_ACCESS_TOKEN_KEY,
            self.TW_ACCESS_TOKEN_SECRET
        )

        self.add_cnt = 0
        self.del_cnt = 0

        self.add_url_list = []
        self.del_url_list = []

    def GetTwitterAPIResourceType(self, url: str) -> str:
        """使用するTwitterAPIのAPIリソースタイプを返す

        Args:
            url (str): TwitterAPIのエンドポイントURL

        Returns:
            str: APIリソースタイプ
        """

        called_url = urllib.parse.urlparse(url).path
        url = urllib.parse.urljoin(url, os.path.basename(called_url))
        resources = []
        if "users" in url:
            resources.append("users")
        elif "statuses" in url:
            resources.append("statuses")
        elif "favorites" in url:
            resources.append("favorites")
        return ",".join(resources)

    def GetTwitterAPILimitContext(self, res_text: dict, params: dict) -> (int, int):
        """Limitを取得するAPIの返り値を解釈して残数と開放時間を取得する

        Note:
            TwitterAPIリファレンス:rate_limit_status
            http://westplain.sakuraweb.com/translate/twitter/Documentation/REST-APIs/Public-API/GET-application-rate_limit_status.cgi

        Args:
            res_text (dict): TwitterAPI:rate_limit_statusの返り値(json)
            params (dict): TwitterAPI:rate_limit_statusを呼び出したときのパラメータ辞書

        Returns:
            int, int: 残り使用回数, 制限リセット時間(UNIXエポック秒)
        """

        if "resources" not in params:
            return -1, -1  # 引数エラー
        r = params["resources"]

        if r not in res_text["resources"]:
            return -1, -1  # 引数エラー

        for p in res_text["resources"][r].keys():
            # remainingとresetを取得する
            remaining = res_text["resources"][r][p]["remaining"]
            reset = res_text["resources"][r][p]["reset"]
            return int(remaining), int(reset)

    def WaitUntilReset(self, dt_unix: float) -> int:
        """指定UNIX時間まで待機する

        Notes:
            念のため(dt_unix + 10)秒まで待機する

        Args:
            dt_unix (float): UNIX時間の指定

        Returns:
            int: 成功時0
        """

        seconds = dt_unix - time.mktime(datetime.now().timetuple())
        seconds = max(seconds, 0)
        logger.debug('=======================')
        logger.debug('== waiting {} sec =='.format(seconds))
        logger.debug('=======================')
        sys.stdout.flush()
        time.sleep(seconds + 10)  # 念のため + 10 秒
        return 0

    def CheckTwitterAPILimit(self, called_url: str) -> int:
        """TwitterAPI制限を取得する

        Args:
            called_url (str): API制限を取得したいTwitterAPIエンドポイントURL

        Raises:
            Exception: API制限情報を取得するのに503で10回失敗した場合エラー
            Exception: API制限情報取得した結果が200でない場合エラー

        Returns:
            int: 成功時0、このメソッド実行後はcalled_urlのエンドポイントが利用可能であることが保証される
        """

        unavailableCnt = 0
        while True:
            url = "https://api.twitter.com/1.1/application/rate_limit_status.json"
            params = {
                "resources": self.GetTwitterAPIResourceType(called_url)
            }
            responce = self.oath.get(url, params=params)

            if responce.status_code == 503:
                # 503 : Service Unavailable
                if unavailableCnt > 10:
                    raise Exception('Twitter API error %d' % responce.status_code)

                unavailableCnt += 1
                logger.info('Service Unavailable 503')
                self.WaitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
                continue

            unavailableCnt = 0

            if responce.status_code != 200:
                raise Exception('Twitter API error %d' % responce.status_code)

            remaining, reset = self.GetTwitterAPILimitContext(json.loads(responce.text), params)
            if (remaining == 0):
                self.WaitUntilReset(reset)
            else:
                break
        return 0

    def WaitTwitterAPIUntilReset(self, responce: dict) -> int:
        """TwitterAPIが利用できるまで待つ

        Args:
            responce (dict): 利用できるまで待つTwitterAPIを使ったときのレスポンス

        Returns:
            int: 成功時0、このメソッド実行後はresponceに対応するエンドポイントが利用可能であることが保証される
        """

        # X-Rate-Limit-Remaining が入ってないことが稀にあるのでチェック
        if 'X-Rate-Limit-Remaining' in responce.headers and 'X-Rate-Limit-Reset' in responce.headers:
            # 回数制限（ヘッダ参照）
            remain_cnt = int(responce.headers['X-Rate-Limit-Remaining'])
            dt_unix = int(responce.headers['X-Rate-Limit-Reset'])
            dt_jst_aware = datetime.fromtimestamp(dt_unix, timezone(timedelta(hours=9)))
            remain_sec = dt_unix - time.mktime(datetime.now().timetuple())
            logger.debug('リクエストURL {}'.format(responce.url))
            logger.debug('アクセス可能回数 {}'.format(remain_cnt))
            logger.debug('リセット時刻 {}'.format(dt_jst_aware))
            logger.debug('リセットまでの残り時間 %s[s]' % remain_sec)
            if remain_cnt == 0:
                self.WaitUntilReset(dt_unix)
                self.CheckTwitterAPILimit(responce.url)
        else:
            # 回数制限（API参照）
            logger.debug('not found  -  X-Rate-Limit-Remaining or X-Rate-Limit-Reset')
            self.CheckTwitterAPILimit(responce.url)
        return 0

    def TwitterAPIRequest(self, url: str, params: dict) -> dict:
        """TwitterAPIを使用するラッパメソッド

        Args:
            url (str): TwitterAPIエンドポイントURL
            params (dict): TwitterAPI使用時に渡すパラメータ

        Raises:
            Exception: API利用に503で10回失敗した場合エラー
            Exception: API利用結果が200でない場合エラー

        Returns:
            dict: TwitterAPIレスポンス
        """

        unavailableCnt = 0
        while True:
            responce = self.oath.get(url, params=params)

            if responce.status_code == 503:
                # 503 : Service Unavailable
                if unavailableCnt > 10:
                    raise Exception('Twitter API error %d' % responce.status_code)

                unavailableCnt += 1
                logger.info('Service Unavailable 503')
                self.WaitTwitterAPIUntilReset(responce)
                continue
            unavailableCnt = 0

            if responce.status_code != 200:
                raise Exception('Twitter API error %d' % responce.status_code)

            res = json.loads(responce.text)
            return res

    def GetMediaUrl(self, media_dict: dict) -> str:
        """tweet["extended_entities"]["media"]から保存対象のメディアURLを取得する

        Args:
            media_dict (dict): tweet["extended_entities"]["media"]

        Returns:
            str: 成功時メディアURL、引数や辞書構造が不正だった場合空文字列を返す
        """

        media_type = "None"
        if "type" not in media_dict:
            logger.info("メディアタイプが不明です。")
            return ""
        media_type = media_dict["type"]

        url = ""
        if media_type == "photo":
            if "media_url" not in media_dict:
                logger.info("画像を含んでいないツイートです。")
                return ""
            url = media_dict["media_url"]
        elif media_type == "video":
            if "video_info" not in media_dict:
                logger.info("動画を含んでいないツイートです。")
                return ""
            video_variants = media_dict["video_info"]["variants"]
            bitrate = -sys.maxsize  # 最小値
            for video_variant in video_variants:
                if video_variant["content_type"] == "video/mp4":
                    if int(video_variant["bitrate"]) > bitrate:
                        # 同じ動画の中で一番ビットレートが高い動画を保存する
                        url = video_variant["url"]
                        bitrate = int(video_variant["bitrate"])
            # クエリを除去
            url_path = urllib.parse.urlparse(url).path
            url = urllib.parse.urljoin(url, os.path.basename(url_path))
        else:
            logger.info("メディアタイプが不明です。")
            return ""

        return url

    def ImageSaver(self, tweets: dict) -> int:
        """ツイートオブジェクトから画像を保存する

        Args:
            tweets (dict): 画像を含んでいる可能性があるツイートオブジェクト辞書

        Returns:
            int: 正常時0
        """

        for tweet in tweets:
            if "extended_entities" not in tweet:
                logger.debug("メディアを含んでいないツイートです。")
                continue
            if "media" not in tweet["extended_entities"]:
                logger.debug("メディアを含んでいないツイートです。")
                continue
            media_list = tweet["extended_entities"]["media"]

            # 画像つきツイートが投稿された日時を取得する
            # もしcreated_atが不正な形式だった場合、strptimeはValueErrorを返す
            # ex) tweet["created_at"] = "Tue Sep 04 15:55:52 +0000 2012"
            td_format = '%a %b %d %H:%M:%S +0000 %Y'
            created_time = time.strptime(tweet["created_at"], td_format)
            atime = mtime = time.mktime(
                (created_time.tm_year,
                    created_time.tm_mon,
                    created_time.tm_mday,
                    created_time.tm_hour,
                    created_time.tm_min,
                    created_time.tm_sec,
                    0, 0, -1)
            )

            for media_dict in media_list:
                media_type = "None"
                if "type" not in media_dict:
                    logger.debug("メディアタイプが不明です。")
                    continue
                media_type = media_dict["type"]

                url = self.GetMediaUrl(media_dict)
                if url == "":
                    continue

                if media_type == "photo":
                    url_orig = url + ":orig"
                    url_thumbnail = url + ":large"
                    file_name = os.path.basename(url)
                    save_file_path = os.path.join(self.save_path, os.path.basename(url))
                    save_file_fullpath = os.path.abspath(save_file_path)
                elif media_type == "video":
                    url_orig = url
                    url_thumbnail = media_dict["media_url"] + ":orig"  # サムネ
                    file_name = os.path.basename(url_orig)
                    save_file_path = os.path.join(self.save_path, os.path.basename(url_orig))
                    save_file_fullpath = os.path.abspath(save_file_path)
                else:
                    logger.debug("メディアタイプが不明です。")
                    continue

                if not os.path.isfile(save_file_fullpath):
                    # URLから画像を取得してローカルに保存
                    urllib.request.urlretrieve(url_orig, save_file_fullpath)
                    self.add_url_list.append(url_orig)

                    # DB操作
                    if self.type == "Fav":
                        self.db_cont.DBFavUpsert(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath)
                    elif self.type == "RT":
                        self.db_cont.DBRetweetUpsert(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath)

                    # image magickで画像変換
                    if media_type == "photo":
                        img_magick_path = self.config["processes"]["image_magick"]
                        if img_magick_path:
                            os.system('"' + img_magick_path + '" -quality 60 ' +
                                      save_file_fullpath + " " +
                                      save_file_fullpath)

                    # 更新日時を上書き
                    config = self.config["timestamp"]
                    if config.getboolean("timestamp_created_at"):
                        os.utime(save_file_fullpath, (atime, mtime))

                    logger.info(os.path.basename(save_file_fullpath) + " -> done!")
                    self.add_cnt += 1
        return 0

    def GetExistFilelist(self) -> list:
        """self.save_pathに存在するファイル名一覧を取得する

        Returns:
            list: self.save_pathに存在するファイル名一覧
        """

        xs = []
        for root, dir, files in os.walk(self.save_path):
            for f in files:
                path = os.path.join(root, f)
                xs.append((os.path.getmtime(path), path))
        os.walk(self.save_path).close()

        filelist = []
        for mtime, path in sorted(xs, reverse=True):
            filelist.append(path)
        return filelist

    def ShrinkFolder(self, holding_file_num: int) -> int:
        """フォルダ内ファイルの数を一定にする

        Args:
            holding_file_num (int): フォルダ内に残すファイルの数

        Returns:
            int: 成功時0
        """

        filelist = self.GetExistFilelist()

        # フォルダに既に保存しているファイルにはURLの情報がない
        # ファイル名とドメインを結びつけてURLを手動で生成する
        # twitterの画像URLの仕様が変わったらここも変える必要がある
        # http://pbs.twimg.com/media/{file.basename}.jpg:orig
        # 動画ファイルのURLはDBに問い合わせる
        add_img_filename = []
        for i, file in enumerate(filelist):
            url = ""
            if ".mp4" in file:  # media_type == "video":
                url = self.GetVideoURL(os.path.basename(file))
            else:  # media_type == "photo":
                image_base_url = 'http://pbs.twimg.com/media/{}:orig'
                url = image_base_url.format(os.path.basename(file))

            if i > holding_file_num:
                os.remove(file)
                self.del_cnt += 1
                self.del_url_list.append(url)
            else:
                # self.add_url_list.append(url)
                add_img_filename.append(os.path.basename(file))

        # 存在マーキングを更新する
        self.UpdateDBExistMark(add_img_filename)

        return 0

    @abstractmethod
    def UpdateDBExistMark(self, add_img_filename: list):
        """存在マーキングを更新する

        Args:
            add_img_filename (list): 保存したメディアのアドレスリスト
        """

        pass

    @abstractmethod
    def GetVideoURL(self, file_name: str) -> str:
        """動画ファイルのURLをDBに問い合わせる

        Args:
            file_name (str): 動画ファイル名

        Returns:
            str: 成功時動画ファイルURL、失敗時空文字列
        """

        pass

    @abstractmethod
    def MakeDoneMessage(self) -> str:
        """実行後の結果文字列を生成する
        """

        pass

    def EndOfProcess(self) -> int:
        """実行後の後処理

        Returns:
            int: 成功時0
        """

        logger.info("")

        done_msg = self.MakeDoneMessage()

        logger.info(done_msg)

        config = self.config["notification"]

        WriteHTML.WriteResultHTML(self.type, self.del_url_list)
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
                self.PostTweet(done_msg)
                logger.info("Reply posted.")

            if self.type == "RT" and config.getboolean("is_post_retweet_done_reply"):
                self.PostTweet(done_msg)
                logger.info("Reply posted.")

            if config.getboolean("is_post_line_notify"):
                self.PostLineNotify(done_msg)
                logger.info("Line Notify posted.")

            if config.getboolean("is_post_discord_notify"):
                self.PostDiscordNotify(done_msg)
                logger.info("Discord Notify posted.")

            if config.getboolean("is_post_slack_notify"):
                self.PostSlackNotify(done_msg)
                logger.info("Slack Notify posted.")

        # 古い通知リプライを消す
        if config.getboolean("is_post_fav_done_reply") or config.getboolean("is_post_retweet_done_reply"):
            targets = self.db_cont.DBDelSelect()
            url = "https://api.twitter.com/1.1/statuses/destroy/{}.json"
            for target in targets:
                responce = self.oath.post(url.format(target["tweet_id"]))  # tweet_id

        return 0

    def PostTweet(self, str: str) -> int:
        """実行完了ツイートをポストする

        Args:
            str (str): ポストする文字列

        Returns:
            int: 成功時0、失敗時None
        """

        url = "https://api.twitter.com/1.1/users/show.json"
        reply_user_name = self.config["notification"]["reply_to_user_name"]
        random_pickup = False  # 自分がアップロードしたことになるのでメディア欄が侵食されるためオフに

        params = {
            "screen_name": reply_user_name,
        }
        res = self.TwitterAPIRequest(url, params=params)
        if res is None:
            return None

        # 画像をランダムにピックアップしてアップロードする
        media_ids = ""
        if random_pickup:
            url = "https://upload.twitter.com/1.1/media/upload.json"

            pickup_url_list = random.sample(self.add_url_list, 4)
            for pickup_url in pickup_url_list:
                files = {
                    "media": urllib.request.urlopen(pickup_url).read()
                }
                responce = self.oath.post(url, files=files)

                if responce.status_code != 200:
                    logger.error("Error code: {0}".format(responce.status_code))
                    return None

                media_id = json.loads(responce.text)['media_id']
                media_id_string = json.loads(responce.text)['media_id_string']
                logger.debug("Media ID: {} ".format(media_id))

                # メディアIDの文字列をカンマ","で結合
                if media_ids == "":
                    media_ids += media_id_string
                else:
                    media_ids = media_ids + "," + media_id_string

        url = "https://api.twitter.com/1.1/statuses/update.json"
        reply_to_status_id = res["id_str"]

        str = "@" + reply_user_name + " " + str

        params = {
            "status": str,
            "in_reply_to_status_id": reply_to_status_id,
        }

        # 画像つきツイートの場合
        if media_ids != "":
            # メディアID（カンマ区切り）をパラメータに含める
            params["media_ids"] = media_ids

        responce = self.oath.post(url, params=params)
        logger.debug(responce.text)
        self.db_cont.DBDelInsert(json.loads(responce.text))

        if responce.status_code != 200:
            logger.error("Error code: {0}".format(responce.status_code))
            return None

        return 0

    def PostLineNotify(self, str: str) -> int:
        """LINE通知ポスト

        Args:
            str (str): LINEに通知する文字列

        Returns:
            int: 成功時0
        """

        url = "https://notify-api.line.me/api/notify"
        token = self.LN_TOKEN_KEY

        headers = {"Authorization": "Bearer " + token}
        payload = {"message": str}

        responce = requests.post(url, headers=headers, params=payload)

        if responce.status_code != 200:
            logger.error("Error code: {0}".format(responce.status_code))
            return None

        return 0

    def PostSlackNotify(self, str: str) -> int:
        """Slack通知ポスト

        Args:
            str (str): Slackに通知する文字列

        Returns:
            int: 成功時0
        """

        try:
            slack = slackweb.Slack(url=self.SLACK_WEBHOOK_URL)
            slack.notify(text="<!here> " + str)
        except ValueError:
            logger.error("Webhook URL error: {0} is invalid".format(self.SLACK_WEBHOOK_URL))
            return None

        return 0

    def PostDiscordNotify(self, str: str) -> int:
        """Discord通知ポスト

        Args:
            str (str): Discordに通知する文字列

        Returns:
            int: 成功時0
        """

        url = self.DISCORD_WEBHOOK_URL

        headers = {
            "Content-Type": "application/json"
        }

        # "content": "😎普通の絵文字\r:sunglasses:Discordの絵文字も:ok_woman:"
        payload = {
            "content": str
        }

        responce = requests.post(url, headers=headers, data=json.dumps(payload))

        if responce.status_code != 204:  # 成功すると204 No Contentが返ってくる
            logger.error("Error code: {0}".format(responce.status_code))
            return None

        return 0

    @abstractmethod
    def Crawl(self) -> int:
        """一連の実行メソッドをまとめる

        Returns:
            int: 成功時0
        """

        return 0


if __name__ == "__main__":
    import FavCrawler as FavCrawler
    c = FavCrawler.FavCrawler()
    c.Crawl()
