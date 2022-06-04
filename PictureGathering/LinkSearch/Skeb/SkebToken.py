# coding: utf-8
import asyncio
import random
import urllib.parse
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

from requests_html import HTMLSession
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
    def is_valid_token(self, top_url: URL, token_str: str, headers: dict) -> bool:
        """トークンが有効かどうか判定する

        tokenが有効かどうか検証する
        実際にアクセスするため負荷がかかる

        Args:
            token_str (str): 検証対象のトークン

        Returns:
            bool: tokenが有効なトークンならTrue、有効でなければFalse
        """
        if token_str == "":
            return False

        # コールバックURLを取得する
        request_url = f"{top_url.non_query_url}callback?path=/&token={token_str}"

        # コールバック後のトップページを取得するリクエストを行う
        session = HTMLSession()
        response = session.get(request_url, headers=headers)
        response.raise_for_status()
        response.html.render(sleep=2)

        # トークンが有効な場合はトップページからaccountページへのリンクが取得できる
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
    async def get_token_from_oauth(cls, username: Username, password: Password, top_url: URL) -> "SkebToken":
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
    def get(cls, username: Username, password: Password, top_url: URL, headers: dict) -> "SkebToken":
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
            if(SkebToken.is_valid_token(top_url, token, headers)):
                return SkebToken(token)
            else:
                logger.error("Getting Skeb token is failed.")

        # トークンファイルがない場合、または有効なトークンではなかった場合
        # 認証してtokenを取得する
        loop = asyncio.new_event_loop()
        token = loop.run_until_complete(SkebToken.get_token_from_oauth(username, password, top_url)).token

        logger.info(f"Getting Skeb token is success: {token}")

        # 取得したトークンを保存
        with stp.open("w") as fout:
            fout.write(token)

        return SkebToken(token)


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
