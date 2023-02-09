# coding: utf-8
from dataclasses import dataclass
from httplib2 import Response
from logging import INFO, getLogger
from pathlib import Path
from typing import ClassVar
import asyncio
import random
import re

from requests_html import AsyncHTMLSession
import pyppeteer
import requests.cookies
import requests.utils

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class TwitterSession():
    """Twitterセッション

    通常の接続ではページがうまく取得できないので
    クッキーとローカルストレージを予め設定したページセッションを用いる
    """
    username: str  # ユーザーネーム(@除外)
    password: str  # パスワード
    cookies: requests.cookies.RequestsCookieJar  # 接続時に使うクッキー
    local_storage: list[str]                     # 接続時に使うローカルストレージ
    session: ClassVar[AsyncHTMLSession]          # 非同期セッション
    loop: ClassVar[asyncio.AbstractEventLoop]    # イベントループ

    # 接続時に使用するヘッダー
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
    # トップページ
    TOP_URL = "https://twitter.com/"
    # ログインページ
    LOGIN_URL = "https://twitter.com/i/flow/login"
    # Likesページのテンプレート
    LIKES_URL_TEMPLATE = "https://twitter.com/{}/likes"

    # クッキーファイルパス
    TWITTER_COOKIE_PATH = "./config/twitter_cookie.ini"
    # ローカルストレージファイルパス
    TWITTER_LOCAL_STORAGE_PATH = "./config/twitter_localstorage.ini"

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
        # if not self._is_valid_session():
        #     raise ValueError("TwitterSession: session setting failed.")

    @property
    def headers(self) -> dict:
        return TwitterSession.HEADERS

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
        if not isinstance(self.username, str):
            raise TypeError("username is not str, invalid TwitterSession.")
        if not isinstance(self.password, str):
            raise TypeError("password is not str, invalid TwitterSession.")
        if not isinstance(self.cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("cookies is not requests.cookies.RequestsCookieJar, invalid TwitterSession.")
        if not isinstance(self.local_storage, list):
            raise TypeError("local_storage is not list, invalid TwitterSession.")

        # # ローカルストレージに（最低限）必要なキーが含まれているか確認
        # if not any(["user" in s for s in self.local_storage]):
        #     raise ValueError("local_storage is invalid, not included 'user'.")
        # if not any(["token" in s for s in self.local_storage]):
        #     raise ValueError("local_storage is invalid, not included 'token'.")
        # if not any(["cache-sprite-plyr" in s for s in self.local_storage]):
        #     raise ValueError("local_storage is invalid, not included 'cache-sprite-plyr'.")
        # if not any(["blockingUsers" in s for s in self.local_storage]):
        #     raise ValueError("local_storage is invalid, not included 'blockingUsers'.")

        # # クッキーに（最低限）必要なキーが含まれているか確認
        # if not any([c.name == "_interslice_session" for c in self.cookies]):
        #     raise ValueError("cookies is invalid, not included '_interslice_session'.")
        # if not any([c.name == "_ga" for c in self.cookies]):
        #     raise ValueError("cookies is invalid, not included '_ga'.")
        return True

    def _is_valid_session(self) -> bool:
        """セッションの正当性チェック

        Returns:
            bool: 正しくページが取得できたらTrue, 不正ならFalse
        """
        url = self.LIKES_URL_TEMPLATE.format(self.username)
        response: Response = self.get(url)
        response.raise_for_status()

        a_tags = response.html.find("time")
        if a_tags:
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
            await page.evaluate(javascript_func1.format(key, value), force_expr=True)

        # クッキーをセットする
        for c in self.cookies:
            d = {
                "name": c.name,
                "value": c.value,
                "expires": c.expires,
                "path": c.path,
                "domain": c.domain,
                "secure": bool(c.secure),
                "httpOnly": bool(c._rest["HttpOnly"])
            }
            await page.setCookie(d)

        # ローカルストレージとクッキーセット後にページ遷移できるか確認
        url = self.LIKES_URL_TEMPLATE.format(self.username)
        await asyncio.gather(
            page.goto(url),
            page.waitForNavigation()
        )

        # AsyncHTMLSession を作成してブラウザに紐づける
        session = AsyncHTMLSession()
        session._browser = browser

        return session

    async def _async_get(self, request_url_str: str) -> Response:
        """セッションを使ってレスポンスを取得する

        Args:
            request_url_str (str): getするURL文字列

        Returns:
            Response: レンダリング済htmlページレスポンス
        """
        response = await self.session.get(request_url_str, headers=self.headers, cookies=self.cookies)
        response.raise_for_status()
        # await response.html.arender(sleep=2)
        return response

    async def get(self, request_url_str: str) -> Response:
        """セッションを使ってレスポンスを取得する

        イベントループはself.loopを使い回す

        Args:
            request_url_str (str): getするURL文字列

        Returns:
            Response: レンダリング済htmlページレスポンス
        """
        return await self._async_get(request_url_str)

    async def prepare(self) -> None:
        """セッションを使う準備
        """
        response = await self.session.get(self.TOP_URL)
        await response.html.arender()

    @classmethod
    async def get_cookies_from_oauth(cls, username, password) -> tuple[requests.cookies.RequestsCookieJar, list[str]]:
        """ツイッターログインを行いTwitterページで使うクッキーとローカルストレージを取得する

        pyppeteerを通してheadless chromeを操作する
        取得したクッキーとローカルストレージはそれぞれファイルに保存する

        Args:
            username (Username): ユーザーID(ツイッターID)
            password (Password): ユーザーIDのパスワード(ツイッターIDのパスワード)

        Returns:
            requests.cookies.RequestsCookieJar: ログイン後のクッキー
            list[str]: ログイン後のローカルストレージ
        """
        login_url = TwitterSession.LOGIN_URL

        urls = []
        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()
        logger.info("Browsing start.")

        # THINK::レスポンスを監視してコールバックURLをキャッチする
        # async def ResponseListener(response):
        #     if (login_url + "callback") in response.url:
        #         urls.append(response.url)
        # page.on("response", lambda response: asyncio.ensure_future(ResponseListener(response)))

        # ログインページに遷移
        await asyncio.gather(
            page.goto(login_url),
            page.waitForNavigation()
        )
        content = await page.content()
        cookies = await page.cookies()
        logger.info("Twitter Top Page loaded.")

        # 右上のログインボタンを押下
        # 不可視の別ボタンがある？ようなのでセレクタで該当した2つ目のタグを操作する
        # selector = "body > div > div > div > header > nav > div > div.navbar-menu > div > div > button"
        # selector = 'button[class="button is-twitter"]'
        # login_btn = await page.querySelectorAll(selector)
        # if len(login_btn) != 2 or not login_btn[1]:
        #     raise ValueError("Twitter Login failed.")
        # await asyncio.gather(login_btn[1].click(), page.waitForNavigation())
        # content = await page.content()
        # cookies = await page.cookies()
        # logger.info("Twitter Login Page loaded.")

        # ツイッターログイン情報を入力し、ログインする
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[autocomplete="username"]'
        await page.type(selector, username)
        selector = 'div[style="color: rgb(255, 255, 255);"]'
        await page.click(selector)

        # TODO::短時間に何度もログインするとIDを聞かれる
        # await page.waitFor(random.random() * 3 * 1000)
        # selector = 'input[name="password"]'
        # await page.type(selector, password.password)
        # await asyncio.gather(page.click(selector), page.waitForNavigation())

        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="password"]'
        await page.type(selector, password)
        selector = 'div[style="color: rgb(255, 255, 255);"]'
        await asyncio.gather(page.click(selector), page.waitForNavigation())

        # TODO::ツイッターログインが成功かどうか調べる
        await page.waitFor(3000)
        content = await page.content()
        cookies = await page.cookies()

        logger.info("Twitter login success.")

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
            raise ValueError("Getting Twitter session is failed.")
        logger.info("Getting local_storage success.")

        # 取得したローカルストレージ情報を保存
        slsp = Path(TwitterSession.TWITTER_LOCAL_STORAGE_PATH)
        with slsp.open("w") as fout:
            for ls in local_storage:
                fout.write(ls + "\n")

        # クッキー保存を試みる
        # クッキー情報が取得できたことを確認
        if not cookies:
            raise ValueError("Getting Twitter session is failed.")
        logger.info("Getting cookies success.")

        # クッキー解析用
        def CookieToString(c):
            name = c["name"]
            value = c["value"]
            expires = c["expires"]
            path = c["path"]
            domain = c["domain"]
            httponly = c["httpOnly"]
            secure = c["secure"]
            return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}", httponly="{httponly}", secure="{secure}"'

        # クッキー情報をファイルに保存する
        # 取得したクッキーはRequestsCookieJarのインスタンスではないので変換もここで行う
        requests_cookies = requests.cookies.RequestsCookieJar()
        scp = Path(TwitterSession.TWITTER_COOKIE_PATH)
        with scp.open(mode="w") as fout:
            for c in cookies:
                requests_cookies.set(
                    c["name"],
                    c["value"],
                    expires=c["expires"],
                    path=c["path"],
                    domain=c["domain"],
                    secure=c["secure"],
                    rest={"HttpOnly": c["httpOnly"]})
                fout.write(CookieToString(c) + "\n")

        return requests_cookies, local_storage

    @classmethod
    def create(cls, username, password) -> "TwitterSession":
        """TwitterSessionインスタンス作成

        Args:
            username (Username): ユーザーID(紐づいているツイッターID)
            password (Password): ユーザーIDのパスワード(ツイッターパスワード)

        Returns:
            TwitterSession: TwitterSessionインスタンス
        """
        # アクセスに使用するクッキーファイル置き場
        scp = Path(TwitterSession.TWITTER_COOKIE_PATH)
        # アクセスに使用するローカルストレージファイル置き場
        slsp = Path(TwitterSession.TWITTER_LOCAL_STORAGE_PATH)

        # 以前に接続した時のクッキーとローカルストレージのファイルが存在しているならば
        if scp.exists() and slsp.exists():
            RETRY_NUM = 5
            for i in range(RETRY_NUM):
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

                            key, val = element.split("=", 1)  # =で分割
                            sc[key] = val

                        cookies.set(
                            sc["name"],
                            sc["value"],
                            expires=sc["expires"],
                            path=sc["path"],
                            domain=sc["domain"],
                            secure=bool(sc["secure"]),
                            rest={"HttpOnly": bool(sc["httponly"])}
                        )

                # TwitterSessionインスタンスを生成する
                # 正当性は生成時に確認される
                # エラーが発生した場合は以降の処理に続いて
                # 再度クッキーとローカルストレージを取得することを試みる
                try:
                    twitter_session = TwitterSession(username, password, cookies, local_storage)
                    # logger.info("Getting Twitter session is success.")
                    return twitter_session
                except Exception as e:
                    logger.info(f"Local_storage and cookies loading retry ... ({i+1}/{RETRY_NUM}).")
            else:
                logger.info(f"Retry num is exceed RETRY_NUM={RETRY_NUM}.")

        # クッキーとローカルストレージのファイルがない場合
        # または有効なセッションが取得できなかった場合
        # 認証してクッキーとローカルストレージの取得を試みる
        loop = asyncio.new_event_loop()
        cookies, local_storage = loop.run_until_complete(TwitterSession.get_cookies_from_oauth(username, password))
        twitter_session = TwitterSession(username, password, cookies, local_storage)

        return twitter_session


