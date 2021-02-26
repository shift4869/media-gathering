# coding: utf-8
import configparser
import logging.config
import os
import re
import traceback
import urllib.parse
import zipfile
from logging import INFO, getLogger
from pathlib import Path
from time import sleep

import requests
from bs4 import BeautifulSoup

logger = getLogger("root")
logger.setLevel(INFO)


def GetIllustURLs(illust_url):
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    qs = urllib.parse.urlparse(illust_url).query
    qd = urllib.parse.parse_qs(qs)
    illust_id = qd["id"][0]
    illust_url = "http://nijie.info/view_popup.php?id={}".format(illust_id)
    
    # User-Agent偽装用ヘッダ
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

    # ログイン情報を保持するクッキー置き場
    NIJIE_COOKIE_PATH = "./config/nijie_cookie.ini"
    ncp = Path(NIJIE_COOKIE_PATH)

    cookies = requests.cookies.RequestsCookieJar()
    auth_success = False
    if ncp.is_file():
        # クッキーが既に存在している場合
        # クッキーを読み込む
        with ncp.open(mode="r") as fin:
            for line in fin:
                if line == "":
                    break

                nc = {}
                elements = re.split("[,\n]", line)
                for element in elements:
                    element = element.strip().replace('"', "")  # 左右の空白とダブルクォートを除去
                    if element == "":
                        break

                    key, val = element.split("=")  # =で分割
                    nc[key] = val

                cookies.set(nc["name"], nc["value"], expires=nc["expires"], path=nc["path"], domain=nc["domain"])
        
        # トップページをGETしてクッキーが有効かどうか調べる
        top_url = "http://nijie.info/index.php"
        res = requests.get(top_url, headers=headers, cookies=cookies)
        res.raise_for_status()
        
        # 返ってきたレスポンスがトップページのものかチェック
        # 不正なクッキーだと年齢確認画面に飛ばされる（titleとurlから判別可能）
        auth_success = "ニジエ - nijie" in res.text and res.status_code == 200 and res.url == top_url

    if not auth_success:
        # クッキーが存在していない場合、または有効なクッキーではなかった場合

        # 年齢確認で「はい」を選択したあとのURL
        res = requests.get("https://nijie.info/age_jump.php?url=", headers=headers)
        res.raise_for_status()

        # 認証用URLクエリを取得する
        qs = urllib.parse.urlparse(res.url).query
        qd = urllib.parse.parse_qs(qs)
        url = qd["url"][0]

        # ログイン時に必要な情報
        payload = {
            "email": config["nijie"]["email"],
            "password": config["nijie"]["password"],
            "save": "on",
            "ticket": "",
            "url": url
        }

        # ログインする
        post_url = "https://nijie.info/login_int.php"
        res = requests.post(post_url, data=payload)
        res.raise_for_status()

        # 以降はクッキーに認証情報が含まれているため、これを用いて各ページをGETする
        cookies = res.cookies

        # クッキー解析用
        def CookieToString(c):
            name = c.name
            value = c.value
            expires = c.expires
            path = c.path
            domain = c.domain
            return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}"'

        # クッキー情報を保存する
        with ncp.open(mode="w") as fout:
            for c in cookies:
                fout.write(CookieToString(c) + "\n")

    # 作品詳細ページをGET
    res = requests.get(illust_url, headers=headers, cookies=cookies)
    res.raise_for_status()

    with open("./response.html", mode="w", encoding="UTF-8") as fout:
        fout.write(res.text)

    # with open("./response.html", mode="r") as fin:
    #     res = fin.read()

    # soup = BeautifulSoup(res, "html.parser")
    pass


if __name__ == "__main__":
    illust_id = 417853
    illust_url = "http://nijie.info/view_popup.php?id={}".format(illust_id)
    GetIllustURLs(illust_url)

    pass
