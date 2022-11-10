# coding: utf-8
import asyncio
import logging.config
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from logging import INFO, getLogger
from pathlib import Path
import pyppeteer
from requests_html import AsyncHTMLSession, HTMLResponse

from PictureGathering.Screenshot.URL import URL

logger = getLogger(__name__)
logger.setLevel(INFO)


class Screenshot():
    RETRY_NUM = 5
    URL_PATTERN = r"^https?://twitter.com/([a-zA-Z0-9_/:%#$&\?\(\)~\.=\+\-]+?)/status/([a-zA-Z0-9_/:%#$&\?\(\)~\.=\+\-]+?)/.*$"

    def __init__(self, url: URL, save_directory_path: Path):
        self.is_valid(url, save_directory_path)

        self.url = url
        self.save_directory_path = save_directory_path
        self.save_directory_path.mkdir(parents=True, exist_ok=True)

        matched = re.findall(self.URL_PATTERN, self.url.non_query_url)[0]
        self.screen_name = matched[0]
        self.tweet_id = matched[1]
        self.save_file_name = f"{self.screen_name}_{self.tweet_id}.png"
        self.save_full_path = self.save_directory_path / self.save_file_name

    @classmethod
    def is_valid(cls, url: URL, save_directory_path: Path) -> bool:
        if not isinstance(url, URL):
            raise ValueError("argument url is not URL.")
        if not isinstance(save_directory_path, Path):
            raise ValueError("argument save_directory_path is not Path.")
        if re.search(cls.URL_PATTERN, url.non_query_url) is None:
            raise ValueError("argument url is not valid URL.")
        return True

    async def take_screenshot(self):
        if self.save_full_path.is_file():
            logger.info(f"{self.url.non_query_url} -> exist.")
            return

        browser = await pyppeteer.launch({
            "headless": True,
            "handleSIGINT": False,
            "handleSIGTERM": False,
            "handleSIGHUP": False,
            "ignoreHTTPSErrors": True,
        })

        for i in range(self.RETRY_NUM):
            try:
                page = await browser.newPage()
                await page.goto(self.url.non_query_url, waitUntil="networkidle0")
                await asyncio.sleep(1.0)

                content = await page.content()
                if "<title>Page not found / Twitter</title>" in content:
                    logger.warning(f"{self.url.non_query_url} -> not found, failed.")
                    break
                if "<title>Tweet / Twitter</title>" in content:
                    logger.warning(f"{self.url.non_query_url} -> limited tweet, failed.")
                    break

                await page.setViewport({"width": 1920, "height": 1080})
                await page.screenshot(path=str(self.save_full_path), fullPage=True)

                logger.info(f"{self.url.non_query_url} -> done.")
                await page.close()
                break
            except Exception:
                logger.warning(f"retry ({i+1}/{self.RETRY_NUM}) ...")
                await asyncio.sleep(1.0)
        else:
            logger.error("exceed RETRY_NUM.")
            # logger.error(traceback.format_exc())
            logger.warning(f"{self.url.non_query_url} -> failed.")
        await browser.close()

    @classmethod
    def create(cls, url: str, save_directory_path: str) -> "Screenshot":
        arg_url = URL(url)
        arg_path = Path(save_directory_path)
        return Screenshot(arg_url, arg_path)

    @classmethod
    def take_screenshot_for_all_urls(cls, urls: list[str], save_directory_path: str):
        def worker(url: str, save_directory_path: str):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            ss = Screenshot.create(url, save_directory_path)
            loop.run_until_complete(ss.take_screenshot())

        logger.info("Taking screenshot -> start.")
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="thread") as executor:
            futures = []
            for url in urls:
                futures.append(executor.submit(worker, url, save_directory_path))
                pass
            # print([f.result() for f in futures])
        logger.info("Taking screenshot -> done.")


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        if "__main__" not in name:
            getLogger(name).disabled = True

    urls = [
        # "https://twitter.com/_shift4869/status/1589482360793223168/photo/1",
        # "https://twitter.com/_shift4869/status/1589520249719640064/photo/1",
        # "https://twitter.com/_shift4869/status/invalid_url/photo/1",
        # "https://twitter.com/v_shift9738/status/1589214677971894273/photo/1",
        "https://twitter.com/machismo_p/status/1589262804707856384/photo/1",
        # "https://twitter.com/naga_U_/status/1589050050201915392/photo/1",
    ]
    save_directory_path = Path("./PictureGathering/Screenshot/")

    Screenshot.take_screenshot_for_all_urls(urls, save_directory_path)
