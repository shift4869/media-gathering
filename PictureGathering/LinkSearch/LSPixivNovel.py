# coding: utf-8
import configparser
import logging.config
import urllib
import re
from logging import INFO, getLogger
from pathlib import Path

import emoji
from bs4 import BeautifulSoup
from pixivpy3 import *

from PictureGathering.LinkSearch import LinkSearchBase

logger = getLogger("root")
logger.setLevel(INFO)


class LSPixivNovel(LinkSearchBase.LinkSearchBase):
    def __init__(self, username: str, password: str, base_path: str):
        """非公式pixivAPI利用クラス

        Args:
            username (str): APIを利用するpixivユーザーID
            password (str): APIを利用するpixivユーザーIDのパスワード

        Attributes:
            aapi (AppPixivAPI): 非公式pixivAPI（詳細操作）
            auth_success (boolean): API認証が正常に完了したかどうか
        """
        super().__init__()
        self.aapi = None
        self.auth_success = False
        self.aapi, self.auth_success = self.Login(username, password)

        if not self.auth_success:
            exit(-1)

        self.base_path = base_path

    def Login(self, username: str, password: str) -> tuple[AppPixivAPI, bool]:
        """非公式pixivAPIインスタンスを生成し、ログインする

        Note:
            前回ログインからのrefresh_tokenが残っている場合はそれを使用する

        Args:
            username (str): APIを利用するpixivユーザーID
            password (str): APIを利用するpixivユーザーIDのパスワード

        Returns:
            (api, aapi, auth_success) (PixivAPI, AppPixivAPI, boolean): 非公式pixivAPI（全体操作, 詳細操作, 認証結果）
        """
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
                '''
                # 2021/10/14 python 3.10にてOpenSSL 1.1.1以降が必須になった影響？のためこの回避は使えなくなった
                # また、PixivPy側でデフォルトのユーザーエージェントが修正されたためreCAPTCHAも気にしなくて良くなった
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

                aapi.requests = requests.Session()
                aapi.requests.mount("https://", CustomAdapter())
                '''
                aapi.auth(refresh_token=refresh_token)

                auth_success = (aapi.access_token is not None)
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
                return (None, False)

                # refresh_tokenを保存
                refresh_token = api.refresh_token
                with rt_path.open(mode="w") as fout:
                    fout.write(refresh_token)
            except Exception:
                return (None, False)

        return (aapi, auth_success)

    def IsTargetUrl(self, url: str) -> bool:
        """URLがpixivノベル作品のURLかどうか判定する

        Note:
            想定URL形式：https://www.pixiv.net/novel/show.php?id=********

        Args:
            url (str): 判定対象url

        Returns:
            boolean: pixiv作品ページURLならTrue、そうでなければFalse
        """
        pattern = r"^https://www.pixiv.net/novel/show.php\?id=[0-9]+$"
        regex = re.compile(pattern)
        return not (regex.findall(url) == [])

    def GetNovelId(self, url: str) -> int:
        """pixiv作品ページURLからノベルIDを取得する

        Args:
            url (str): pixiv作品ページURL

        Returns:
            int: 成功時 ノベルID、失敗時 -1
        """
        if not self.IsTargetUrl(url):
            return -1

        q = urllib.parse.urlparse(url).query
        qs = urllib.parse.parse_qs(q)
        return int(qs.get("id", [-1])[0])

    def MakeSaveDirectoryPath(self, url: str, base_path: str) -> str:
        """pixiv作品ページURLから作者情報を取得し、
           保存先ディレクトリパスを生成する

        Notes:
            保存先ディレクトリパスの形式は以下とする
            ./{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID})/
            既に{作者pixivID}が一致するディレクトリがある場合はそのディレクトリを使用する
            （{作者名}変更に対応するため）

        Args:
            url (str)      : pixiv作品ページURL
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            str: 成功時 保存先ディレクトリパス、失敗時 空文字列
        """
        # ノベルID取得
        novel_id = self.GetNovelId(url)
        if novel_id == -1:
            return ""

        # ノベル詳細取得
        works = self.aapi.novel_detail(novel_id)
        if works.error or (works.novel is None):
            return ""
        work = works.novel

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", work.user.name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(work.user.id)
        novel_title = regex.sub("", work.title)
        novel_title = emoji.get_emoji_regexp().sub("", novel_title)

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
                        sd_path = "./{}/{}({})/".format(dir_name, novel_title, novel_id)
                        break
        
        if sd_path == "":
            sd_path = "./{}({})/{}({})/".format(author_name, author_id, novel_title, novel_id)

        save_directory_path = save_path / sd_path
        return str(save_directory_path)

    def DownloadNovel(self, url: str, save_directory_path: str) -> int:
        """pixiv作品ページURLからノベル作品をダウンロードする

        Notes:
            非公式pixivAPIを通して保存する
            save_directory_pathは
            {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID})/の形を想定している
            save_directory_pathからノベルタイトルとノベルIDを取得し
            {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID}).{拡張子}の形式で保存
            ノベルテキスト全文はurlからノベルIDを取得し、非公式pixivAPIを利用して取得する

        Args:
            url (str): pixiv作品ページURL
            save_directory_path (str): 保存先フルパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        # ノベルID取得
        novel_id = self.GetNovelId(url)
        if novel_id == -1:
            logger.info("Download pixiv novel: " + url + " -> failed")
            return -1

        # ノベル詳細取得
        works = self.aapi.novel_detail(novel_id)
        if works.error or (works.novel is None):
            logger.info("Download pixiv novel: " + url + " -> failed")
            return -1
        work = works.novel

        # ノベルテキスト取得
        work_text = self.aapi.novel_text(novel_id)
        if work_text.error or (work_text.novel_text is None):
            logger.info("Download pixiv novel: " + url + " -> failed")
            return -1

        # 保存場所親ディレクトリ作成
        sd_path = Path(save_directory_path)
        sd_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイル名取得
        ext = ".txt"
        name = "{}{}".format(sd_path.name, ext)

        # 既に存在しているなら再DLしないでスキップ
        if (sd_path.parent / name).is_file():
            logger.info("Download pixiv novel: " + name + " -> exist")
            return 1

        # ノベル詳細から作者・キャプション等付与情報を取得する
        info_tag = f"[info]\n" \
                   f"author:{work.user.name}({work.user.id})\n" \
                   f"id:{work.id}\n" \
                   f"title:{work.title}\n" \
                   f"create_date:{work.create_date}\n" \
                   f"page_count:{work.page_count}\n" \
                   f"text_length:{work.text_length}\n"
        soup = BeautifulSoup(work.caption, "html.parser")
        caption = f"[caption]\n" \
                  f"{soup.prettify()}\n"

        # ノベルテキストの全文を保存する
        # 改ページは"[newpage]"の内部タグで表現される
        # self.aapi.download(url, path=str(sd_path.parent), name=name)
        with (sd_path.parent / name).open("w", encoding="utf-8") as fout:
            fout.write(info_tag + "\n")
            fout.write(caption + "\n")
            fout.write("[text]\n" + work_text.novel_text + "\n")

        logger.info("Download pixiv novel: " + name + " -> done")
        return 0

    def Process(self, url: str) -> int:
        save_directory_path = self.MakeSaveDirectoryPath(url, self.base_path)
        res = self.DownloadNovel(url, save_directory_path)
        return 0 if (res in [0, 1]) else -1


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    if config["pixiv"].getboolean("is_pixiv_trace"):
        pa_cont = LSPixivNovel(config["pixiv"]["username"], config["pixiv"]["password"], config["pixiv"]["save_base_path"])
        work_url = "https://www.pixiv.net/novel/show.php?id=3195243"
        pa_cont.Process(work_url)
    pass
