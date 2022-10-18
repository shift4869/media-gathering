# coding: utf-8
"""サンドボックス

Twitter API v2を試す
"""

import configparser
import json
import logging.config
import pprint
from logging import INFO, getLogger

from requests_oauthlib import OAuth1Session

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    # すべてのライブラリのログ出力を抑制
    # print("logger", name)
    getLogger(name).disabled = True
logger = getLogger("root")
logger.setLevel(INFO)


if __name__ == "__main__":
    # import PictureGathering.FavCrawler as FavCrawler
    # c = FavCrawler.FavCrawler()
    # c.Crawl()

    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_token_keys_v2"]
    TW_API_KEY = config["api_key"]
    TW_API_SECRET = config["api_key_secret"]
    TW_ACCESS_TOKEN_KEY = config["access_token"]
    TW_ACCESS_TOKEN_SECRET = config["access_token_secret"]

    oath = OAuth1Session(
        TW_API_KEY,
        TW_API_SECRET,
        TW_ACCESS_TOKEN_KEY,
        TW_ACCESS_TOKEN_SECRET
    )

    # ツイート取得
    # 認証ユーザー詳細取得
    # url = "https://api.twitter.com/2/users/me"
    # res = oath.get(url, params={})
    # tweet = json.loads(res.text)
    # pprint.pprint(tweet)

    # ツイート取得
    # MY_ID = 175674367
    # url = f"https://api.twitter.com/2/users/{MY_ID}/tweets"
    # params = {
    #     "expansions": "author_id",
    #     "tweet.fields": "author_id,entities,text,source,created_at",
    #     "user.fields": "id,name,username,url",
    #     "max_results": 5,
    # }
    # res = oath.get(url, params=params)
    # tweet = json.loads(res.text)
    # pprint.pprint(tweet)

    # レートリミット

    # ツイート投稿
    # url = "https://api.twitter.com/2/tweets"
    # params = {
    #     "text": "ツイートテスト with v2",
    # }
    # res = oath.post(url, json=params)
    # tweet = json.loads(res.text)
    # pprint.pprint(tweet)

    # ツイート削除
    # url = f"https://api.twitter.com/2/tweets/1579254037484310530"
    # res = oath.delete(url)
    # tweet = json.loads(res.text)
    # pprint.pprint(tweet)

    # ユーザー詳細取得（必要か？）

    # like取得
    # MY_ID = 175674367
    # url = f"https://api.twitter.com/2/users/{MY_ID}/liked_tweets"
    # params = {
    #     "expansions": "author_id,attachments.media_keys",
    #     "tweet.fields": "id,attachments,author_id,entities,text,source,created_at",
    #     "user.fields": "id,name,username,url",
    #     "media.fields": "url",
    #     "max_results": 100,
    # }
    # res = oath.get(url, params=params)
    # tweet = json.loads(res.text)
    # pprint.pprint(tweet)

    # RT取得
    # MY_ID = 175674367
    # url = f"https://api.twitter.com/2/users/{MY_ID}/tweets"
    # params = {
    #     "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
    #     "tweet.fields": "id,attachments,author_id,referenced_tweets,entities,text,source,created_at",
    #     "user.fields": "id,name,username,url",
    #     "media.fields": "url,variants,preview_image_url,alt_text",
    #     "max_results": self.max_results,
    # }
    # res = oath.get(url, params=params)
    # tweet = json.loads(res.text)
    # pprint.pprint(tweet)

    # 必要な情報
    # td_format = "%a %b %d %H:%M:%S +0000 %Y"
    # dts_format = "%Y-%m-%d %H:%M:%S"
    # tca = tweet["created_at"]
    # dst = datetime.strptime(tca, td_format) + timedelta(hours=9)
    # text = tweet["text"] if "text" in tweet else tweet["full_text"]
    # regex = re.compile(r"<[^>]*?>")
    # via = regex.sub("", tweet["source"])
    # param = {
    #     "img_filename": file_name,
    #     "url": url_orig,
    #     "url_thumbnail": url_thumbnail,
    #     "tweet_id": tweet["id_str"],
    #     "tweet_url": tweet["entities"]["media"][0]["expanded_url"],
    #     "created_at": dst.strftime(dts_format),
    #     "user_id": tweet["user"]["id_str"],
    #     "user_name": tweet["user"]["name"], //
    #     "screan_name": tweet["user"]["screen_name"],
    #     "tweet_text": text,
    #     "tweet_via": via,
    #     "saved_localpath": save_file_fullpath,
    #     "saved_created_at": datetime.now().strftime(dts_format)
    # }
