# coding: utf-8
from abc import ABCMeta, abstractmethod
import configparser
from datetime import datetime
from datetime import timezone
from datetime import timedelta
import json
import logging.config
from logging import getLogger, DEBUG, INFO
import os
from pathlib import Path
import requests
from requests_oauthlib import OAuth1Session
import slackweb
import sys
import time
import traceback
import urllib


from PictureGathering import DBController, WriteHTML


logging.config.fileConfig("./log/logging.ini")
logger = getLogger("root")
logger.setLevel(INFO)


class Crawler(metaclass=ABCMeta):
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

    def GetTwitterAPIResourceType(self, url):
        # クエリを除去
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

    def GetTwitterAPILimitContext(self, res_text, params):
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

    def WaitUntilReset(self, dt_unix):
        seconds = dt_unix - time.mktime(datetime.now().timetuple())
        seconds = max(seconds, 0)
        logger.debug('=======================')
        logger.debug('== waiting {} sec =='.format(seconds))
        logger.debug('=======================')
        sys.stdout.flush()
        time.sleep(seconds + 10)  # 念のため + 10 秒
        return 0

    def CheckTwitterAPILimit(self, called_url):
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

    def WaitTwitterAPIUntilReset(self, responce):
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

    def TwitterAPIRequest(self, url, params):
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

    # tweet["extended_entities"]["media"]から保存対象のメディアURLを取得する
    # 引数や辞書構造が不正だった場合空文字列を返す
    def GetMediaUrl(self, media_dict):
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

    def ImageSaver(self, tweets):
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

    # save_pathにあるファイル名一覧を取得する
    def GetExistFilelist(self):
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

    def ShrinkFolder(self, holding_file_num):
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
                self.add_url_list.append(url)
                add_img_filename.append(os.path.basename(file))

        # 存在マーキングを更新する
        self.UpdateDBExistMark(add_img_filename)

        return 0

    @abstractmethod
    def UpdateDBExistMark(self, add_img_filename):
        pass

    @abstractmethod
    def GetVideoURL(self, file_name):
        pass

    @abstractmethod
    def MakeDoneMessage(self):
        pass

    def EndOfProcess(self):
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

    def PostTweet(self, str):
        url = "https://api.twitter.com/1.1/users/show.json"
        reply_user_name = self.config["notification"]["reply_to_user_name"]

        params = {
            "screen_name": reply_user_name,
        }
        res = self.TwitterAPIRequest(url, params=params)
        if res is None:
            return None

        url = "https://api.twitter.com/1.1/statuses/update.json"
        reply_to_status_id = res["id_str"]

        str = "@" + reply_user_name + " " + str

        params = {
            "status": str,
            "in_reply_to_status_id": reply_to_status_id,
        }
        responce = self.oath.post(url, params=params)

        self.db_cont.DBDelInsert(json.loads(responce.text))

        if responce.status_code != 200:
            logger.error("Error code: {0}".format(responce.status_code))
            return None

        return 0

    def PostLineNotify(self, str):
        url = "https://notify-api.line.me/api/notify"
        token = self.LN_TOKEN_KEY

        headers = {"Authorization": "Bearer " + token}
        payload = {"message": str}

        responce = requests.post(url, headers=headers, params=payload)

        if responce.status_code != 200:
            logger.error("Error code: {0}".format(responce.status_code))
            return None

        return 0

    def PostSlackNotify(self, str):
        try:
            slack = slackweb.Slack(url=self.SLACK_WEBHOOK_URL)
            slack.notify(text="<!here> " + str)
        except ValueError:
            logger.error("Webhook URL error: {0} is invalid".format(self.SLACK_WEBHOOK_URL))
            return None

        return 0

    @abstractmethod
    def Crawl(self):
        pass

if __name__ == "__main__":
    # import FavCrawler as FavCrawler
    # c = FavCrawler.FavCrawler()
    # c.Crawl()
    pass
