# coding: utf-8
import asyncio
import random
import re
from dataclasses import dataclass
from logging import INFO, getLogger
from typing import ClassVar

import pyppeteer
from requests.models import Response
from requests_html import HTML, AsyncHTMLSession, Element

from PictureGathering.noapi.Cookies import Cookies
from PictureGathering.noapi.LocalStorage import LocalStorage
from PictureGathering.noapi.Password import Password
from PictureGathering.noapi.Username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class TwitterSession():
    """Twitterセッション

    通常の接続ではページがうまく取得できないので
    クッキーとローカルストレージを予め設定したページセッションを用いる
    """
    username: Username           # ユーザーネーム(@除外)
    password: Password           # パスワード
    cookies: Cookies             # 接続時に使うクッキー
    local_storage: LocalStorage  # 接続時に使うローカルストレージ
    session: ClassVar[AsyncHTMLSession]        # 非同期セッション
    loop: ClassVar[asyncio.AbstractEventLoop]  # イベントループ

    # 接続時に使用するヘッダー
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
    # トップページ
    TOP_URL = "https://twitter.com/"
    # ログインページ
    LOGIN_URL = "https://twitter.com/i/flow/login"
    # Likesページのテンプレート
    LIKES_URL_TEMPLATE = "https://twitter.com/{}/likes"
    # RT取得用のTLページのテンプレート
    RETWEET_URL_TEMPLATE = "https://twitter.com/{}/with_replies"

    def __post_init__(self) -> None:
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
            self.loop.close()
            raise ValueError("TwitterSession: session setting failed.")

    @property
    def headers(self) -> dict:
        return TwitterSession.HEADERS

    def _is_valid_args(self) -> bool:
        """属性の型チェック

        Returns:
            bool: 問題なければTrue

        Raise:
            TypeError: 属性の型が不正な場合
        """
        # 属性型チェック
        if not isinstance(self.username, Username):
            raise TypeError("username is not Username, invalid TwitterSession.")
        if not isinstance(self.password, Password):
            raise TypeError("password is not Password, invalid TwitterSession.")
        if not isinstance(self.cookies, Cookies):
            raise TypeError("cookies is not Cookies, invalid TwitterSession.")
        if not isinstance(self.local_storage, LocalStorage):
            raise TypeError("local_storage is not LocalStorage, invalid TwitterSession.")
        return True

    def _is_valid_session(self) -> bool:
        """セッションの正当性チェック

        Returns:
            bool: 正しくLikesページが取得できたらTrue, 不正ならFalse
        """
        url = self.LIKES_URL_TEMPLATE.format(self.username.name)
        response: Response = self.loop.run_until_complete(self.get(url))
        response.raise_for_status()
        html: HTML = response.html
        self.loop.run_until_complete(html.arender(sleep=2))

        # 取得結果の確認
        # 左下のアカウントメニューの領域を参照する
        # プロフィール画像に設定されているaltを取得し
        # username.name と一致するかどうかで判定する
        try:
            a_tags: list[Element] = html.find("a")
            a_tag = [dt for dt in a_tags if "プロフィール" in dt.attrs.get("aria-label", "")][0]
            return "/" + self.username.name == a_tag.attrs.get("href", "")
        except Exception as e:
            pass
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
        for line in self.local_storage.local_storage:
            elements = re.split(" : |\n", line)
            key = elements[0]
            value = elements[1]
            await page.evaluate(javascript_func1.format(key, value), force_expr=True)

        # クッキーをセットする
        for c in self.cookies.cookies:
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
        url = self.LIKES_URL_TEMPLATE.format(self.username.name)
        await asyncio.gather(
            page.goto(url),
            page.waitForNavigation()
        )

        # AsyncHTMLSession を作成してブラウザに紐づける
        session = AsyncHTMLSession()
        session._browser = browser

        return session

    async def _async_get(self, request_url: str) -> Response:
        """セッションを使ってレスポンスを取得する

        Args:
            request_url (str): getするURL

        Returns:
            Response: htmlページレスポンス
        """
        response: Response = await self.session.get(request_url, headers=self.headers, cookies=self.cookies.cookies)
        response.raise_for_status()
        return response

    async def get(self, request_url_str: str) -> Response:
        """セッションを使ってレスポンスを取得する

        Args:
            request_url_str (str): getするURL文字列

        Returns:
            Response: htmlページレスポンス
        """
        return await self._async_get(request_url_str)

    async def prepare(self) -> None:
        """セッションを使う準備

        リファラの関係？でTOPページを取得してレンダリングを試みる
        """
        response: Response = await self._async_get(self.TOP_URL)
        await response.html.arender()

    @classmethod
    async def get_cookies_from_oauth(cls, username: Username, password: Password) -> tuple[Cookies, LocalStorage]:
        """ツイッターログインを行いクッキーとローカルストレージを取得する

        pyppeteerを通してheadless chromeを操作する
        取得したクッキーとローカルストレージはそれぞれファイルに保存する

        Args:
            username (Username): ユーザーID(ツイッターID, @除外)
            password (Password): ユーザーIDのパスワード(ツイッターIDのパスワード)

        Returns:
            Cookies: ログイン後のクッキー
            LocalStorage: ログイン後のローカルストレージ
        """
        login_url = TwitterSession.LOGIN_URL

        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()
        logger.info("Login flow start.")

        # ログインページに遷移
        await asyncio.gather(
            page.goto(login_url),
            page.waitForNavigation()
        )
        content = await page.content()
        cookies = await page.cookies()
        logger.info("Twitter Login Page loaded.")

        # ツイッターログイン情報を入力し、ログインする
        # ツイッターIDを入力
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="text"]'
        await page.type(selector, username.name)
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'div[style="color: rgb(255, 255, 255);"]'
        await page.click(selector)
        logger.info("Twitter Login Page username input.")

        # TODO::短時間に何度もログインするとIDを聞かれる
        # await page.waitFor(random.random() * 3 * 1000)
        # selector = 'input[name="password"]'
        # await page.type(selector, password.password)
        # await asyncio.gather(page.click(selector), page.waitForNavigation())

        # パスワードを入力
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="password"]'
        await page.type(selector, password.password)
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'div[style="color: rgb(255, 255, 255);"]'
        await asyncio.gather(page.click(selector), page.waitForNavigation())
        logger.info("Twitter Login Page password input.")

        # TODO::ツイッターログインが成功かどうか調べる

        await page.waitFor(3000)
        content = await page.content()
        cookies = await page.cookies()

        logger.info("Twitter login is success.")

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
        RETRY_NUM = 5
        local_storage = []
        for _ in range(RETRY_NUM):
            local_storage = await page.evaluate(localstorage_get_js, force_expr=True)
            if local_storage:
                break
        else:
            # ローカルストレージ情報が取得できたことを確認
            # 空白もあり得る？
            # raise ValueError("Getting local_storage is failed.")
            pass

        # 取得したローカルストレージ情報を保存
        LocalStorage.save(local_storage)
        logger.info("Getting local_storage is success.")

        # クッキー情報が取得できたことを確認
        if not cookies:
            raise ValueError("Getting cookies is failed.")

        # クッキー情報をファイルに保存する
        Cookies.save(cookies)
        logger.info("Getting cookies is success.")

        return Cookies.create(), LocalStorage.create()

    @classmethod
    def create(cls, username: Username, password: Password) -> "TwitterSession":
        """TwitterSessionインスタンス作成

        Args:
            username (Username): ユーザーID(紐づいているツイッターID)
            password (Password): ユーザーIDのパスワード(ツイッターパスワード)

        Returns:
            TwitterSession: TwitterSessionインスタンス
        """
        logger.info("Getting Twitter session -> start")

        # 以前に接続した時のクッキーとローカルストレージのファイルが存在しているならば
        RETRY_NUM = 5
        for i in range(RETRY_NUM):
            try:
                cookies = Cookies.create()
                local_storage = LocalStorage.create()
                twitter_session = TwitterSession(username, password, cookies, local_storage)
                logger.info("Getting Twitter session -> done")
                return twitter_session
            except FileNotFoundError as e:
                logger.info(f"No exist Cookies and LocalStorage file.")
                break
            except Exception as e:
                logger.info(f"Cookies and LocalStorage loading retry ... ({i+1}/{RETRY_NUM}).")
        else:
            logger.info(f"Retry num is exceed RETRY_NUM={RETRY_NUM}.")

        # クッキーとローカルストレージのファイルがない場合
        # または有効なセッションが取得できなかった場合
        # 認証してクッキーとローカルストレージの取得を試みる
        loop = asyncio.new_event_loop()
        cookies, local_storage = loop.run_until_complete(
            TwitterSession.get_cookies_from_oauth(username, password)
        )
        loop.close()
        twitter_session = TwitterSession(username, password, cookies, local_storage)
        logger.info("Getting Twitter session -> done")
        return twitter_session


if __name__ == "__main__":
    import configparser
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    try:
        username = config["twitter_noapi"]["username"]
        password = config["twitter_noapi"]["password"]
        twitter_session = TwitterSession.create(Username(username), Password(password))
        twitter_session.loop.run_until_complete(twitter_session.prepare())
    except Exception as e:
        logger.exception(e)
