# coding: utf-8
import configparser
import logging.config
import re
from logging import INFO, getLogger
from pathlib import Path
from time import sleep
from typing import List

import emoji
import requests
from PIL import Image
from pixivpy3 import *

from PictureGathering import LinkSearchBase

logger = getLogger("root")
logger.setLevel(INFO)


class LSPixiv(LinkSearchBase.LinkSearchBase):
    def __init__(self, username: str, password: str, base_path: str):
        """非公式pixivAPI利用クラス

        Args:
            username (str): APIを利用するpixivユーザーID
            password (str): APIを利用するpixivユーザーIDのパスワード

        Attributes:
            api (PixivAPI): 非公式pixivAPI（全体操作）
            aapi (AppPixivAPI): 非公式pixivAPI（詳細操作）
            auth_success (boolean): API認証が正常に完了したかどうか
        """
        super().__init__()
        self.api = None
        self.aapi = None
        self.auth_success = False
        self.api, self.aapi, self.auth_success = self.Login(username, password)

        if not self.auth_success:
            exit(-1)

        self.base_path = base_path

    def Login(self, username: str, password: str) -> tuple[PixivAPI, AppPixivAPI, bool]:
        """非公式pixivAPIインスタンスを生成し、ログインする

        Note:
            前回ログインからのrefresh_tokenが残っている場合はそれを使用する

        Args:
            username (str): APIを利用するpixivユーザーID
            password (str): APIを利用するpixivユーザーIDのパスワード

        Returns:
            (api, aapi, auth_success) (PixivAPI, AppPixivAPI, boolean): 非公式pixivAPI（全体操作, 詳細操作, 認証結果）
        """
        api = PixivAPI()
        aapi = AppPixivAPI()

        # 前回ログインからのrefresh_tokenが残っているか調べる
        REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
        rt_path = Path(REFRESH_TOKEN_PATH)
        auth_success = False
        if rt_path.is_file():
            refresh_token = ""
            with rt_path.open(mode="r") as fin:
                refresh_token = str(fin.read())
            try:
                # 2021/06/15 reCAPTCHAを回避する
                # https://github.com/upbit/pixivpy/issues/171#issuecomment-860264788
                class CustomAdapter(requests.adapters.HTTPAdapter):
                    def init_poolmanager(self, *args, **kwargs):
                        # When urllib3 hand-rolls a SSLContext, it sets 'options |= OP_NO_TICKET'
                        # and CloudFlare really does not like this. We cannot control this behavior
                        # in urllib3, but we can just pass our own standard context instead.
                        import ssl
                        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                        ctx.load_default_certs()
                        ctx.set_alpn_protocols(["http/1.1"])
                        return super().init_poolmanager(*args, **kwargs, ssl_context=ctx)

                api.requests = requests.Session()
                api.requests.mount("https://", CustomAdapter())
                api.auth(refresh_token=refresh_token)

                aapi.requests = requests.Session()
                aapi.requests.mount("https://", CustomAdapter())
                aapi.auth(refresh_token=refresh_token)

                auth_success = (api.access_token is not None) and (aapi.access_token is not None)
            except Exception:
                pass

        if not auth_success:
            # refresh_tokenが存在していない場合、または有効なトークンではなかった場合
            try:
                # api.login(username, password)
                # aapi.login(username, password)
                # auth_success = (api.access_token is not None) and (aapi.access_token is not None)
                # 2021/05/20 現在PixivPyで新規ログインができない
                # https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362
                # https://gist.github.com/upbit/6edda27cb1644e94183291109b8a5fde
                logger.info(f"not found {REFRESH_TOKEN_PATH}")
                logger.info("please access to make refresh_token.ini for below way:")
                logger.info("https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362")
                logger.info(" or ")
                logger.info("https://gist.github.com/upbit/6edda27cb1644e94183291109b8a5fde")
                logger.info("process abort")
                return (None, None, False)

                # refresh_tokenを保存
                refresh_token = api.refresh_token
                with rt_path.open(mode="w") as fout:
                    fout.write(refresh_token)
            except Exception:
                return (None, None, False)

        return (api, aapi, auth_success)

    def IsTargetUrl(self, url: str) -> bool:
        """URLがpixivのURLかどうか判定する

        Note:
            想定URL形式：https://www.pixiv.net/artworks/********

        Args:
            url (str): 判定対象url

        Returns:
            boolean: pixiv作品ページURLならTrue、そうでなければFalse
        """
        pattern = r"^https://www.pixiv.net/artworks/[0-9]+$"
        regex = re.compile(pattern)
        return not (regex.findall(url) == [])

    def GetIllustId(self, url: str) -> int:
        """pixiv作品ページURLからイラストIDを取得する

        Args:
            url (str): pixiv作品ページURL

        Returns:
            int: 成功時 イラストID、失敗時 -1
        """
        if not self.IsTargetUrl(url):
            return -1

        tail = Path(url).name
        illust_id = int(tail)
        return illust_id

    def GetIllustURLs(self, url: str) -> List[str]:
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

    def MakeSaveDirectoryPath(self, url: str, base_path: str) -> str:
        """pixiv作品ページURLから作者情報を取得し、
           保存先ディレクトリパスを生成する

        Notes:
            保存先ディレクトリパスの形式は以下とする
            ./{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/
            既に{作者pixivID}が一致するディレクトリがある場合はそのディレクトリを使用する
            （{作者名}変更に対応するため）

        Args:
            url (str)      : pixiv作品ページURL
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            str: 成功時 保存先ディレクトリパス、失敗時 空文字列
        """
        illust_id = self.GetIllustId(url)
        if illust_id == -1:
            return ""

        works = self.api.works(illust_id)
        if works.status != "success":
            return ""
        work = works.response[0]

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", work.user.name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(work.user.id)
        illust_title = regex.sub("", work.title)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

        # 既に{作者pixivID}が一致するディレクトリがあるか調べる
        IS_SEARCH_AUTHOR_ID = True
        sd_path = ""
        save_path = Path(base_path)
        if IS_SEARCH_AUTHOR_ID:
            filelist = []
            filelist_tp = [(sp.stat().st_mtime, sp.name) for sp in save_path.glob("*") if sp.is_dir()]
            for mtime, path in sorted(filelist_tp, reverse=True):
                filelist.append(path)

            regex = re.compile(r'.*\(([0-9]*)\)$')
            for dir_name in filelist:
                result = regex.match(dir_name)
                if result:
                    ai = result.group(1)
                    if ai == str(author_id):
                        sd_path = "./{}/{}({})/".format(dir_name, illust_title, illust_id)
                        break
        
        if sd_path == "":
            sd_path = "./{}({})/{}({})/".format(author_name, author_id, illust_title, illust_id)

        save_directory_path = save_path / sd_path
        return str(save_directory_path)

    def DownloadIllusts(self, urls: List[str], save_directory_path: str) -> int:
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
            うごイラの場合：
                save_directory_pathからイラストタイトルとイラストIDを取得し
                /{作者名}({作者pixivID})/{イラストタイトル}({イラストID}).{拡張子}の形式で扉絵（1枚目）を保存
                /{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/{3ケタの連番}.{拡張子}の形式で各フレームを保存
                /{作者名}({作者pixivID})/{イラストタイトル}({イラストID}).gifとしてアニメーションgifを保存

        Args:
            urls (List[str]): イラスト直リンクURL（GetIllustURLsの返り値）
                              len(urls)が1の場合はイラスト一枚絵と判断する
            save_directory_path (str): 保存先フルパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        pages = len(urls)
        sd_path = Path(save_directory_path)
        if pages > 1:  # 漫画形式
            dirname = sd_path.parent.name
            logger.info("Download pixiv illust: [" + dirname + "] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return 1

            sd_path.mkdir(parents=True, exist_ok=True)
            for i, url in enumerate(urls):
                ext = Path(url).suffix
                name = "{:03}{}".format(i + 1, ext)
                self.aapi.download(url, path=str(sd_path), name=name)
                logger.info("\t\t: " + name + " -> done({}/{})".format(i + 1, pages))
                sleep(0.5)
        elif pages == 1:  # 一枚絵
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            url = urls[0]
            ext = Path(url).suffix
            name = "{}{}".format(sd_path.name, ext)
            
            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / name).is_file():
                logger.info("Download pixiv illust: " + name + " -> exist")
                return 1

            self.aapi.download(url, path=str(sd_path.parent), name=name)
            logger.info("Download pixiv illust: " + name + " -> done")

            # うごイラの場合は追加で保存する
            regex = re.compile(r'.*\(([0-9]*)\)$')
            result = regex.match(sd_path.name)
            if result:
                illust_id = int(result.group(1))
                self.DownloadUgoira(illust_id, str(sd_path.parent))
        else:  # エラー
            return -1
        return 0
    
    def DownloadUgoira(self, illust_id: int, base_path: str) -> int:
        """うごイラをダウンロードする

        Notes:
            {base_path}/{イラストタイトル}({イラストID})/以下に各フレーム画像を保存
            {base_path}/{イラストタイトル}({イラストID}).gifとしてアニメーションgifを保存

        Args:
            illust_id (int): イラストID
            base_path (str): 保存先ベースフルパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        works = self.api.works(illust_id)
        if works.status != "success":
            return -1
        work = works.response[0]

        if work.type != "ugoira":
            return 1  # うごイラではなかった
        
        logger.info("\t\t: ugoira download -> see below ...")

        # サニタイズ
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", work.user.name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(work.user.id)
        illust_title = regex.sub("", work.title)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

        # うごイラの各フレームを保存するディレクトリを生成
        sd_path = Path(base_path) / "./{}({})/".format(illust_title, illust_id)
        sd_path.mkdir(parents=True, exist_ok=True)

        # うごイラの情報をaapiから取得する
        # アドレスは以下の形になっている
        # https://{...}/{イラストID}_ugoira{画像の番号}.jpg
        illust = self.aapi.illust_detail(illust_id)
        ugoira = self.aapi.ugoira_metadata(illust_id)
        ugoira_url = illust.illust.meta_single_page.original_image_url.rsplit("0", 1)
        frames_len = len(ugoira.ugoira_metadata.frames)
        delays = [f["delay"] for f in ugoira.ugoira_metadata.frames]

        # 各フレーム画像DL
        for i in range(frames_len):
            frame_url = ugoira_url[0] + str(i) + ugoira_url[1]
            self.aapi.download(frame_url, path=str(sd_path))
            logger.info("\t\t: " + frame_url.rsplit("/", 1)[1] + " -> done({}/{})".format(i + 1, frames_len))
            sleep(0.5)
        
        # DLした各フレーム画像のパスを収集
        frames = []
        fr = [(sp.stat().st_mtime, str(sp)) for sp in sd_path.glob("*") if sp.is_file()]
        for mtime, path in sorted(fr, reverse=False):
            frames.append(path)

        # うごイラをanimated gifとして保存
        first = Image.open(frames[0])
        first = first.copy()
        image_list = []
        for f in frames[1:]:
            buf = Image.open(f)
            buf = buf.copy()
            # buf = buf.quantize(method=0)  # ディザリング抑制
            image_list.append(buf)
        name = "{}({}).gif".format(illust_title, illust_id)
        first.save(
            fp=str(Path(base_path) / name),
            save_all=True,
            append_images=image_list,
            optimize=False,
            duration=delays,
            loop=0
        )
        logger.info("\t\t: animated gif saved: " + name + " -> done")
        return 0

    def Process(self, url: str) -> int:
        urls = self.GetIllustURLs(url)
        save_directory_path = self.MakeSaveDirectoryPath(url, self.base_path)
        res = self.DownloadIllusts(urls, save_directory_path)
        return 0 if (res in [0, 1]) else -1


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    if config["pixiv"].getboolean("is_pixiv_trace"):
        pa_cont = LSPixiv(config["pixiv"]["username"], config["pixiv"]["password"], config["pixiv"]["save_base_path"])
        work_url = "https://www.pixiv.net/artworks/86704541"
        pa_cont.Process(work_url)
    pass
