# coding: utf-8
import configparser
import logging.config
import os
import re
import traceback
import urllib.parse
import zipfile
from logging import INFO, getLogger
from pathlib import Path
from time import sleep

import requests
from bs4 import BeautifulSoup

logger = getLogger("root")
logger.setLevel(INFO)


class NijieController:
    def __init__(self, email: str, password: str):
        # User-Agent偽装用ヘッダ
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

        self.cookies = None
        self.auth_success = False
        self.cookies, self.auth_success = self.Login(email, password)

        if not self.auth_success:
            exit(-1)
    
    def Login(self, email: str, password: str):
        """nijieページにログインし、ログイン情報を保持したクッキーを返す

        Args:
            email (str): nijieユーザー名（メールアドレス）
            password (str): nijieユーザーPW

        Returns:
            cookies: ログイン情報を保持したクッキー
        """
        # ログイン情報を保持するクッキー置き場
        NIJIE_COOKIE_PATH = "./config/nijie_cookie.ini"
        ncp = Path(NIJIE_COOKIE_PATH)

        cookies = requests.cookies.RequestsCookieJar()
        auth_success = False
        if ncp.is_file():
            # クッキーが既に存在している場合
            # クッキーを読み込む
            with ncp.open(mode="r") as fin:
                for line in fin:
                    if line == "":
                        break

                    nc = {}
                    elements = re.split("[,\n]", line)
                    for element in elements:
                        element = element.strip().replace('"', "")  # 左右の空白とダブルクォートを除去
                        if element == "":
                            break

                        key, val = element.split("=")  # =で分割
                        nc[key] = val

                    cookies.set(nc["name"], nc["value"], expires=nc["expires"], path=nc["path"], domain=nc["domain"])

            # トップページをGETしてクッキーが有効かどうか調べる
            top_url = "http://nijie.info/index.php"
            res = requests.get(top_url, headers=self.headers, cookies=cookies)
            res.raise_for_status()

            # 返ってきたレスポンスがトップページのものかチェック
            # 不正なクッキーだと年齢確認画面に飛ばされる（titleとurlから判別可能）
            auth_success = res.status_code == 200 and res.url == top_url and "ニジエ - nijie" in res.text

        if not auth_success:
            # クッキーが存在していない場合、または有効なクッキーではなかった場合

            # 年齢確認で「はい」を選択したあとのURLにアクセス
            res = requests.get("https://nijie.info/age_jump.php?url=", headers=self.headers)
            res.raise_for_status()

            # 認証用URLクエリを取得する
            qs = urllib.parse.urlparse(res.url).query
            qd = urllib.parse.parse_qs(qs)
            url = qd["url"][0]

            # ログイン時に必要な情報
            payload = {
                "email": email,
                "password": password,
                "save": "on",
                "ticket": "",
                "url": url
            }

            # ログインする
            login_url = "https://nijie.info/login_int.php"
            res = requests.post(login_url, data=payload)
            res.raise_for_status()

            # 以降はクッキーに認証情報が含まれているため、これを用いて各ページをGETする
            cookies = res.cookies

            # クッキー解析用
            def CookieToString(c):
                name = c.name
                value = c.value
                expires = c.expires
                path = c.path
                domain = c.domain
                return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}"'

            # クッキー情報を保存する
            with ncp.open(mode="w") as fout:
                for c in cookies:
                    fout.write(CookieToString(c) + "\n")

        return (cookies, auth_success)

    @classmethod
    def IsNijieURL(cls, url: str) -> bool:
        """URLがnijieのURLかどうか判定する

        Note:
            想定URL形式：http://nijie.info/view.php?id=******
                      ：http://nijie.info/view_popup.php?id=******

        Args:
            url (str): 判定対象url

        Returns:
            boolean: nijie作品ページURLならTrue、そうでなければFalse
        """
        pattern = r"^http://nijie.info/view.php\?id=[0-9]*$"
        regex = re.compile(pattern)
        f1 = not (regex.findall(url) == [])

        pattern = r"^http://nijie.info/view_popup.php\?id=[0-9]*$"
        regex = re.compile(pattern)
        f2 = not (regex.findall(url) == [])

        return f1 or f2

    def GetIllustId(self, url: str) -> int:
        """nijie作品ページURLからイラストIDを取得する

        Args:
            url (str): nijie作品ページURL

        Returns:
            int: 成功時 イラストID、失敗時 -1
        """
        if not self.IsNijieURL(url):
            return -1

        qs = urllib.parse.urlparse(url).query
        qd = urllib.parse.parse_qs(qs)
        illust_id = int(qd["id"][0])
        return illust_id

    def DownloadIllusts(self, url: str, base_path: str) -> list[str]:
        illust_id = self.GetIllustId(url)
        if illust_id == -1:
            return []

        # 作品詳細ページをGET
        illust_url = "http://nijie.info/view_popup.php?id={}".format(illust_id)
        res = requests.get(illust_url, headers=self.headers, cookies=self.cookies)
        res.raise_for_status()

        # BeautifulSoupを用いてhtml解析を行う
        soup = BeautifulSoup(res.text, "html.parser")
        urls, author_name, author_id, illust_name = self.DetailPageAnalysis(soup)

        # 保存先ディレクトリを取得
        save_directory_path = self.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path)
        sd_path = Path(save_directory_path)

        pages = len(urls)
        if pages > 1:  # 漫画形式、うごイラ複数
            dirname = sd_path.parent.name
            logger.info("Download nijie illust: [" + dirname + "] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return 1

            # {作者名}/{作品名}ディレクトリ作成
            sd_path.mkdir(parents=True, exist_ok=True)

            # 画像をDLする
            # ファイル名は3桁の連番
            for i, url in enumerate(urls):
                res = requests.get(url, headers=self.headers, cookies=self.cookies)
                res.raise_for_status()

                ext = Path(url).suffix
                file_name = "{:03}{}".format(i, ext)
                with Path(sd_path / file_name).open(mode="wb") as fout:
                    fout.write(res.content)

                logger.info("\t\t: " + file_name + " -> done({}/{})".format(i + 1, pages))
                sleep(0.5)
        elif pages == 1:  # 一枚絵、うごイラ一枚
            # {作者名}ディレクトリ作成
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル名設定
            url = urls[0]
            ext = Path(url).suffix
            name = "{}{}".format(sd_path.name, ext)

            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / name).is_file():
                logger.info("Download nijie illust: " + name + " -> exist")
                return 1

            # 画像をDLする
            res = requests.get(url, headers=self.headers, cookies=self.cookies)
            res.raise_for_status()

            # {作者名}ディレクトリ直下に保存
            with Path(sd_path.parent / name).open(mode="wb") as fout:
                fout.write(res.content)
            logger.info("Download nijie illust: " + name + " -> done")

        else:  # エラー
            return -1

        return 0

    def DetailPageAnalysis(self, soup) -> list[str]:
        # html構造解析
        urls = []

        # メディアへの直リンクを取得する
        # メディアは画像（jpg, png）、うごイラ（gif, mp4）などがある
        # メディアが置かれているdiv
        div_imgs = soup.find_all("div", id="img_filter")
        for div_img in div_imgs:
            # うごイラがないかvideoタグを探す
            video_s = div_img.find_all("video")
            video_url = ""
            for video in video_s:
                if video.get("src") is not None:
                    video_url = "http:" + video["src"]
                    break
            if video_url != "":
                # videoタグがあった場合はaタグは探さない
                # 詳細ページへのリンクしか持っていないので
                urls.append(video_url)
                continue

            # 一枚絵、漫画がないかaタグを探す
            a_s = div_img.find_all("a")
            img_url = ""
            for a in a_s:
                if a.get("href") is not None:
                    img_url = "http:" + a.img["src"]
                    break
            if img_url != "":
                urls.append(img_url)

        # 作者IDは1枚目の画像ファイル名に含まれている
        author_id = int(Path(urls[0]).name.split("_")[0])

        # 作品タイトル、作者名はページタイトルから取得する
        title_tag = soup.find("title")
        title = title_tag.text.split("|")
        illust_name = title[0].strip()
        author_name = title[1].strip()
        return (urls, author_name, author_id, illust_name)

    def MakeSaveDirectoryPath(self, author_name, author_id, illust_name, illust_id, base_path: str) -> str:
        """nijie作品ページURLから作者情報を取得し、
           保存先ディレクトリパスを生成する

        Notes:
            保存先ディレクトリパスの形式は以下とする
            ./{作者名}({作者nijieID})/{イラストタイトル}({イラストID})/
            既に{作者nijieID}が一致するディレクトリがある場合はそのディレクトリを使用する
            （{作者名}変更に対応するため）

        Args:
            url (str)      : nijie作品ページURL
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            str: 成功時 保存先ディレクトリパス、失敗時 空文字列
        """
        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", author_name)
        author_id = int(author_id)
        illust_title = regex.sub("", illust_name)

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


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    nc = NijieController(config["nijie"]["email"], config["nijie"]["password"])
    # illust_id = 251267  # 一枚絵
    # illust_id = 251197  # 漫画
    # illust_id = 414793  # うごイラ一枚
    illust_id = 409587  # うごイラ複数

    illust_url = "http://nijie.info/view_popup.php?id={}".format(illust_id)
    nc.DownloadIllusts(illust_url, config["nijie"]["save_base_path"])

    pass
