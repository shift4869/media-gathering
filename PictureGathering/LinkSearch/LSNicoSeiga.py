# coding: utf-8
import configparser
import logging.config
import re
from logging import INFO, getLogger
from pathlib import Path
from time import sleep
import bs4

import emoji
import requests
import urllib
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from PictureGathering.LinkSearch import LinkSearchBase

logger = getLogger("root")
logger.setLevel(INFO)


class LSNicoSeiga(LinkSearchBase.LinkSearchBase):
    def __init__(self, email: str, password: str, base_path: str):
        """ニコニコ静画から画像を取得するためのクラス

        Notes:
            ニコニコ静画の漫画機能には対応していない

        Args:
            base_path (str): 保存先ディレクトリのベースとなるパス

        Attributes:
            base_path (str): 保存先ディレクトリのベースとなるパス
        """
        super().__init__()
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

        self.session = None
        self.auth_success = False
        self.base_path = base_path
        self.session, self.auth_success = self.Login(email, password)

        if not self.auth_success:
            exit(-1)

    def Login(self, email: str, password: str) -> tuple[requests.Session, bool]:
        """セッションを開始し、ログインする

        Args:
            email (str): ニコニコユーザーIDとして登録したemailアドレス
            password (str): ニコニコユーザーIDのパスワード

        Returns:
            session, auth_success (requests.Session, boolean): 認証済みセッションと認証結果の組
        """
        # セッション開始
        session = requests.session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        # ログイン
        NS_LOGIN_ENDPOINT = "https://account.nicovideo.jp/api/v1/login?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url=&mail_or_tel=1"
        params = {
            "mail_tel": email,
            "password": password,
        }
        response = session.post(NS_LOGIN_ENDPOINT, data=params, headers=self.headers)
        response.raise_for_status()

        return (session, True)

    def IsTargetUrl(self, url: str) -> bool:
        """URLがニコニコ静画のURLかどうか判定する

        Note:
            想定URL形式：https://seiga.nicovideo.jp/seiga/im*******

        Args:
            url (str): 判定対象url

        Returns:
            boolean: ニコニコ静画作品ページURLならTrue、そうでなければFalse
        """
        # クエリを除去
        url_path = Path(urllib.parse.urlparse(url).path)
        url = urllib.parse.urljoin(url, url_path.name)

        pattern = r"^https://seiga.nicovideo.jp/seiga/(im)[0-9]+$"
        regex = re.compile(pattern)
        f1 = not (regex.findall(url) == [])

        pattern = r"^http://nico.ms/(im)[0-9]+$"
        regex = re.compile(pattern)
        f2 = not (regex.findall(url) == [])

        return f1 or f2

    def GetIllustId(self, url: str) -> int:
        """ニコニコ静画作品ページURLからイラストIDを取得する

        Args:
            url (str): ニコニコ静画作品ページURL

        Returns:
            int: 成功時 イラストID、失敗時 -1
        """
        if not self.IsTargetUrl(url):
            return -1

        tail = Path(url).name
        if tail[:2] != "im":
            return -1

        illust_id = int(tail[2:])
        return illust_id

    def GetIllustInfo(self, illust_id: int) -> tuple[int, str]:
        """ニコニコ静画情報を取得する

        Args:
            illust_id (int): 対象作品ID

        Returns:
            author_id, illust_title (int, str): 作者IDと作品タイトルの組
        """
        # 静画情報取得APIエンドポイント
        NS_IMAGE_INFO_API_ENDPOINT = "http://seiga.nicovideo.jp/api/illust/info?id="

        # 静画情報を取得する
        info_url = NS_IMAGE_INFO_API_ENDPOINT + str(illust_id)
        response = self.session.get(info_url, headers=self.headers)
        response.raise_for_status()

        # 静画情報解析
        author_id = -1
        illust_title = ""
        try:
            soup = BeautifulSoup(response.text, "lxml-xml")
            xml_image = soup.find("image")
            author_id = xml_image.find("user_id").text
            illust_title = xml_image.find("title").text
        except Exception:
            author_id = -1
            illust_title = ""
        return (int(author_id), illust_title)

    def GetAuthorName(self, author_id: int) -> str:
        """ニコニコ静画の作者名を取得する

        Args:
            author_id (int): 作者ID

        Returns:
            author_name (str): 作者名
        """
        # 作者情報取得APIエンドポイント
        NS_USERNAME_API_ENDPOINT = "https://seiga.nicovideo.jp/api/user/info?id="

        # 作者情報を取得する
        username_info_url = NS_USERNAME_API_ENDPOINT + str(author_id)
        response = self.session.get(username_info_url, headers=self.headers)
        response.raise_for_status()

        # 作者情報解析
        author_name = ""
        try:
            soup = BeautifulSoup(response.text, "lxml-xml")
            xml_user = soup.find("user")
            author_name = xml_user.find("nickname").text
        except Exception:
            author_name = ""
        return author_name

    def GetSourceURL(self, illust_id: int) -> str:
        """ニコニコ静画の画像直リンクを取得する

        Args:
            illust_id (int): 対象作品ID

        Returns:
            source_url (str): 画像直リンク
        """
        # ニコニコ静画ページ取得APIエンドポイント
        NS_IMAGE_SOUECE_API_ENDPOINT = "http://seiga.nicovideo.jp/image/source?id="

        # ニコニコ静画ページ取得（画像表示部分のみ）
        source_page_url = NS_IMAGE_SOUECE_API_ENDPOINT + str(illust_id)
        response = self.session.get(source_page_url, headers=self.headers)
        response.raise_for_status()

        # ニコニコ静画ページを解析して画像直リンクを取得する
        source_url = ""
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            div_contents = soup.find_all("div", id="content")
            for div_content in div_contents:
                div_illust = div_content.find(class_="illust_view_big")
                source_url = div_illust.get("data-src")
                break
        except Exception:
            source_url = ""
        return source_url
    
    def GetExtFromBytes(self, data: bytes) -> str:
        """バイナリデータ配列から拡張子を判別する

        Args:
            data (bytes): 対象byte列

        Returns:
            ext (str): 拡張子（'.xxx'）, エラー時（'.invalid'）
        """
        ext = ".invalid"

        # プリフィックスを得るのに短すぎるbyte列の場合はエラー
        if len(data) < 8:
            return ".invalid"

        # 拡張子判別
        if bool(re.search(b"^\xff\xd8", data[:2])):
            # jpgは FF D8 で始まる
            ext = ".jpg"
        elif bool(re.search(b"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", data[:8])):
            # pngは 89 50 4E 47 0D 0A 1A 0A で始まる
            ext = ".png"
        elif bool(re.search(b"^\x47\x49\x46\x38", data[:4])):
            # gifは 47 49 46 38 で始まる
            ext = ".gif"
        return ext

    def DownloadIllusts(self, url: str, base_path: str) -> int:
        """ニコニコ静画作品ページURLからダウンロードする

        Notes:
            静画画像実体（リダイレクト先）
            http://seiga.nicovideo.jp/image/source?id={illust_id}
            静画情報（xml）
            http://seiga.nicovideo.jp/api/illust/info?id={illust_id}
            ユーザーネーム取得（xml）※user_idは静画情報に含まれる
            https://seiga.nicovideo.jp/api/user/info?id={user_id}

        Args:
            url (str): ニコニコ静画作品ページURL
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """

        illust_id = self.GetIllustId(url)
        author_id, illust_title = self.GetIllustInfo(illust_id)
        author_name = self.GetAuthorName(author_id)

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", author_name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(author_id)
        illust_title = regex.sub("", illust_title)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

        # 画像保存先パスを取得
        save_directory_path = self.MakeSaveDirectoryPath(author_name, author_id, illust_title, illust_id, base_path)
        sd_path = Path(save_directory_path)
        if save_directory_path == "":
            return -1

        # 画像直リンクを取得
        source_url = self.GetSourceURL(illust_id)
        if source_url == "":
            return -1

        # {作者名}ディレクトリ作成
        sd_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイルが既に存在しているか調べる
        # 拡張子は実際にDLするまで分からない
        # そのため、対象フォルダ内にillust_idを含むファイル名を持つファイルが存在するか調べることで代用する
        name = sd_path.name
        pattern = "^.*\(" + str(illust_id) + "\).*$"
        same_name_list = [f for f in sd_path.parent.glob("**/*") if re.search(pattern, str(f))]

        # 既に存在しているなら再DLしないでスキップ
        if same_name_list:
            name = same_name_list[0].name
            logger.info("Download seiga illust: " + name + " -> exist")
            return 1

        # 画像DL
        response = self.session.get(source_url, headers=self.headers)
        response.raise_for_status()

        # 拡張子取得
        ext = self.GetExtFromBytes(response.content)

        # ファイル名設定
        name = "{}{}".format(sd_path.name, ext)

        # {作者名}ディレクトリ直下に保存
        with Path(sd_path.parent / name).open(mode="wb") as fout:
            fout.write(response.content)
        logger.info("Download seiga illust: " + name + " -> done")

        return 0

    def MakeSaveDirectoryPath(self, author_name: str, author_id: int, illust_title: str, illust_id: int, base_path: str) -> str:
        """保存先ディレクトリパスを生成する

        Notes:
            保存先ディレクトリパスの形式は以下とする
            ./{作者名}({作者ID})/{イラストタイトル}({イラストID})/
            既に{作者ID}が一致するディレクトリがある場合はそのディレクトリを使用する
            （{作者名}変更に対応するため）

        Args:
            author_name (str): 作者名
            author_id (int): 作者ID
            illust_title (str): 作品名
            illust_id (int): 作者ID
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            str: 成功時 保存先ディレクトリパス、失敗時 空文字列
        """
        if author_name == "" or author_id == -1 or illust_title == "" or illust_id == -1:
            return ""

        # 既に{作者nijieID}が一致するディレクトリがあるか調べる
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

    def Process(self, url: str) -> int:
        # クエリを除去
        url_path = Path(urllib.parse.urlparse(url).path)
        url = urllib.parse.urljoin(url, url_path.name)

        res = self.DownloadIllusts(url, self.base_path)
        return 0 if (res in [0, 1]) else -1


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    if config["nico_seiga"].getboolean("is_seiga_trace"):
        ns_cont = LSNicoSeiga(config["nico_seiga"]["email"], config["nico_seiga"]["password"], config["nico_seiga"]["save_base_path"])
        work_url = "https://seiga.nicovideo.jp/seiga/im5360137"
        res = ns_cont.Process(work_url)
    pass
