# coding: utf-8
import json
import pprint
import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

import requests
from requests_oauthlib import OAuth1Session


class TwitterAPIEndpoint(Enum):
    # 必要な機能
    # ツイート取得(userid)
    TIMELINE_TWEET = ["https://api.twitter.com/2/users/{}/tweets", "GET"]

    # ツイート投稿
    POST_TWEET = ["https://api.twitter.com/2/tweets", "POST"]

    # ツイート削除(tweetid)
    DELETE_TWEET = ["https://api.twitter.com/2/tweets/{}", "DELETE"]

    # ユーザー詳細取得
    USER_LOOKUP = ["https://api.twitter.com/2/users", "GET"]

    # like取得(userid)
    LIKED_TWEET = ["https://api.twitter.com/2/users/{}/liked_tweets", "GET"]

    # レートリミット

    # RT取得
    # MY_ID = 175674367
    # url = f"https://api.twitter.com/2/users/{MY_ID}/tweets"
    pass


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
        if not isinstance(self.oauth, OAuth1Session):
            raise ValueError("oauth must be OAuth1Session, invalid keys.")

    def request(self, endpoint_url: str, params: dict, method: str = "GET") -> dict:
        """TwitterAPIを使用するラッパメソッド

        Args:
            endpoint_url (str): TwitterAPIエンドポイントURL
            params (dict): TwitterAPI使用時に渡すパラメータ
            method (str): TwitterAPI使用時のメソッド、デフォルトはGET

        Raises:
            ValueError: endpoint_url が想定外のエンドポイントの場合
            ValueError: method が想定外のメソッドの場合
            HTTPError: RETRY_NUM=5回リトライしてもAPI利用結果が200でかった場合

        Returns:
            dict: TwitterAPIレスポンス
        """
        # バリデーション
        for expect_endpoint in TwitterAPIEndpoint:
            e_url = expect_endpoint.value[0]
            e_method = expect_endpoint.value[1]
            pattern = e_url.format(".*") if "{}" in e_url else e_url
            if re.findall(f"^{pattern}$", endpoint_url) != []:
                if e_method == method:
                    break
        else:
            raise ValueError(f"{method} {endpoint_url} : is not Twitter API Endpoint or invalid method.")

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

        # リクエスト
        RETRY_NUM = 5
        for _ in range(RETRY_NUM):
            try:
                response = method_func(endpoint_url, params=params)
                response.raise_for_status()
                res = json.loads(response.text)
                return res
            except requests.exceptions.RequestException as e:
                continue
            except Exception as e:
                continue
        else:
            raise requests.HTTPError(f"Twitter API error : exceed RETRY_NUM.")


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
    url = "https://api.twitter.com/2/users"
    params = {
        "ids": "175674367,175674367"
    }
    res = twitter.request(url, params, "GET")
    pprint.pprint(res)