if __name__ == "__main__":
    import configparser
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    if config["twitter_noapi"].getboolean("is_twitter_noapi"):
        username = config["twitter_noapi"]["username"]
        password = config["twitter_noapi"]["password"]
        twitter_session = TwitterSession.create(username, password)

        # result = []
        # for i in range(2):
        #     with Path(f"./content_cache{i}.txt").open("r", encoding="utf8") as fin:
        #         json_dict = json.load(fin)
        #         result.append(json_dict)

        # all_tweets = []
        # for r in result:
        #     r1 = r["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"][0]
        #     entries = r1["entries"]
        #     for entry in entries:
        #         e1 = entry["content"].get("itemContent", {})
        #         if not e1:
        #             continue
        #         e2 = e1["tweet_results"]["result"]
        #         t = twitter_session.interpret_json(e2)
        #         if not t:
        #             continue
        #         all_tweets.extend(t)

        # for t in all_tweets:
        #     print(t["id_str"] + " : " + t["full_text"])

        # result = twitter_session.loop.run_until_complete(twitter_session.get_like_links())
        # pprint.pprint(result)

        # links = []
        # with Path("./cache.txt").open("r") as fin:
        #     for line in fin:
        #         links.append(line.strip())
        # result = twitter_session.loop.run_until_complete(twitter_session.get_media_url(links[0]))
        # pprint.pprint(result)
