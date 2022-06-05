# coding: utf-8
import asyncio
import random
import re
import urllib.parse
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

import pyppeteer
import requests.cookies
from requests_html import HTMLSession

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class SkebCookie():
    """SkebCookie

    Returns:
        SkebCookie: SkebCookieを表すValueObject
    """
    cookies: requests.cookies.RequestsCookieJar
    headers: dict
    token: str

    SKEB_COOKIE_PATH = "./config/skeb_cookie.ini"
    SKEB_TOKEN_PATH = "./config/skeb_token.ini"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("cookies is not requests.cookies.RequestsCookieJar, invalid SkebCookie.")
        if not isinstance(self.headers, dict):
            raise TypeError("headers is not dict, invalid SkebCookie.")
        return True

    @classmethod
    def is_valid_cookies(self, top_url: URL, headers: dict, cookies: requests.cookies.RequestsCookieJar, token: str) -> bool:
        # テスト用作品ページ（画像）
        # url = "https://skeb.jp/@matsukitchi12/works/25"
        url = f"{top_url.non_query_url}callback?path=/&token={token}"

        session = HTMLSession()
        response = session.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        response.html.render(sleep=2)

        # トップページはローカルストレージ情報を使うため
        # 直接作品ページを見てみる
        # 画像直リンクが取得できればOK
        # img_tags = response.html.find("img")
        # for img_tag in img_tags:
        #     src_url = img_tag.attrs.get("src", "")
        #     if "https://skeb.imgix.net/uploads/" in src_url or \
        #        "https://skeb.imgix.net/requests/" in src_url:
        #         return True

        # クッキーが有効な場合はトップページからaccountページへのリンクが取得できる
        # 右上のアイコンマウスオーバー時に展開されるリストから
        # 「アカウント」メニューがあるかどうかを見ている
        a_tags = response.html.find("a")
        for a_tag in a_tags:
            account_href = a_tag.attrs.get("href", "")
            full_text = a_tag.full_text
            if "/account" in account_href and "アカウント" == full_text:
                return True
        return False

    @classmethod
    async def get_cookies_from_oauth(cls, username: Username, password: Password, top_url: URL, headers: dict) -> "SkebCookie":
        """ツイッターログインを行いSkebページで使うcookiesを取得する

        Notes:
            pyppeteerを通してheadless chromeを操作する

        Args:
            twitter_id (str): SkebユーザーIDとして登録したツイッターID
            twitter_password (str): SkebユーザーIDとして登録したツイッターのパスワード

        Returns:
            SkebCookie: アクセスに使うクッキー
        """
        urls = []
        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()
        logger.info("Browsing start.")

        # レスポンスを監視してコールバックURLをキャッチする
        async def ResponseListener(response):
            if (top_url.original_url + "callback") in response.url:
                urls.append(response.url)
        page.on("response", lambda response: asyncio.ensure_future(ResponseListener(response)))

        # トップページに遷移
        await asyncio.gather(page.goto(top_url.original_url), page.waitForNavigation())
        content = await page.content()
        cookies = await page.cookies()
        logger.info("Skeb Top Page loaded.")

        # 右上のログインボタンを押下
        # 不可視の別ボタンがある？ようなのでセレクタで該当した2つ目のタグを操作する
        # selector = "body > div > div > div > header > nav > div > div.navbar-menu > div > div > button"
        selector = 'button[class="button is-twitter"]'
        login_btn = await page.querySelectorAll(selector)
        if len(login_btn) != 2 or not login_btn[1]:
            raise ValueError("Twitter Login failed.")
        await asyncio.gather(login_btn[1].click(), page.waitForNavigation())
        content = await page.content()
        cookies = await page.cookies()
        logger.info("Twitter Login Page loaded.")

        # ツイッターログイン情報を入力し、3-Leg認証を進める
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="session[username_or_email]"]'
        await page.type(selector, username.name)
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="session[password]"]'
        await page.type(selector, password.password)
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[id="allow"]'
        await asyncio.gather(page.click(selector), page.waitForNavigation())
        logger.info("Twitter oauth running...")

        # ツイッターログインが成功かどうか調べる
        # ログインに成功していればこのタイミングでコールバックURLが返ってくる
        await page.waitForNavigation()
        content = await page.content()
        cookies = await page.cookies()

        # コールバックURLがキャッチできたことを確認
        if len(urls) == 0:
            raise ValueError("Getting Skeb Cookie is failed.")
        logger.info("Twitter oauth success.")

        # コールバックURLからtokenを切り出す
        callback_url = urls[0]
        q = urllib.parse.urlparse(callback_url).query
        qs = urllib.parse.parse_qs(q)
        token = qs.get("token", [""])[0]

        javascript_func = """
            function allStorage() {
                var values = [],
                    keys = Object.keys(localStorage),
                    i = keys.length;

                while ( i-- ) {
                    values.push( keys[i] + ' : ' + localStorage.getItem(keys[i]) );
                }

                return values;
            }
            allStorage()
        """
        localstorage = await page.evaluate(javascript_func, force_expr=True)

        # 取得したローカルストレージを保存
        slsp = Path("./config/skeb_localstorage.ini")
        with slsp.open("w") as fout:
            for ls in localstorage:
                fout.write(ls + "\n")

        # 取得したトークンを保存
        stp = Path(SkebCookie.SKEB_TOKEN_PATH)
        with stp.open("w") as fout:
            fout.write(token)

        # クッキー保存を試みる
        # クッキー解析用
        def CookieToString(c):
            name = c["name"]
            value = c["value"]
            expires = c["expires"]
            path = c["path"]
            domain = c["domain"]
            return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}"'

        # クッキー情報をファイルに保存する
        requests_cookies = requests.cookies.RequestsCookieJar()
        scp = Path(SkebCookie.SKEB_COOKIE_PATH)
        with scp.open(mode="w") as fout:
            for c in cookies:
                requests_cookies.set(c["name"], c["value"], expires=c["expires"], path=c["path"], domain=c["domain"])
                fout.write(CookieToString(c) + "\n")

        return SkebCookie(requests_cookies, headers, token)

    @classmethod
    def get(cls, username: Username, password: Password, top_url: URL, headers: dict) -> "SkebCookie":
        """クッキー取得
        """
        # アクセスに使用するクッキーファイル置き場
        scp = Path(SkebCookie.SKEB_COOKIE_PATH)
        # アクセスに使用するトークンファイル置き場
        stp = Path(SkebCookie.SKEB_TOKEN_PATH)

        # クッキーとトークンを取得する
        token = ""
        if scp.exists() and stp.exists():
            # トークンが既に存在している場合
            # トークンを読み込む
            with stp.open(mode="r") as fin:
                token = fin.read()

            # クッキーが既に存在している場合
            # クッキーを読み込む
            cookies = requests.cookies.RequestsCookieJar()
            with scp.open(mode="r") as fin:
                for line in fin:
                    if line == "":
                        break

                    sc = {}
                    elements = re.split("[,\n]", line)
                    for element in elements:
                        element = element.strip().replace('"', "")  # 左右の空白とダブルクォートを除去
                        if element == "":
                            break

                        key, val = element.split("=")  # =で分割
                        sc[key] = val

                    cookies.set(sc["name"], sc["value"], expires=sc["expires"], path=sc["path"], domain=sc["domain"])

            # 有効なクッキーか確認する
            # 実際にアクセスして確認するので負荷を考えるとチェックするかどうかは微妙
            if(SkebCookie.is_valid_cookies(top_url, headers, cookies, token)):
                return SkebCookie(cookies, headers, token)
            else:
                logger.error("Getting Skeb Cookie is failed.")

        # クッキーファイルがない場合、または有効なクッキーではなかった場合
        # 認証してCookiesを取得する
        loop = asyncio.new_event_loop()
        skeb_cookie = loop.run_until_complete(SkebCookie.get_cookies_from_oauth(username, password, top_url, headers))

        # logger.info(f"Getting Skeb token is success: {token}")
        logger.info("Getting Skeb Cookie is success.")

        # 取得したクッキーを保存
        # get_cookies_from_oauth内で保存される
        # with scp.open("w") as fout:
        #     fout.write(skeb_cookie)

        return skeb_cookie


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path
    from PictureGathering.LinkSearch.Password import Password
    from PictureGathering.LinkSearch.Skeb.SkebFetcher import SkebFetcher
    from PictureGathering.LinkSearch.Username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["skeb"].getboolean("is_skeb_trace"):
        fetcher = SkebFetcher(Username(config["skeb"]["twitter_id"]), Password(config["skeb"]["twitter_password"]), base_path)

        # イラスト（複数）
        work_url = "https://skeb.jp/@matsukitchi12/works/25?query=1"
        # 動画（単体）
        # work_url = "https://skeb.jp/@wata_lemon03/works/7"
        # gif画像（複数）
        # work_url = "https://skeb.jp/@_sa_ya_/works/55"

        fetcher.fetch(work_url)
