# coding: utf-8
import asyncio
from http.client import HTTPResponse
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


@dataclass(frozen=True)
class SkebSession():
    """skebセッション

    通常の接続ではページがうまく取得できないので
    クッキーとローカルストレージを予め設定したページセッションを用いる
    """
    cookies: requests.cookies.RequestsCookieJar  # 接続時に使うクッキー
    local_storage: list[str]                     # 接続時に使うローカルストレージ
    session: ClassVar[AsyncHTMLSession]          # 非同期セッション
    loop: ClassVar[asyncio.AbstractEventLoop]    # イベントループ

    # 接続時に使用するヘッダー
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
    # skebトップページ
    TOP_URL = "https://skeb.jp/"
    # クッキーファイルパス
    SKEB_COOKIE_PATH = "./config/skeb_cookie.ini"
    # ローカルストレージファイルパス
    SKEB_LOCAL_STORAGE_PATH = "./config/skeb_localstorage.ini"

    def __post_init__(self) -> None:
        """初期化処理
        """
        # 引数チェック
        self._is_valid_args()

        # イベントループ設定
        # 一つのものを使い回す
        object.__setattr__(self, "loop", asyncio.new_event_loop())

        # クッキーとローカルストレージをセットしたセッションを保持する
        session = self.loop.run_until_complete(self._get_session())
        object.__setattr__(self, "session", session)

        # 正しくセッションが作成されたか確認
        if not self._is_valid_session():
            raise ValueError("SkebSession: session setting failed.")

    @property
    def headers(self) -> dict:
        return SkebSession.HEADERS

    def _is_valid_args(self) -> bool:
        """属性の型チェック

        簡易的にクッキーとローカルストレージのキーも調べる

        Returns:
            bool: 問題なければTrue

        Raise:
            TypeError: 属性の型が不正な場合
            ValueError: クッキーまたはローカルストレージに想定されるキーが含まれていない場合
        """
        # 属性型チェック
        if not isinstance(self.cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("cookies is not requests.cookies.RequestsCookieJar, invalid SkebSession.")
        if not isinstance(self.local_storage, list):
            raise TypeError("local_storage is not list, invalid SkebSession.")

        # ローカルストレージに（最低限）必要なキーが含まれているか確認
        if not any(["user" in s for s in self.local_storage]):
            raise ValueError("local_storage is invalid, not included 'user'.")
        if not any(["token" in s for s in self.local_storage]):
            raise ValueError("local_storage is invalid, not included 'token'.")

        # クッキーに（最低限）必要なキーが含まれているか確認
        if not any([c.name == "_interslice_session" for c in self.cookies]):
            raise ValueError("cookies is invalid, not included '_interslice_session'.")
        if not any([c.name == "_ga" for c in self.cookies]):
            raise ValueError("cookies is invalid, not included '_ga'.")
        return True

    def _is_valid_session(self) -> bool:
        """セッションの正当性チェック

        クッキーとローカルストレージが正しく設定されている場合
        トップページからaccountページへのリンクが取得できる
        右上のアイコンマウスオーバー時に展開されるリストから
        「アカウント」メニューがあるかどうかを見ている

        Returns:
            bool: 正しくページが取得できたらTrue, 不正ならFalse
        """
        response: Response = self.get(self.TOP_URL)
        response.raise_for_status()

        a_tags = response.html.find("a")
        for a_tag in a_tags:
            account_href = a_tag.attrs.get("href", "")
            full_text = a_tag.full_text
            if "/account" in account_href and "アカウント" == full_text:
                return True
        return False

    async def _get_session(self) -> AsyncHTMLSession:
        """セッション取得

        クッキーとローカルストレージを設定したpyppeteerブラウザに紐づける

        Returns:
            AsyncHTMLSession: 非同期セッション
        """
        url = self.TOP_URL

        # クッキーとローカルストレージをセットしたpyppeteerブラウザを設定する
        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()
        await page.goto(url)

        # ローカルストレージをセットする
        javascript_func1 = "localStorage.setItem('{}', '{}');"
        for line in self.local_storage:
            elements = re.split(" : |\n", line)
            key = elements[0]
            value = elements[1]
            await page.evaluate(javascript_func1.format(key, value))

        # クッキーをセットする
        for c in self.cookies:
            d = {
                "name": c.name,
                "value": c.value,
                "expires": c.expires,
                "path": c.path,
                "domain": c.domain,
            }
            await page.setCookie(d)

        # AsyncHTMLSession を作成してブラウザに紐づける
        session = AsyncHTMLSession()
        session._browser = browser
        return session

    async def _async_get(self, request_url_str: str) -> Response:
        """セッションを使ってレスポンスを取得する

        Returns:
            Response: レンダリング済htmlページレスポンス
        """
        response = await self.session.get(request_url_str, headers=self.headers, cookies=self.cookies)
        response.raise_for_status()
        await response.html.arender(sleep=2)
        return response

    def get(self, request_url_str: str) -> Response:
        """セッションを使ってレスポンスを取得する

        イベントループはself.loopを使い回す

        Returns:
            Response: レンダリング済htmlページレスポンス
        """
        url = URL(request_url_str)
        return self.loop.run_until_complete(self._async_get(url.original_url))

    @classmethod
    async def get_cookies_from_oauth(cls, username: Username, password: Password, top_url: URL, headers: dict) -> "SkebSession":
        """ツイッターログインを行いSkebページで使うクッキーとローカルストレージを取得する

        pyppeteerを通してheadless chromeを操作する
        取得したクッキーとローカルストレージはそれぞれファイルに保存する

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
            raise ValueError("Getting Skeb session is failed.")
        logger.info("Twitter oauth success.")

        # コールバックURLからtokenを切り出す
        # callback_url = urls[0]
        # q = urllib.parse.urlparse(callback_url).query
        # qs = urllib.parse.parse_qs(q)
        # token = qs.get("token", [""])[0]

        # ローカルストレージ情報を取り出す
        localstorage_get_js = """
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
        local_storage = await page.evaluate(localstorage_get_js, force_expr=True)

        # ローカルストレージ情報が取得できたことを確認
        if not local_storage:
            raise ValueError("Getting Skeb session is failed.")
        logger.info("Getting local_storage success.")

        # 取得したローカルストレージ情報を保存
        slsp = Path("./config/skeb_localstorage.ini")
        with slsp.open("w") as fout:
            for ls in local_storage:
                fout.write(ls + "\n")

        # クッキー保存を試みる
        # クッキー情報が取得できたことを確認
        if not cookies:
            raise ValueError("Getting Skeb session is failed.")
        logger.info("Getting cookies success.")

        # クッキー解析用
        def CookieToString(c):
            name = c["name"]
            value = c["value"]
            expires = c["expires"]
            path = c["path"]
            domain = c["domain"]
            return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}"'

        # クッキー情報をファイルに保存する
        # 取得したクッキーはRequestsCookieJarのインスタンスではないので変換もここで行う
        requests_cookies = requests.cookies.RequestsCookieJar()
        scp = Path(SkebSession.SKEB_COOKIE_PATH)
        with scp.open(mode="w") as fout:
            for c in cookies:
                requests_cookies.set(c["name"], c["value"], expires=c["expires"], path=c["path"], domain=c["domain"])
                fout.write(CookieToString(c) + "\n")

        return SkebSession(requests_cookies, local_storage)

    @classmethod
    def create(cls, username: Username, password: Password) -> "SkebSession":
        """SkebSessionインスタンス作成

        Args:
            username (Username): ユーザーID(紐づいているツイッターID)
            password (Password): ユーザーIDのパスワード(ツイッターパスワード)

        Returns:
            SkebSession: SkebSessionインスタンス
        """
        # トップページURL
        top_url = URL(SkebSession.TOP_URL)
        # 接続に使うヘッダー
        headers = SkebSession.HEADERS
        # アクセスに使用するクッキーファイル置き場
        scp = Path(SkebSession.SKEB_COOKIE_PATH)
        # アクセスに使用するローカルストレージファイル置き場
        slsp = Path(SkebSession.SKEB_LOCAL_STORAGE_PATH)

        # 以前に接続した時のクッキーとローカルストレージのファイルが存在しているならば
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

            # SkebSessionインスタンスを生成する
            # 正当性は生成時に確認される
            # エラーが発生した場合は以降の処理に続いて
            # 再度クッキーとローカルストレージを取得することを試みる
            try:
                skeb_session = SkebSession(cookies, local_storage)
                logger.info("Getting Skeb session is success.")
                return skeb_session
            except Exception:
                pass

        # クッキーとローカルストレージのファイルがない場合
        # または有効なセッションが取得できなかった場合
        # 認証してクッキーとローカルストレージの取得を試みる
        loop = asyncio.new_event_loop()
        skeb_session = loop.run_until_complete(SkebSession.get_cookies_from_oauth(username, password, top_url, headers))

        logger.info("Getting Skeb session is success.")

        # 取得したクッキーとローカルストレージを保存する
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
