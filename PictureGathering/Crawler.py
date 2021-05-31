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
import shutil
import sys
import time
import urllib
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta, timezone
from logging import DEBUG, INFO, getLogger
from pathlib import Path
from typing import List

import requests
import slackweb
from requests_oauthlib import OAuth1Session

from PictureGathering import WriteHTML, Archiver, GoogleDrive
from PictureGathering import LinkSearchBase, LSPixiv, LSNijie, LSNicoSeiga

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
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
        db_cont (DBControllerBase): DB操作用クラス（実態はCrawler派生クラスで規定）
        lsb (LinkSearchBase): 外部リンク探索機構ベースクラス
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
            if not self.config.read(self.CONFIG_FILE_NAME, encoding="utf8"):
                raise IOError

            config = self.config["save_directory"]
            Path(config["save_fav_path"]).mkdir(parents=True, exist_ok=True)
            Path(config["save_retweet_path"]).mkdir(parents=True, exist_ok=True)

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

            self.save_path = Path()
            self.type = ""

            # 情報保持DBコントローラー（派生クラスで実体が代入される）
            self.db_cont = None

            # 外部リンク探索機構のセットアップ
            self.LinkSearchRegister()
        except IOError:
            logger.exception(self.CONFIG_FILE_NAME + " is not exist or cannot be opened.")
            exit(-1)
        except KeyError:
            logger.exception("invalid config file error.")
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

    def LinkSearchRegister(self) -> int:
        """外部リンク探索機構のセットアップ

        Notes:
            self.lsbに設定する

        Returns:
            int: 成功時0
        """
        # 外部リンク探索を登録
        self.lsb = LinkSearchBase.LinkSearchBase()
        # pixivURLを処理する担当者を登録
        config = self.config["pixiv"]
        if config.getboolean("is_pixiv_trace"):
            lsp = LSPixiv.LSPixiv(config["username"], config["password"], config["save_base_path"])
            self.lsb.Register(lsp)

        # nijieURLを処理する担当者を登録
        config = self.config["nijie"]
        if config.getboolean("is_nijie_trace"):
            lsn = LSNijie.LSNijie(config["email"], config["password"], config["save_base_path"])
            self.lsb.Register(lsn)

        # ニコニコ静画のURLを処理する担当者を登録
        config = self.config["nico_seiga"]
        if config.getboolean("is_seiga_trace"):
            lsns = LSNicoSeiga.LSNicoSeiga(config["email"], config["password"], config["save_base_path"])
            self.lsb.Register(lsns)

    def GetTwitterAPIResourceType(self, url: str) -> str:
        """使用するTwitterAPIのAPIリソースタイプを返す

        Args:
            url (str): TwitterAPIのエンドポイントURL

        Returns:
            str: APIリソースタイプ
        """
        called_url = Path(urllib.parse.urlparse(url).path)
        url = urllib.parse.urljoin(url, called_url.name)
        resources = []
        if "users" in url:
            resources.append("users")
        elif "statuses" in url:
            resources.append("statuses")
        elif "favorites" in url:
            resources.append("favorites")
        return ",".join(resources)

    def GetTwitterAPILimitContext(self, res_text: dict, params: dict) -> tuple[int, int]:
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
        logger.debug("=======================")
        logger.debug("=== waiting {} sec ===".format(seconds))
        logger.debug("=======================")
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
            response = self.oath.get(url, params=params)

            if response.status_code == 503:
                # 503 : Service Unavailable
                if unavailableCnt > 10:
                    raise Exception("Twitter API error %d" % response.status_code)

                unavailableCnt += 1
                logger.info("Service Unavailable 503")
                self.WaitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
                continue

            unavailableCnt = 0

            if response.status_code != 200:
                raise Exception("Twitter API error %d" % response.status_code)

            remaining, reset = self.GetTwitterAPILimitContext(json.loads(response.text), params)
            if (remaining == 0):
                self.WaitUntilReset(reset)
            else:
                break
        return 0

    def WaitTwitterAPIUntilReset(self, response: dict) -> int:
        """TwitterAPIが利用できるまで待つ

        Args:
            response (dict): 利用できるまで待つTwitterAPIを使ったときのレスポンス

        Returns:
            int: 成功時0、このメソッド実行後はresponseに対応するエンドポイントが利用可能であることが保証される
        """
        # X-Rate-Limit-Remaining が入ってないことが稀にあるのでチェック
        if "X-Rate-Limit-Remaining" in response.headers and "X-Rate-Limit-Reset" in response.headers:
            # 回数制限（ヘッダ参照）
            remain_cnt = int(response.headers["X-Rate-Limit-Remaining"])
            dt_unix = int(response.headers["X-Rate-Limit-Reset"])
            dt_jst_aware = datetime.fromtimestamp(dt_unix, timezone(timedelta(hours=9)))
            remain_sec = dt_unix - time.mktime(datetime.now().timetuple())
            logger.debug("リクエストURL {}".format(response.url))
            logger.debug("アクセス可能回数 {}".format(remain_cnt))
            logger.debug("リセット時刻 {}".format(dt_jst_aware))
            logger.debug("リセットまでの残り時間 {}[s]".format(remain_sec))
            if remain_cnt == 0:
                self.WaitUntilReset(dt_unix)
                self.CheckTwitterAPILimit(response.url)
        else:
            # 回数制限（API参照）
            logger.debug("not found  -  X-Rate-Limit-Remaining or X-Rate-Limit-Reset")
            self.CheckTwitterAPILimit(response.url)
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
            response = self.oath.get(url, params=params)

            if response.status_code == 503:
                # 503 : Service Unavailable
                if unavailableCnt > 10:
                    raise Exception("Twitter API error %d" % response.status_code)

                unavailableCnt += 1
                logger.info("Service Unavailable 503")
                self.WaitTwitterAPIUntilReset(response)
                continue
            unavailableCnt = 0

            if response.status_code != 200:
                raise Exception("Twitter API error %d" % response.status_code)

            res = json.loads(response.text)
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
        elif media_type == "video" or media_type == "animated_gif":
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
            url_path = Path(urllib.parse.urlparse(url).path)
            url = urllib.parse.urljoin(url, url_path.name)
        else:
            logger.info("メディアタイプが不明です。")
            return ""
        return url

    def GetMediaTweet(self, tweet: dict, id_str_list: list = None) -> List[dict]:
        """ツイートオブジェクトの階層（RT、引用RTの親子関係）をたどり、ツイートがメディアを含むかどうか調べる

        Note:
           ツイートオブジェクトのルートを引数として受け取り、以下のようにresultを返す
           (1)tweetにメディアが添付されている場合、resultにtweetを追加
           (2)tweetに外部リンクが含まれている場合、resultにtweetを追加
           (3)RTされているツイートの場合、resultにtweet["retweeted_status"]とtweetを追加
           (4)引用RTされているツイートの場合、resultにtweet["quoted_status"]とtweetを追加
           (5)引用RTがRTされているツイートの場合、
              resultにtweet["retweeted_status"]["quoted_status"]とtweet["retweeted_status"]とtweetを追加

           引用RTはRTできるがRTは引用RTできないので無限ループにはならない（最大深さ2）
           id_strが重複しているツイートは格納しない
           最終的な返り値となる辞書リストは、タイムスタンプ順に昇順ソートされている
           （昔  RT先ツイート(=A) → （存在するならば）(A)を引用RTしたツイート(=B) → (AまたはB)をRTしたツイート  直近）

        Args:
            tweet (dict): ツイートオブジェクトのルート
            id_str_list (list[str]): 格納済みツイートのid_strリスト

        Returns:
            list[dict]: 上記にて出力された辞書リスト
        """
        result = []

        # デフォルト引数の処理
        if id_str_list is None:
            id_str_list = []
            id_str_list.append(None)

        # ツイートオブジェクトにRTフラグが立っている場合
        if tweet.get("retweeted") and tweet.get("retweeted_status"):
            retweeted_tweet = tweet.get("retweeted_status", {})
            if retweeted_tweet.get("extended_entities"):
                if retweeted_tweet.get("id_str") not in id_str_list:
                    result.append(retweeted_tweet)
                    id_str_list.append(retweeted_tweet.get("id_str"))
                    result.append(tweet)
                    id_str_list.append(tweet.get("id_str"))
            # リツイートオブジェクトに引用RTフラグも立っている場合
            if retweeted_tweet.get("is_quote_status") and retweeted_tweet.get("quoted_status"):
                quoted_tweet = retweeted_tweet.get("quoted_status", {})
                if quoted_tweet.get("extended_entities"):
                    if quoted_tweet.get("id_str") not in id_str_list:
                        result = result + self.GetMediaTweet(retweeted_tweet, id_str_list)
                        result.append(tweet)
                        id_str_list.append(tweet.get("id_str"))
        # ツイートオブジェクトに引用RTフラグが立っている場合
        elif tweet.get("is_quote_status") and tweet.get("quoted_status"):
            quoted_tweet = tweet.get("quoted_status", {})
            if quoted_tweet.get("extended_entities"):
                if quoted_tweet.get("id_str") not in id_str_list:
                    result.append(quoted_tweet)
                    id_str_list.append(quoted_tweet.get("id_str"))
                    result.append(tweet)
                    id_str_list.append(tweet.get("id_str"))
            # ツイートオブジェクトにRTフラグも立っている場合（仕様上、本来はここはいらない）
            if quoted_tweet.get("retweeted") and quoted_tweet.get("retweeted_status"):
                retweeted_tweet = quoted_tweet.get("retweeted_status", {})
                if retweeted_tweet.get("extended_entities"):
                    if retweeted_tweet.get("id_str") not in id_str_list:
                        result = result + self.GetMediaTweet(quoted_tweet, id_str_list)
                        result.append(tweet)
                        id_str_list.append(tweet.get("id_str"))

        # ツイートオブジェクトにメディアがある場合
        if tweet.get("extended_entities", {}).get("media"):
            if tweet.get("id_str") not in id_str_list:
                result.append(tweet)
                id_str_list.append(tweet.get("id_str"))

        # ツイートに外部リンクが含まれている場合
        if tweet.get("entities", {}).get("urls"):
            urls = tweet.get("entities", {}).get("urls", [{}])
            url = urls[0].get("expanded_url")
            # 外部リンク探索が登録されている場合CoRで調べる
            if self.lsb.CoRProcessCheck(url):
                if tweet.get("id_str") not in id_str_list:
                    result.append(tweet)
                    id_str_list.append(tweet.get("id_str"))

        return result

    def TweetMediaSaver(self, tweet: dict, media_dict: dict, atime: float, mtime: float) -> int:
        """指定URLの画像を保存する

        Args:
            tweet (dict): メディア含むツイート（全体）
            media_dict (dict): tweet["extended_entities"]["media"]
            atime (float): 指定更新日時
            mtime (float): 指定更新日時

        Returns:
            int: 成功時0、既に存在しているメディアだった場合1、
                 失敗時（メディア辞書構造がエラー、urlが取得できない）-1
        """
        media_type = "None"
        if "type" not in media_dict:
            logger.debug("メディアタイプが不明です。")
            return -1
        media_type = media_dict["type"]

        url = self.GetMediaUrl(media_dict)
        if url == "":
            logger.debug("urlが不正です。")
            return -1

        if media_type == "photo":
            url_orig = url + ":orig"
            url_thumbnail = url + ":large"
            file_name = Path(url).name
            save_file_path = Path(self.save_path) / file_name
            save_file_fullpath = save_file_path.absolute()
        elif media_type == "video" or media_type == "animated_gif":
            url_orig = url
            url_thumbnail = media_dict["media_url"] + ":orig"  # サムネ
            file_name = Path(url_orig).name
            save_file_path = Path(self.save_path) / file_name
            save_file_fullpath = save_file_path.absolute()
        else:
            logger.debug("メディアタイプが不明です。")
            return -1

        if not save_file_fullpath.is_file():
            # URLから画像を取得してローカルに保存
            # タイムアウトを設定するためにurlopenを利用
            # urllib.request.urlretrieve(url_orig, save_file_fullpath)
            data = urllib.request.urlopen(url_orig, timeout=60).read()
            with save_file_fullpath.open(mode="wb") as f:
                f.write(data)
            self.add_url_list.append(url_orig)

            # DB操作
            # db_cont.Upsert派生クラスによって呼び分けられる（ポリモーフィズム）
            include_blob = self.config["db"].getboolean("save_blob")
            self.db_cont.Upsert(file_name, url_orig, url_thumbnail, tweet, str(save_file_fullpath), include_blob)

            # image magickで画像変換
            if media_type == "photo":
                img_magick_path = Path(self.config["processes"]["image_magick"])
                if img_magick_path.is_file():
                    os.system('"' + str(img_magick_path) + '" -quality 60 ' + str(save_file_fullpath) + " " + str(save_file_fullpath))

            # 更新日時を上書き
            config = self.config["timestamp"]
            if config.getboolean("timestamp_created_at"):
                os.utime(save_file_fullpath, (atime, mtime))

            logger.info(save_file_fullpath.name + " -> done!")
            self.add_cnt += 1

            # 画像を常に保存する設定の場合はコピーする
            config = self.config["db"]
            if config.getboolean("save_permanent_image_flag"):
                shutil.copy2(save_file_fullpath, config["save_permanent_image_path"])

            # 画像をアーカイブする設定の場合
            config = self.config["archive"]
            if config.getboolean("is_archive"):
                shutil.copy2(save_file_fullpath, config["archive_temp_path"])
        else:
            logger.info(save_file_fullpath.name + " -> exist")
            return 1
        return 0

    def InterpretTweets(self, tweets: List[dict]) -> int:
        """ツイートオブジェクトを解釈してメディアURLを取得して保存する

        Note:
            ツイートオブジェクトのメディアを保存する機能はTweetMediaSaverが担う
            外部リンクが含まれている場合の処理はself.lsbが担う

        Args:
            tweets (list[dict]): メディアを含んでいる可能性があるツイートオブジェクト辞書配列

        Returns:
            int: 0(成功)
        """
        for tweet in tweets:
            # メディアツイートツリーを取得
            media_tweets = self.GetMediaTweet(tweet)

            if not media_tweets:
                continue

            """タイムスタンプについて
                https://srbrnote.work/archives/4054
                作成日時:ctime, 更新日時:mtime, アクセス日時:atimeがある
                ctimeはOS依存のため設定には外部ライブラリが必要
                ここでは
                    Favならばatime=mtime=ツイート投稿日時 とする
                    RTならばatime=mtime=ツイート投稿日時 とする
                    （THINK is_apply_now_timestamp == Trueならば収集時の時刻 となる）
                収集されたツイートの投稿日時はDBのcreated_at項目に保持される

                引用RTなどのツリーで関係ツイートが複数ある場合は最新の日時を一律付与する
                もしcreated_atが不正な形式だった場合、strptimeはValueErrorを返す
                ex) tweet["created_at"] = "Tue Sep 04 15:55:52 +0000 2012"
            """
            # is_apply_now_timestamp = (self.type == "Fav")
            is_apply_now_timestamp = False
            atime = mtime = -1
            if is_apply_now_timestamp:
                atime = mtime = time.time()
            else:
                td_format = "%a %b %d %H:%M:%S +0000 %Y"
                mt = media_tweets[-1]
                created_time = time.strptime(mt["created_at"], td_format)
                atime = mtime = time.mktime(
                    (created_time.tm_year,
                     created_time.tm_mon,
                     created_time.tm_mday,
                     created_time.tm_hour + 9,
                     created_time.tm_min,
                     created_time.tm_sec,
                     0, 0, -1)
                )

            # 取得したメディアツイートツリー（複数想定）
            for media_tweet in media_tweets:
                # 外部リンク探索
                if tweet.get("entities"):
                    if tweet["entities"].get("urls"):
                        e_urls = tweet["entities"]["urls"]
                        for element in e_urls:
                            url = element.get("expanded_url")
                            res = self.lsb.CoRProcessDo(url)

                if "extended_entities" not in media_tweet:
                    logger.debug("メディアを含んでいないツイートです。")
                    continue
                if "media" not in media_tweet["extended_entities"]:
                    logger.debug("メディアを含んでいないツイートです。")
                    continue

                # メディアリスト（今の仕様なら画像で最大4枚まで）
                media_list = media_tweet["extended_entities"]["media"]
                for media_dict in media_list:
                    # メディア保存
                    self.TweetMediaSaver(media_tweet, media_dict, atime, mtime)
        return 0

    def GetExistFilelist(self) -> list:
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

    def ShrinkFolder(self, holding_file_num: int) -> int:
        """フォルダ内ファイルの数を一定にする

        Args:
            holding_file_num (int): フォルダ内に残すファイルの数

        Returns:
            int: 0(成功)
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
            file_path = Path(file)

            if ".mp4" == file_path.suffix:  # media_type == "video":
                url = self.GetMediaURL(file_path.name)
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
        self.UpdateDBExistMark(add_img_filename)

        return 0

    def UpdateDBExistMark(self, add_img_filename):
        # 存在マーキングを更新する
        self.db_cont.FlagClear()
        self.db_cont.FlagUpdate(add_img_filename, 1)

    def GetMediaURL(self, filename):
        # 'https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/b0ZDq8zG_HppFWb6.mp4?tag=10'
        response = self.db_cont.SelectFromMediaURL(filename)
        url = response[0]["url"] if len(response) == 1 else ""
        return url

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
                self.PostTweet(done_msg)
                logger.info("Reply posted.")

            if self.type == "RT" and config.getboolean("is_post_retweet_done_reply"):
                self.PostTweet(done_msg)
                logger.info("Reply posted.")

            if config.getboolean("is_post_line_notify"):
                self.PostLineNotify(done_msg)
                logger.info("Line Notify posted.")

            if config.getboolean("is_post_slack_notify"):
                self.PostSlackNotify(done_msg)
                logger.info("Slack Notify posted.")

            if config.getboolean("is_post_discord_notify"):
                self.PostDiscordNotify(done_msg)
                logger.info("Discord Notify posted.")

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
            targets = self.db_cont.DelSelect()
            url = "https://api.twitter.com/1.1/statuses/destroy/{}.json"
            for target in targets:
                response = self.oath.post(url.format(target["tweet_id"]))  # tweet_id

        logger.info("End Of " + self.type + " Crawl Process.")
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
                response = self.oath.post(url, files=files)

                if response.status_code != 200:
                    logger.error("Error code: {0}".format(response.status_code))
                    return None

                media_id = json.loads(response.text)["media_id"]
                media_id_string = json.loads(response.text)["media_id_string"]
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

        response = self.oath.post(url, params=params)
        if response.status_code != 200:
            logger.error("Error code: {0}".format(response.status_code))
            return None

        tweet = json.loads(response.text)

        logger.debug(tweet)
        self.db_cont.DelUpsert(tweet)

        return 0

    def PostLineNotify(self, str: str) -> int:
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
            return None

        return 0

    def PostSlackNotify(self, str: str) -> int:
        """Slack通知ポスト

        Args:
            str (str): Slackに通知する文字列

        Returns:
            int: 0(成功)
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
            int: 0(成功)
        """
        url = self.DISCORD_WEBHOOK_URL

        headers = {
            "Content-Type": "application/json"
        }

        # "content": "😎普通の絵文字\r:sunglasses:Discordの絵文字も:ok_woman:"
        payload = {
            "content": str
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code != 204:  # 成功すると204 No Contentが返ってくる
            logger.error("Error code: {0}".format(response.status_code))
            return None

        return 0

    @abstractmethod
    def Crawl(self) -> int:
        """一連の実行メソッドをまとめる

        Returns:
            int: 0(成功)
        """
        return 0


if __name__ == "__main__":
    import PictureGathering.FavCrawler as FavCrawler
    c = FavCrawler.FavCrawler()
    c.Crawl()
