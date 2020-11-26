# coding: utf-8
import configparser
import logging.config
import os
import re
from logging import INFO, getLogger
from time import sleep
from typing import List

from pixivpy3 import *

logger = getLogger("root")
logger.setLevel(INFO)


class PixivAPIController:
    def __init__(self, username, password):
        """非公式pixivAPI利用クラス

        Args:
            username (str): APIを利用するpixivユーザーID
            password (str): APIを利用するpixivユーザーIDのパスワード

        Attributes:
            username (str): APIを利用するpixivユーザーID
            password (str): APIを利用するpixivユーザーIDのパスワード
            api (PixivAPI): 非公式pixivAPI（全体操作）
            aapi (AppPixivAPI): 非公式pixivAPI（詳細操作）
        """
        self.username = username
        self.password = password
        self.api = PixivAPI()
        self.aapi = AppPixivAPI()
        try:
            self.api.login(username, password)
            self.aapi.login(username, password)
        except Exception:
            exit(-1)

    def GetIllustId(self, url):
        """pixiv作品ページURLからイラストIDを取得する

        Note:
            想定URL形式：https://www.pixiv.net/artworks/********

        Args:
            url (str): pixiv作品ページURL

        Returns:
            int: イラストID
        """
        _, tail = os.path.split(url)
        illust_id = int(tail)
        return illust_id

    def GetIllustURLs(self, url):
        """pixiv作品ページURLからイラストへの直リンクを取得する

        Note:
            漫画ページの場合、それぞれのページについて
            全てURLを取得するため返り値はList[str]となる

        Args:
            url (str): pixiv作品ページURL

        Returns:
            List[str]: 成功時 pixiv作品のイラストへの直リンクlist、失敗時 空リスト
        """
        illust_id = self.GetIllustId(url)
        if illust_id == -1:
            return []

        # イラスト情報取得
        # json_result = aapi.illust_detail(illust_id)
        # illust = json_result.illust
        works = self.api.works(illust_id)
        if works.status != "success":
            return []
        work = works.response[0]

        illust_urls = []
        if work.is_manga:  # 漫画形式
            for page_info in work.metadata.pages:
                illust_urls.append(page_info.image_urls.large)
        else:  # 一枚絵
            illust_urls.append(work.image_urls.large)

        return illust_urls

    def MakeSaveDirectoryPath(self, url):
        """pixiv作品ページURLから作者情報を取得し、
           保存先ディレクトリパスを生成する

        Notes:
            保存先ディレクトリパスの形式は以下とする
            ./{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/

        Args:
            url (str): pixiv作品ページURL

        Returns:
            str: 保存先ディレクトリパス
        """
        illust_id = self.GetIllustId(url)
        if illust_id == -1:
            return []

        works = self.api.works(illust_id)
        if works.status != "success":
            return []
        work = works.response[0]

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regix = re.compile(r'[\\/:*?"<>|]')
        author_name = regix.sub("", work.user.name)
        author_id = int(work.user.id)
        illust_title = regix.sub("", work.title)

        res = "./{}({})/{}({})/".format(author_name, author_id, illust_title, illust_id)
        return res

    def DownloadIllusts(self, urls, save_directory_path):
        """pixiv作品ページURLからダウンロードする

        Notes:
            リファラの関係？で直接requestできないためAPIを通して保存する
            save_directory_pathは
            {base_path}/{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/の形を想定している
            漫画形式の場合：
                save_directory_pathを使用し
                /{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/{3ケタの連番}.{拡張子}の形式で保存
            イラスト一枚絵の場合：
                save_directory_pathからイラストタイトルとイラストIDを取得し
                /{作者名}({作者pixivID})/{イラストタイトル}({イラストID}).{拡張子}の形式で保存

        Args:
            urls (List[str]): イラスト直リンクURL（GetIllustURLsの返り値）
                              len(urls)が1の場合はイラスト一枚絵と判断する
            save_directory_path (str): 保存先フルパス（{base_path}/{MakeSaveDirectoryPathの返り値}）

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        pages = len(urls)
        if pages > 1:  # 漫画形式
            dirname = os.path.basename(os.path.dirname(save_directory_path))
            logger.info("Download pixiv illust: [" + dirname + "] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if os.path.exists(save_directory_path):
                logger.info("\t\t: exist -> skip")
                return 1

            os.makedirs(save_directory_path, exist_ok=True)
            for i, url in enumerate(urls):
                root, ext = os.path.splitext(url)
                name = "{:03}{}".format(i + 1, ext)
                self.aapi.download(url, path=save_directory_path, name=name)
                logger.info("\t\t: " + name + " -> done({}/{})".format(i + 1, pages))
                sleep(0.5)
        elif pages == 1:  # 一枚絵
            head, tail = os.path.split(save_directory_path[:-1])
            save_directory_path = head + "/"
            os.makedirs(save_directory_path, exist_ok=True)

            url = urls[0]
            root, ext = os.path.splitext(url)
            name = "{}{}".format(tail, ext)
            
            # 既に存在しているなら再DLしないでスキップ
            if os.path.exists(os.path.join(save_directory_path, name)):
                logger.info("Download pixiv illust: " + name + " -> exist")
                return 1

            self.aapi.download(url, path=save_directory_path, name=name)
            logger.info("Download pixiv illust: " + name + " -> done")
        else:  # エラー
            return -1
        return 0


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    if config["pixiv"].getboolean("is_pixiv_trace"):
        pa_cont = PixivAPIController(config["pixiv"]["username"], config["pixiv"]["password"])
        work_url = "https://www.pixiv.net/artworks/85861864"
        urls = pa_cont.GetIllustURLs(work_url)
        sd_path = pa_cont.MakeSaveDirectoryPath(work_url)
        save_directory_path = os.path.join(config["pixiv"]["save_base_path"], sd_path)
        pa_cont.DownloadIllusts(urls, save_directory_path)
    pass
