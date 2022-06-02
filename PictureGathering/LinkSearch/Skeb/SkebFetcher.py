# coding: utf-8
import asyncio
import urllib.parse
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from random import random

import pyppeteer

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.Skeb.SkebDownloader import SkebDownloader
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebSourceList import SkebSourceList
from PictureGathering.LinkSearch.Skeb.SkebToken import SkebToken
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class SkebFetcher(FetcherBase):
    token: SkebToken
    base_path: Path

    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

    TOP_URL = "https://skeb.jp/"

    def __init__(self, username: Username, password: Password, base_path: Path):
        super().__init__()

        if not isinstance(username, Username):
            raise TypeError("username is not Username.")
        if not isinstance(password, Password):
            raise TypeError("password is not Password.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path is not Path.")

        object.__setattr__(self, "token", self.get_token(username, password))
        object.__setattr__(self, "base_path", base_path)

    async def _get_token_from_oauth(self, twitter_id: str, twitter_password: str) -> SkebToken:
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
            if (self.TOP_URL + "callback") in response.url:
                urls.append(response.url)
        page.on("response", lambda response: asyncio.ensure_future(ResponseListener(response)))

        # トップページに遷移
        await asyncio.gather(page.goto(self.TOP_URL), page.waitForNavigation())
        content = await page.content()
        cookies = await page.cookies()
        logger.info("Skeb Top Page loaded.")

        # 右上のログインボタンを押下
        # 不可視の別ボタンがある？ようなのでセレクタで該当した2つ目のタグを操作する
        # selector = "body > div > div > div > header > nav > div > div.navbar-menu > div > div > button"
        selector = 'button[class="button is-twitter"]'
        login_btn = await page.querySelectorAll(selector)
        if len(login_btn) != 2 or not login_btn[1]:
            logger.error("Twitter Login failed.")
            return ""
        await asyncio.gather(login_btn[1].click(), page.waitForNavigation())
        content = await page.content()
        cookies = await page.cookies()
        logger.info("Twitter Login Page loaded.")

        # ツイッターログイン情報を入力し、3-Leg認証を進める
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="session[username_or_email]"]'
        await page.type(selector, twitter_id)
        await page.waitFor(random.random() * 3 * 1000)
        selector = 'input[name="session[password]"]'
        await page.type(selector, twitter_password)
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
            logger.error("Getting Skeb token is failed.")
            return ""
        logger.info("Twitter oauth success.")

        # コールバックURLからtokenを切り出す
        callback_url = urls[0]
        q = urllib.parse.urlparse(callback_url).query
        qs = urllib.parse.parse_qs(q)
        token = qs.get("token", [""])[0]

        return SkebToken(token)

    def get_token(self, username: Username, password: Password) -> SkebToken:
        """トークン取得
        """
        # アクセスに使用するトークンファイル置き場
        SKEB_TOKEN_PATH = "./config/skeb_token.ini"
        stp = Path(SKEB_TOKEN_PATH)

        # トークンを取得する
        auth_success = False
        token = ""
        if stp.exists():
            # トークンファイルがある場合読み込み
            with stp.open("r") as fin:
                token = SkebToken(fin.read())

            # 有効なトークンか確認する
            # 実際にアクセスして確認するので負荷を考えるとチェックするかどうかは微妙
            # if(not self.IsValidToken(token)):
            #     logger.error("Getting Skeb token is failed.")
            #     return (None, False)
            return token

        # トークンファイルがない場合、または有効なトークンではなかった場合
        # 認証してtokenを取得する
        loop = asyncio.new_event_loop()
        token = loop.run_until_complete(self._get_token_from_oauth(username.name, password.password))

        logger.info(f"Getting Skeb token is success: {token}")

        # 取得したトークンを保存
        with stp.open("w") as fout:
            fout.write(token)

        return token

    def is_target_url(self, url: URL) -> bool:
        return SkebURL.is_valid(url.original_url)

    def run(self, url: URL) -> None:
        skeb_url = SkebURL.create(url)
        source_list = SkebSourceList.create(skeb_url, URL(self.TOP_URL), self.token)
        save_directory_path = SkebSaveDirectoryPath.create(skeb_url, self.base_path)
        result = SkebDownloader(skeb_url, source_list, save_directory_path, self.HEADERS).result


if __name__ == "__main__":
    import configparser
    import logging.config
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["skeb"].getboolean("is_skeb_trace"):
        fetcher = SkebFetcher(Username(config["skeb"]["twitter_id"]), Password(config["skeb"]["twitter_password"]), base_path)
        # イラスト（複数）
        work_url = "https://skeb.jp/@matsukitchi12/works/25"
        fetcher.run(work_url)
