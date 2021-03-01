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


class NijieController:
    def __init__(self, email: str, password: str):
        # User-Agent偽装用ヘッダ
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

        self.cookies = None
        self.auth_success = False
        self.cookies, self.auth_success = self.Login(email, password)

        if not self.auth_success:
            exit(-1)
    
    def Login(self, email: str, password: str):
        """nijieページにログインし、ログイン情報を保持したクッキーを返す

        Args:
            email (str): nijieユーザー名（メールアドレス）
            password (str): nijieユーザーPW

        Returns:
            cookies: ログイン情報を保持したクッキー
        """
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
            res = requests.get(top_url, headers=self.headers, cookies=cookies)
            res.raise_for_status()
            
            # 返ってきたレスポンスがトップページのものかチェック
            # 不正なクッキーだと年齢確認画面に飛ばされる（titleとurlから判別可能）
            auth_success = res.status_code == 200 and res.url == top_url and "ニジエ - nijie" in res.text 

        if not auth_success:
            # クッキーが存在していない場合、または有効なクッキーではなかった場合

            # 年齢確認で「はい」を選択したあとのURLにアクセス
            res = requests.get("https://nijie.info/age_jump.php?url=", headers=self.headers)
            res.raise_for_status()

            # 認証用URLクエリを取得する
            qs = urllib.parse.urlparse(res.url).query
            qd = urllib.parse.parse_qs(qs)
            url = qd["url"][0]

            # ログイン時に必要な情報
            payload = {
                "email": email,
                "password": password,
                "save": "on",
                "ticket": "",
                "url": url
            }

            # ログインする
            login_url = "https://nijie.info/login_int.php"
            res = requests.post(login_url, data=payload)
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

        return (cookies, auth_success)

    @classmethod
    def IsNijieURL(cls, url: str) -> bool:
        """URLがnijieのURLかどうか判定する

        Note:
            想定URL形式：http://nijie.info/view.php?id=******
                      ：http://nijie.info/view_popup.php?id=******

        Args:
            url (str): 判定対象url

        Returns:
            boolean: nijie作品ページURLならTrue、そうでなければFalse
        """
        pattern = r"^http://nijie.info/view.php\?id=[0-9]*$"
        regex = re.compile(pattern)
        f1 = not (regex.findall(url) == [])

        pattern = r"^http://nijie.info/view_popup.php\?id=[0-9]*$"
        regex = re.compile(pattern)
        f2 = not (regex.findall(url) == [])

        return f1 or f2

    def GetIllustId(self, url: str) -> int:
        """nijie作品ページURLからイラストIDを取得する

        Args:
            url (str): nijie作品ページURL

        Returns:
            int: 成功時 イラストID、失敗時 -1
        """
        if not self.IsNijieURL(url):
            return -1

        qs = urllib.parse.urlparse(url).query
        qd = urllib.parse.parse_qs(qs)
        illust_id = int(qd["id"][0])
        return illust_id

    def GetIllustURLs(self, url: str) -> list[str]:
        """nijie作品ページURLからイラストへの直リンクを取得する

        Note:
            漫画ページの場合、それぞれのページについて
            全てURLを取得するため返り値はList[str]となる

        Args:
            url (str): nijie作品ページURL

        Returns:
            List[str]: 成功時 nijie作品のイラストへの直リンクlist、失敗時 空リスト
        """
        illust_id = self.GetIllustId(url)
        if illust_id == -1:
            return []

        # 作品詳細ページを一時保存する場所
        NIJIE_TEMPHTML_PATH = "./html/nijie_detail_page.html"
        ntp = Path(NIJIE_TEMPHTML_PATH)

        # 作品詳細ページをGET
        illust_url = "http://nijie.info/view_popup.php?id={}".format(illust_id)
        res = requests.get(illust_url, headers=self.headers, cookies=self.cookies)
        res.raise_for_status()

        with ntp.open(mode="w", encoding="UTF-8") as fout:
            fout.write(res.text)

        # BeautifulSoupのhtml解析準備を行う
        soup = BeautifulSoup(res.text, "html.parser")
        urls, author_name, author_id, illust_name = self.DetailPageAnalysis(soup)

        pass

    def DetailPageAnalysis(self, soup) -> list[str]:
        # html構造解析
        urls = []
        # 画像への直リンクを取得する
        div_imgs = soup.find_all("div", id="img_filter")
        for div_img in div_imgs:
            a_s = div_img.find_all("a")
            img_url = ""
            for a in a_s:
                if a.get("href") is not None:
                    img_url = "http:" + a.img["src"]
                    break
            if img_url == "":
                continue
            urls.append(img_url)

        # 作者IDは1枚目の画像ファイル名に含まれている
        author_id = int(Path(urls[0]).name.split("_")[0])

        # 作品タイトル、作者名はページタイトルから取得する
        title_tag = soup.find("title")
        title = title_tag.text.split("|")
        illust_name = title[0].strip()
        author_name = title[1].strip()
        return (urls, author_name, author_id, illust_name)


if __name__ == "__main__":
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    nc = NijieController(config["nijie"]["email"], config["nijie"]["password"])
    illust_id = 417853
    illust_url = "http://nijie.info/view_popup.php?id={}".format(illust_id)
    nc.GetIllustURLs(illust_url)

    pass
