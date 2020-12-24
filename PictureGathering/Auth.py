# coding: utf-8
import configparser
import json
import pprint
from logging import INFO, getLogger
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qs, parse_qsl, urlparse

logger = getLogger("root")
logger.setLevel(INFO)


def GetAuthEndpointURL(consumer_key, consumer_secret):
    callback = "https://twitter.com/home"

    oauth = OAuth1Session(consumer_key, consumer_secret)

    request_token_url = "https://api.twitter.com/oauth/request_token"
    params = {
        "oauth_callback": callback
    }
    response = oauth.post(request_token_url, params=params)

    if response.status_code != 200:
        raise Exception("GetAuthEndpointURL error {}".format(response.status_code))

    # responseからリクエストトークンを取得
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
    params = {
        "oauth_verifier": oauth_verifier
    }
    response = oauth.post(access_token_url, params=params)

    if response.status_code != 200:
        raise Exception("GetAccessToken error {}".format(response.status_code))

    # responseからアクセストークンを取得
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
        response = oath.get(url, params=params)

        if response.status_code == 503:
            # 503 : Service Unavailable
            if unavailableCnt > 10:
                raise Exception("Twitter API error {}".format(response.status_code))

            unavailableCnt += 1
            logger.info("Service Unavailable 503")
            continue
        unavailableCnt = 0

        if response.status_code != 200:
            raise Exception("Twitter API error {}".format(response.status_code))

        res = json.loads(response.text)
        return res


if __name__ == "__main__":
    # consumer_keyとconsumer_secretからaccess_tokenとaccess_token_secretを取得するサンプル
    # twitter diveloper登録をして4つのキーがすべて分かるならこの認証処理は不要
    # https://developer.twitter.com/en
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    # consumer_keyとconsumer_secret（前提）
    TW_CONSUMER_KEY = config["twitter_token_keys"]["consumer_key"]
    TW_CONSUMER_SECRET = config["twitter_token_keys"]["consumer_secret"]

    # 認証用URLを生成する
    auth_url = GetAuthEndpointURL(TW_CONSUMER_KEY, TW_CONSUMER_SECRET)

    # ユーザーが認証URLにアクセス→認証→結果のURLを貼り付けてもらう
    print("")
    print("auth_url = " + auth_url)
    print("please browser access and confirm ...")
    print("")
    print("after confirmed, input callback URL with oauth_token and oauth_verifier")
    callback_url = input("callback URL (full):")

    # 認証結果のURLのクエリから認証トークンを取得する
    pr = urlparse(callback_url)
    q = dict(parse_qsl(pr.query))
    oauth_token = q.get("oauth_token")
    oauth_verifier = q.get("oauth_verifier")

    if (oauth_token is None) or (oauth_verifier is None):
        print("callback URL (full) is invalid.")
        print("process end.")
        exit(-1)
    else:
        print("callback URL (full) is valid !")
        print("app can use Twitter API below.")

    # consumer_keyとconsumer_secretと認証トークンからアクセストークンを取得する
    access_token = GetAccessToken(TW_CONSUMER_KEY, TW_CONSUMER_SECRET, oauth_token, oauth_verifier)

    # consumer_keyとconsumer_secretとアクセストークンから
    # TwitterAPI利用用oauthセッションを作成する
    # TW_ACCESS_TOKEN_KEY = config["twitter_token_keys"]["access_token"]
    # TW_ACCESS_TOKEN_SECRET = config["twitter_token_keys"]["access_token_secret"]
    TW_ACCESS_TOKEN_KEY = access_token["oauth_token"]
    TW_ACCESS_TOKEN_SECRET = access_token["oauth_token_secret"]
    oath = OAuth1Session(
        TW_CONSUMER_KEY,
        TW_CONSUMER_SECRET,
        TW_ACCESS_TOKEN_KEY,
        TW_ACCESS_TOKEN_SECRET
    )

    # TwitterAPI利用サンプル
    # 認証が必要なユーザー名を取得してみる
    # TwitterAPIリファレンス:account/settings
    # https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/manage-account-settings/api-reference/get-account-settings
    print("Twitter API test : account/settings")
    print("response = ")
    url = "https://api.twitter.com/1.1/account/settings.json"
    params = None
    res = TwitterAPIRequest(oath, url, params)
    pprint.pprint(res)
    pass
