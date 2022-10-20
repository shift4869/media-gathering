# coding: utf-8
import json
import pprint
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from logging import INFO, getLogger
from typing import ClassVar

import requests
from requests_oauthlib import OAuth1Session

from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass
class TwitterAPI():
    api_key: str
    api_secret: str
    access_token_key: str
    access_token_secret: str
    oauth: ClassVar[OAuth1Session]

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str):
            raise TypeError("api_key must be str.")
        if not isinstance(self.api_secret, str):
            raise TypeError("api_secret must be str.")
        if not isinstance(self.access_token_key, str):
            raise TypeError("access_token_key must be str.")
        if not isinstance(self.access_token_secret, str):
            raise TypeError("access_token_secret must be str.")

        self.oauth = OAuth1Session(
            self.api_key,
            self.api_secret,
            self.access_token_key,
            self.access_token_secret
        )

        # 疎通確認
        url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        res = self.get(url)  # 失敗時は例外が送出される

    def _wait(self, dt_unix: float) -> None:
        """指定UNIX時間まで待機する

        Args:
            dt_unix (float): UNIX時間の指定（秒）
        """
        seconds = dt_unix - time.mktime(datetime.now().timetuple())
        seconds = max(seconds, 0)
        logger.debug("=======================")
        logger.debug(f"=== waiting {seconds} sec ===")
        logger.debug("=======================")
        sys.stdout.flush()
        time.sleep(seconds)

    def _wait_until_reset(self, response: dict) -> None:
        """TwitterAPIが利用できるまで待つ

        Args:
            response (dict): 利用できるまで待つTwitterAPIを使ったときのレスポンス

        Raises:
            HTTPError: レスポンスヘッダにx-rate-limit-remaining and x-rate-limit-reset が入ってない場合

        Returns:
            None: このメソッド実行後はresponseに対応するエンドポイントが利用可能であることが保証される
        """
        match response.headers:
            case {
                # "x-rate-limit-limit": limit,
                "x-rate-limit-remaining": remain_count,
                "x-rate-limit-reset": dt_unix,
            }:
                dt_jst_aware = datetime.fromtimestamp(dt_unix, timezone(timedelta(hours=9)))
                remain_seconds = dt_unix - time.mktime(datetime.now().timetuple())
                logger.debug("リクエストURL {}".format(response.url))
                logger.debug("アクセス可能回数 {}".format(remain_count))
                logger.debug("リセット時刻 {}".format(dt_jst_aware))
                logger.debug("リセットまでの残り時間 {}[s]".format(remain_seconds))
                if remain_count == 0:
                    self._wait(dt_unix + 3)
            case _:
                msg = "not found  -  x-rate-limit-remaining and x-rate-limit-reset"
                logger.debug(msg)
                raise requests.HTTPError(msg)

    def request(self, endpoint_url: str, params: dict, method: str) -> dict:
        """TwitterAPIを使用するラッパメソッド

        Args:
            endpoint_url (str): TwitterAPIエンドポイントURL
            params (dict): TwitterAPI使用時に渡すパラメータ
            method (str): TwitterAPI使用時のメソッド、デフォルトはGET

        Raises:
            ValueError: endpoint_url が想定外のエンドポイントの場合
            ValueError: method が想定外のメソッドの場合
            ValueError: 月のツイートキャップ上限対象APIで、上限を超えている場合
            HTTPError: RETRY_NUM=5回リトライしてもAPI利用結果が200でなかった場合

        Returns:
            dict: TwitterAPIレスポンス
        """
        # バリデーション
        if not isinstance(endpoint_url, str):
            raise ValueError("endpoint_url must be str.")
        if not isinstance(params, dict):
            raise ValueError("params must be dict.")
        if not (isinstance(method, str) and method in ["GET", "POST", "PUT", "DELETE"]):
            raise ValueError('method must be in ["GET", "POST", "PUT", "DELETE"].')
        if not TwitterAPIEndpoint.validate(endpoint_url, method):
            raise ValueError(f"{method} {endpoint_url} : is not Twitter API Endpoint or invalid method.")

        # 月のツイートキャップを超えていないかチェック
        TwitterAPIEndpoint.raise_for_tweet_cap_limit_over()

        # エンドポイント名を取得
        endpoint_name: TwitterAPIEndpointName = TwitterAPIEndpoint.get_name(endpoint_url, method)
        if not endpoint_name:
            raise ValueError(f"{endpoint_url} : is not Twitter API Endpoint.")

        # メソッド振り分け
        method_func = None
        if method == "GET":
            method_func = self.oauth.get
        elif method == "POST":
            method_func = self.oauth.post
        elif method == "DELETE":
            method_func = self.oauth.delete
        if not method_func:
            raise ValueError(f"{method} is invalid method.")

        # ツイートキャップ対象エンドポイント
        tweet_cap_endpoint = [
            TwitterAPIEndpointName.LIKED_TWEET,
            TwitterAPIEndpointName.TIMELINE_TWEET,
        ]

        # RETRY_NUM 回だけリクエストを試行する
        RETRY_NUM = 5
        for i in range(RETRY_NUM):
            try:
                # POSTの場合はjsonとして送信（ヘッダーにjson指定すればOK?）
                response = None
                if method == "POST":
                    response = method_func(endpoint_url, json=params)
                else:
                    response = method_func(endpoint_url, params=params)
                response.raise_for_status()

                # 成功したならばJSONとして解釈してレスポンスを返す
                res: dict = json.loads(response.text)

                # ツイートキャップ対象エンドポイントならば現在の推定カウント数に加算
                if endpoint_name in tweet_cap_endpoint:
                    count = int(res.get("meta", {}).get("result_count", 0))
                    TwitterAPIEndpoint.increase_tweet_cap(count)
                return res
            except requests.exceptions.RequestException as e:
                logger.error(e.response.txt)
            except Exception as e:
                pass

            # リクエスト失敗した場合
            try:
                # レートリミットにかかっていないか確認して必要なら待つ
                self._wait_until_reset(response)
            except Exception as e:
                # 原因不明：徐々に待機時間を増やしてとりあえず待つ(exp backoff)
                wair_seconds = 2 ** i
                n = time.mktime(datetime.now().timetuple())
                self._wait(n + wair_seconds)
            logger.error(f"retry ({i}/{RETRY_NUM}) ...")
        else:
            raise requests.HTTPError("Twitter API error : exceed RETRY_NUM.")

    def get(self, endpoint_url: str, params: dict = {}) -> dict:
        """GETリクエストのエイリアス
        """
        return self.request(endpoint_url=endpoint_url, params=params, method="GET")

    def post(self, endpoint_url: str, params: dict = {}) -> dict:
        """POSTリクエストのエイリアス
        """
        return self.request(endpoint_url=endpoint_url, params=params, method="POST")

    def delete(self, endpoint_url: str, params: dict = {}) -> dict:
        """DELETEリクエストのエイリアス
        """
        return self.request(endpoint_url=endpoint_url, params=params, method="DELETE")


if __name__ == "__main__":
    import configparser
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_token_keys_v2"]
    TW_API_KEY = config["api_key"]
    TW_API_SECRET = config["api_key_secret"]
    TW_ACCESS_TOKEN_KEY = config["access_token"]
    TW_ACCESS_TOKEN_SECRET = config["access_token_secret"]
    twitter = TwitterAPI(
        TW_API_KEY,
        TW_API_SECRET,
        TW_ACCESS_TOKEN_KEY,
        TW_ACCESS_TOKEN_SECRET
    )

    # 認証ユーザー詳細取得
    url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
    res = twitter.request(url, {}, "GET")
    pprint.pprint(res)

    # like取得
    # MY_ID = 175674367
    # url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.LIKED_TWEET, MY_ID)
    # params = {
    #     "expansions": "author_id,attachments.media_keys",
    #     "tweet.fields": "id,attachments,author_id,entities,text,source,created_at",
    #     "user.fields": "id,name,username,url",
    #     "media.fields": "url",
    #     "max_results": 100,
    # }
    # tweets = twitter.get(url, params=params)
    # pprint.pprint(tweets)
