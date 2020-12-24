# coding: utf-8
import configparser
import json
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qsl
from logging import INFO, getLogger

logger = getLogger("root")
logger.setLevel(INFO)


def GetAuthEndpointURL(consumer_key, consumer_secret):
    callback = "https://twitter.com/home"

    oauth = OAuth1Session(consumer_key, consumer_secret)

    request_token_url = "https://api.twitter.com/oauth/request_token"
    params = {"oauth_callback": callback}
    response = oauth.post(
        request_token_url,
        params
    )

    # responseからリクエストトークンを取り出す
    request_token = dict(parse_qsl(response.content.decode("utf-8")))

    # リクエストトークンから連携画面のURLを生成
    authenticate_url = "https://api.twitter.com/oauth/authenticate"
    authenticate_endpoint = "{}?oauth_token={}".format(authenticate_url, request_token["oauth_token"])

    return authenticate_endpoint


def GetAccessToken(consumer_key, consumer_secret, oauth_token, oauth_verifier):
    callback = "https://twitter.com/home"

    oauth = OAuth1Session(
        consumer_key,
        consumer_secret,
        oauth_token,
        oauth_verifier
    )

    access_token_url = "https://api.twitter.com/oauth/access_token"
    params = {"oauth_verifier": oauth_verifier}
    response = oauth.post(
        access_token_url,
        params
    )

    # responseからアクセストークンを取り出す
    access_token = dict(parse_qsl(response.content.decode("utf-8")))

    return access_token


def TwitterAPIRequest(oath, url: str, params: dict) -> dict:
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
        responce = oath.get(url, params=params)

        if responce.status_code == 503:
            # 503 : Service Unavailable
            if unavailableCnt > 10:
                raise Exception('Twitter API error %d' % responce.status_code)

            unavailableCnt += 1
            logger.info('Service Unavailable 503')
            continue
        unavailableCnt = 0

        if responce.status_code != 200:
            raise Exception('Twitter API error %d' % responce.status_code)

        res = json.loads(responce.text)
        return res


if __name__ == "__main__":
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    TW_CONSUMER_KEY = config["twitter_token_keys"]["consumer_key"]
    TW_CONSUMER_SECRET = config["twitter_token_keys"]["consumer_secret"]

    # auth_url = MakeAuthEndpointURL(TW_CONSUMER_KEY, TW_CONSUMER_SECRET)
    # oauth_token = ""
    # oauth_verifier = ""
    # accese_token = GetAccessToken(TW_CONSUMER_KEY, TW_CONSUMER_SECRET, oauth_token, oauth_verifier)

    TW_ACCESS_TOKEN_KEY = config["twitter_token_keys"]["access_token"]
    TW_ACCESS_TOKEN_SECRET = config["twitter_token_keys"]["access_token_secret"]
    oath = OAuth1Session(
        TW_CONSUMER_KEY,
        TW_CONSUMER_SECRET,
        TW_ACCESS_TOKEN_KEY,
        TW_ACCESS_TOKEN_SECRET
    )

    user_name = config["tweet_timeline"]["user_name"]
    count = int(config["tweet_timeline"]["count"])
    page = 1
    url = "https://api.twitter.com/1.1/favorites/list.json"
    params = {
        "screen_name": user_name,
        "page": page,
        "count": count,
        "include_entities": 1,
        "tweet_mode": "extended"
    }
    res = TwitterAPIRequest(oath, url, params)
    pass
