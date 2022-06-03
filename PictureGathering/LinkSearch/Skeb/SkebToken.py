# coding: utf-8
import asyncio
import urllib.parse
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from random import random

import pyppeteer

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class SkebToken():
    """SkebToken

    Returns:
        SkebToken: SkebTokenを表すValueObject
    """
    token: str

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.token, str):
            raise TypeError("token is not string, invalid SkebToken.")
        if self.token == "":
            raise ValueError("empty string, invalid SkebToken")
        return True

    @classmethod
    async def _get_token_from_oauth(cls, username: Username, password: Password, top_url: URL) -> "SkebToken":
        """ツイッターログインを行いSkebページで使うtokenを取得する

        Notes:
            pyppeteerを通してheadless chromeを操作する

        Args:
            twitter_id (str): SkebユーザーIDとして登録したツイッターID
            twitter_password (str): SkebユーザーIDとして登録したツイッターのパスワード

        Returns:
            str: アクセスに使うトークン
        """
        token = ""
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
            raise ValueError("Getting Skeb token is failed.")
        logger.info("Twitter oauth success.")

        # コールバックURLからtokenを切り出す
        callback_url = urls[0]
        q = urllib.parse.urlparse(callback_url).query
        qs = urllib.parse.parse_qs(q)
        token = qs.get("token", [""])[0]

        return SkebToken(token)

    @classmethod
    def get(cls, username: Username, password: Password, top_url: URL) -> "SkebToken":
        """トークン取得
        """
        # アクセスに使用するトークンファイル置き場
        SKEB_TOKEN_PATH = "./config/skeb_token.ini"
        stp = Path(SKEB_TOKEN_PATH)

        # トークンを取得する
        token = ""
        if stp.exists():
            # トークンファイルがある場合読み込み
            with stp.open("r") as fin:
                token = fin.read()

            # 有効なトークンか確認する
            # 実際にアクセスして確認するので負荷を考えるとチェックするかどうかは微妙
            # if(not self.IsValidToken(token)):
            #     logger.error("Getting Skeb token is failed.")
            #     return (None, False)
            return SkebToken(token)

        # トークンファイルがない場合、または有効なトークンではなかった場合
        # 認証してtokenを取得する
        loop = asyncio.new_event_loop()
        token = loop.run_until_complete(SkebToken._get_token_from_oauth(username, password, top_url))

        logger.info(f"Getting Skeb token is success: {token}")

        # 取得したトークンを保存
        with stp.open("w") as fout:
            fout.write(token)

        return SkebToken(token)


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = SkebToken.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
