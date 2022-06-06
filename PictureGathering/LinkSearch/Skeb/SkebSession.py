# coding: utf-8
import asyncio
from http.cookiejar import Cookie
import random
import re
from typing import ClassVar
import urllib.parse
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from httplib2 import Response

import pyppeteer
import requests.cookies
import requests.utils
from requests_html import HTMLSession, HTML, AsyncHTMLSession

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass()
class SkebSession():
    headers: dict
    cookie_jar: requests.cookies.RequestsCookieJar
    local_storage: list[str]
    session: ClassVar[AsyncHTMLSession]
    cookies: ClassVar[list[Cookie]]
    loop: ClassVar[asyncio.AbstractEventLoop]

    SKEB_COOKIE_PATH = "./config/skeb_cookie.ini"
    SKEB_TOKEN_PATH = "./config/skeb_token.ini"
    SKEB_LOCAL_STORAGE_PATH = "./config/skeb_localstorage.ini"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self.loop = asyncio.new_event_loop()
        res = self.loop.run_until_complete(self._is_valid())

    async def _is_valid(self) -> bool:
        # if not isinstance(self.cookies, requests.cookies.RequestsCookieJar):
        #     raise TypeError("cookies is not requests.cookies.RequestsCookieJar, invalid SkebSession.")
        # if not isinstance(self.headers, dict):
        #     raise TypeError("headers is not dict, invalid SkebSession.")
        # テスト用作品ページ（画像）
        # url = "https://skeb.jp/@matsukitchi12/works/25"
        # url = f"{top_url.non_query_url}callback?path=/&token={token}"

        # ローカルストレージをセットしたpyppeteerで直リンクが載っているページを取得する
        url = "https://skeb.jp/"
        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()
        await page.goto(url)

        # ローカルストレージを読み込んでセットする
        javascript_func1 = "localStorage.setItem('{}', '{}');"
        for line in self.local_storage:
            elements = re.split(" : |\n", line)
            key = elements[0]
            value = elements[1]
            await page.evaluate(javascript_func1.format(key, value))

        # ローカルストレージを出力する
        # javascript_func2 = """
        #     function allStorage() {
        #         var values = [],
        #             keys = Object.keys(localStorage),
        #             i = keys.length;

        #         while ( i-- ) {
        #             values.push( keys[i] + ' : ' + localStorage.getItem(keys[i]) );
        #         }

        #         return values;
        #     }
        #     allStorage()
        # """
        # localstorage = await page.evaluate(javascript_func2, force_expr=True)
        # print(localstorage)

        self.cookie = []
        for c in self.cookie_jar:
            d = {
                "name": c.name,
                "value": c.value,
                "expires": c.expires,
                "path": c.path,
                "domain": c.domain,
            }
            self.cookie.append(d)
            await page.setCookie(d)

        # 後の解析のためにAsyncHTMLSession を通す
        self.session = AsyncHTMLSession()
        self.session._browser = browser
        response = await self.session.get(url, headers=self.headers, cookies=self.cookie_jar)
        response.raise_for_status()
        await response.html.arender(sleep=2)

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

    async def _async_get(self, request_url_str: str) -> Response:
        response = await self.session.get(request_url_str, headers=self.headers, cookies=self.cookie_jar)
        response.raise_for_status()
        await response.html.arender(sleep=2)
        return response

    def get(self, request_url_str: str) -> Response:
        url = URL(request_url_str)
        return self.loop.run_until_complete(self._async_get(url.original_url))

    @classmethod
    async def get_cookies_from_oauth(cls, username: Username, password: Password, top_url: URL, headers: dict) -> "SkebSession":
        """ツイッターログインを行いSkebページで使うcookiesを取得する

        pyppeteerを通してheadless chromeを操作する

        Returns:
            SkebSession: アクセスに使うセッション
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

        # ローカルストレージ情報を取り出す
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
        local_storage = await page.evaluate(javascript_func, force_expr=True)

        # 取得したローカルストレージ情報を保存
        slsp = Path("./config/skeb_localstorage.ini")
        with slsp.open("w") as fout:
            for ls in local_storage:
                fout.write(ls + "\n")

        # 取得したトークンを保存
        stp = Path(SkebSession.SKEB_TOKEN_PATH)
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
        scp = Path(SkebSession.SKEB_COOKIE_PATH)
        with scp.open(mode="w") as fout:
            for c in cookies:
                requests_cookies.set(c["name"], c["value"], expires=c["expires"], path=c["path"], domain=c["domain"])
                fout.write(CookieToString(c) + "\n")

        return SkebSession(headers, requests_cookies, local_storage)

    @classmethod
    def create(cls, username: Username, password: Password, top_url: URL, headers: dict) -> "SkebSession":
        # アクセスに使用するクッキーファイル置き場
        scp = Path(SkebSession.SKEB_COOKIE_PATH)
        # アクセスに使用するローカルストレージファイル置き場
        slsp = Path(SkebSession.SKEB_LOCAL_STORAGE_PATH)

        if scp.exists() and slsp.exists():
            # ローカルストレージを読み込む
            local_storage = []
            with slsp.open(mode="r") as fin:
                for line in fin:
                    if line == "":
                        break
                    local_storage.append(line)

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
            # if(SkebSession.is_valid_cookies(top_url, headers, cookies, token)):
            #     return SkebSession(cookies, headers, token)
            # else:
            #     logger.error("Getting Skeb Cookie is failed.")
            return SkebSession(headers, cookies, local_storage)

        # クッキーファイルがない場合、または有効なクッキーではなかった場合
        # 認証してCookiesを取得する
        loop = asyncio.new_event_loop()
        skeb_session = loop.run_until_complete(SkebSession.get_cookies_from_oauth(username, password, top_url, headers))

        # logger.info(f"Getting Skeb token is success: {token}")
        logger.info("Getting Skeb Cookie is success.")

        # 取得したクッキーを保存
        # get_cookies_from_oauth内で保存される
        # with scp.open("w") as fout:
        #     fout.write(skeb_cookie)

        return skeb_session


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
