# coding: utf-8
import asyncio
import configparser
import logging.config
import random
import re
import urllib.parse
from logging import DEBUG, INFO, getLogger
from pathlib import Path
from time import sleep

import emoji
import pyppeteer
import requests
from PIL import Image
from requests_html import HTMLSession

from PictureGathering import LinkSearchBase

logger = getLogger("root")
logger.setLevel(INFO)


class LSSkeb(LinkSearchBase.LinkSearchBase):
    def __init__(self, twitter_id: str, twitter_password: str, base_path: str):
        """Skebページ取得用クラス

        Args:
            twitter_id (str): SkebユーザーIDとして登録したツイッターID
            twitter_password (str): SkebユーザーIDとして登録したツイッターのパスワード

        Attributes:
            auth_success (boolean): Skebログインが正常に完了したかどうか
            base_path (str): 保存先ベースパス
            headers (dict): httpリクエスト時のUser-Agent偽装用ヘッダ
            top_url (str): Skebのトップページ
            token (str): Skebの作品ページを表示するために使う認証トークン
        """
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
        }

        self.top_url = "https://skeb.jp/"
        self.token = ""
        self.auth_success = False

        self.token, self.auth_success = self.GetToken(twitter_id, twitter_password)

        if not self.auth_success:
            exit(-1)

        self.base_path = base_path

    async def GetTokenFromOAuth(self, twitter_id: str, twitter_password: str) -> str:
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
            if (self.top_url + "callback") in response.url:
                urls.append(response.url)
        page.on("response", lambda response: asyncio.ensure_future(ResponseListener(response)))

        # トップページに遷移
        await asyncio.gather(page.goto(self.top_url), page.waitForNavigation())
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
        logger.info(f"Getting Skeb token is success: {token}")

        return token

    def GetToken(self, twitter_id: str, twitter_password: str):
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
                token = fin.read()

            # 有効なトークンか確認する
            # 実際にアクセスして確認するので負荷を考えるとチェックするかどうかは微妙
            # if(not self.IsValidToken(token)):
            #     logger.error("Getting Skeb token is failed.")
            #     return (None, False)

            auth_success = True

        if not auth_success:
            # トークンファイルがない場合、または有効なトークンではなかった場合
            # 認証してtokenを取得する
            loop = asyncio.new_event_loop()
            token = loop.run_until_complete(self.GetTokenFromOAuth(twitter_id, twitter_password))

            if token == "":
                logger.error("Getting token from oauth is failed.")
                return (None, False)

            # 取得したトークンを保存
            with stp.open("w") as fout:
                fout.write(token)

            auth_success = True

        return (token, auth_success)

    def MakeCallbackURL(self, path: str, token: str) -> str:
        """コールバックURLを生成する

        Notes:
            以下のURLを生成する
                callback_url = f"{self.top_url}callback?path=/{path}&token={token}"
            self.top_urlが不正（存在しないor空白）の場合は空文字列を返す
            tokenの正当性はチェックしない(self.IsValidTokenの役目)

        Args:
            path (str): 遷移先のURLパス、先頭に"/"があった場合は"/"は無視される
            token (str): アクセス用トークン

        Returns:
            str: 正常時callback_url、異常時 空文字列
        """
        if not hasattr(self, "top_url") or self.top_url == "":
            return ""

        # pathの先頭チェック
        # 先頭と末尾に"/"があった場合は"/"を無視する
        if path[0] == "/":
            path = path[1:]
        if len(path) > 1 and path[-1] == "/":
            path = path[:-1]

        callback_url = f"{self.top_url}callback?path=/{path}&token={token}"
        return callback_url

    def IsValidToken(self, token: str = "") -> bool:
        """トークンが有効かどうか判定する

        Notes:
            tokenが有効かどうか検証する
            実際にアクセスするため負荷がかかる

        Args:
            token (str): 検証対象のトークン

        Returns:
            boolean: tokenが有効なトークンならTrue、有効でなければFalse
        """
        # 引数でtokenが指定されていない場合はself.tokenがあるかチェック
        if token == "":
            if not hasattr(self, "token") or self.token == "":
                return False
            token = self.token

        # コールバックURLを取得する
        request_url = self.MakeCallbackURL("/", token)
        if request_url == "":
            return False

        # コールバック後のトップページを取得するリクエストを行う
        session = HTMLSession()
        r = session.get(request_url, headers=self.headers)
        r.raise_for_status()
        r.html.render(sleep=2)

        # トークンが有効な場合はトップページからaccountページへのリンクが取得できる
        # 右上のアイコンマウスオーバー時に展開されるリストから
        # 「アカウント」メニューがあるかどうかを見ている
        result = False
        a_tags = r.html.find("a")
        for a_tag in a_tags:
            account_href = a_tag.attrs.get("href", "")
            full_text = a_tag.full_text
            if "/account" in account_href and "アカウント" == full_text:
                result = True
                break

        return result

    def IsTargetUrl(cls, url: str) -> bool:
        """URLがSkebのURLかどうか判定する

        Note:
            想定URL形式：https://skeb.jp/@{作者アカウント名}/works/{作品id}

        Args:
            url (str): 判定対象url

        Returns:
            boolean: Skeb作品ページURLならTrue、そうでなければFalse
        """
        pattern = r"^https://skeb.jp/\@(.+?)/works/[0-9]+$"
        regex = re.compile(pattern)
        f = not (regex.findall(url) == [])
        return f

    def GetUserWorkID(self, url: str) -> tuple[str, int]:
        """Skeb作品ページURLから作者アカウント名と作品idを取得する

        Note:
            想定URL形式：https://skeb.jp/@{作者アカウント名}/works/{作品id}

        Args:
            url (str): Skeb作品ページURL

        Returns:
            author_name (str): 作者アカウント名、取得失敗時は空文字列
            work_id (int): 作品id、取得失敗時は-1
        """
        # urlチェック
        if not self.IsTargetUrl(url):
            return ("", -1)

        author_name = ""
        work_id = -1
        m = re.match(r"^https://skeb.jp/\@(.+?)/works/([0-9]+)$", url)
        if m:
            author_name = m.group(1)
            work_id = int(m.group(2))
        return (author_name, work_id)

    def ConvertWebp(self, target_path: Path, ext: str = ".png") -> Path:
        """webp形式の画像ファイルをpngに変換する

        Notes:
            PIL.Imageを用いて画像変換する

        Args:
            target_path (Path): 対象webpファイルのパス
            ext (str, optional): ピリオドつきの変換先の拡張子　デフォルトは.png

        Returns:
            Path: 変換後のPathオブジェクト、エラー時None
        """
        try:
            img = Image.open(target_path).convert("RGB")
            dst_path = target_path.with_suffix(ext)
            img.save(dst_path)
            target_path.unlink(missing_ok=True)
        except Exception:
            return None
        return dst_path if dst_path.is_file() else None

    def GetWorkURLs(self, url: str) -> list[str, str]:
        """Skeb作品ページURLから作品URLを取得する

        Note:
            想定URL形式：https://skeb.jp/@{作者アカウント名}/works/{作品id}
            トークンを通して実際にページ取得し、解析する

        Args:
            url (str): Skeb作品ページURL

        Returns:
            list[str, str]: (作品への直リンクURL, リソースタイプ{"illust", "video"})のリスト
        """
        # クエリを除去
        url_path = Path(urllib.parse.urlparse(url).path)
        url = urllib.parse.urljoin(url, url_path.name)

        # urlチェック
        if not self.IsTargetUrl(url):
            return []

        # リクエスト用のURLを作成する
        # tokenを付与したコールバックURLを作成する
        work_path = url.replace(self.top_url, "")
        request_url = self.MakeCallbackURL(work_path, self.token)
        if(request_url == ""):
            logger.error("Setting Callback URL is failed.")
            return []

        # 作品ページを取得して解析する
        session = HTMLSession()
        source_list = []
        work_url = ""

        r = session.get(request_url, headers=self.headers)
        r.raise_for_status()
        r.html.render(sleep=2)

        # イラスト
        # imgタグ、src属性のリンクURL形式が次のいずれかの場合
        # "https://skeb.imgix.net/uploads/"で始まる
        # "https://skeb.imgix.net/requests/"で始まる
        img_tags = r.html.find("img")
        for img_tag in img_tags:
            src_url = img_tag.attrs.get("src", "")
            if "https://skeb.imgix.net/uploads/" in src_url or \
               "https://skeb.imgix.net/requests/" in src_url:
                source_list.append((src_url, "illust"))

        # gif
        # videoタグのsrc属性
        # 動画として保存する
        src_tags = r.html.find("video")
        for src_tag in src_tags:
            preload_a = src_tag.attrs.get("preload", "")
            autoplay_a = src_tag.attrs.get("autoplay", "")
            muted_a = src_tag.attrs.get("muted", "")
            loop_a = src_tag.attrs.get("loop", "")
            src_url = src_tag.attrs.get("src", "")
            if preload_a == "auto" and autoplay_a == "autoplay" and muted_a == "muted" and loop_a == "loop" and src_url != "":
                source_list.append((src_url, "video"))

        # 動画
        # type="video/mp4"属性を持つsourceタグのsrc属性
        src_tags = r.html.find("source")
        for src_tag in src_tags:
            type = src_tag.attrs.get("type", "")
            src_url = src_tag.attrs.get("src", "")
            if type == "video/mp4" and src_url != "":
                source_list.append((src_url, "video"))

        if len(source_list) == 0:
            logger.error(f"GetWorkURLs : html analysis failed")

        return source_list

    def MakeSaveDirectoryPath(self, url: str, base_path: str) -> str:
        """保存先ディレクトリパスを生成する

        Notes:
            出力する保存先ディレクトリパスの形式は以下とする
            {base_path}/{作者アカウント名}/{作品id}/

        Args:
            url (str): Skeb作品ページURL
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            str: 成功時 保存先ディレクトリパス、失敗時 空文字列
        """
        # urlチェック
        if not self.IsTargetUrl(url):
            return ""

        author_name, work_id = self.GetUserWorkID(url)
        if author_name == "" or work_id == -1:
            return ""

        # パスに使えない文字をサニタイズする
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", author_name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)

        # パス生成
        save_path = Path(base_path)
        sd_path = "./{}/{:03}/".format(author_name, work_id)
        save_directory_path = save_path / sd_path
        return str(save_directory_path)

    def DownloadWorks(self, source_list: list[str, str], save_directory_path: str) -> int:
        """Skeb作品ページURLから作品をダウンロードして保存先ディレクトリパスに保存する

        Notes:
            保存先ディレクトリパスの形式は以下の形式を想定している
                {base_path}/{作者アカウント名}/{作品id}/
            この配下に
                複数作品ある場合：{作者アカウント名}_{作品id}_{3ケタの連番}.{拡張子(png)}
                単一の場合：{作者アカウント名}_{作品id}.{拡張子(png)}
            で保存される
            ※複数/一枚絵のイラストのみを対象とする

        Args:
            source_list (list[str, str]): (作品への直リンクURL, リソースタイプ{"illust", "video"})のリスト
            save_directory_path (str): 保存先ディレクトリパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        sd_path = Path(save_directory_path)
        author_name = sd_path.parent.name
        work_id = int(sd_path.name)

        work_num = len(source_list)
        if work_num > 1:  # 複数作品
            logger.info(f"Download Skeb work: [{author_name}_{work_id:03}] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return 1

            # {作者名}/{作品名}ディレクトリ作成
            sd_path.mkdir(parents=True, exist_ok=True)

            # 作品をDLする
            # ファイル名は{イラストタイトル}({イラストID})_{3ケタの連番}.{拡張子}
            for i, src in enumerate(source_list):
                url, type = src

                # 変換処理用辞書
                # 変換処理が必要かどうか(Trueなら変換する), 変換前拡張子, 変換後拡張子
                p_dict = {
                    "illust": (True, ".webp", ".png"),
                    "video": (False, ".mp4", ".mp4"),
                }
                p = p_dict.get(type)
                if not p:
                    logger.error(f"\t\t: {author_name}_{work_id:03}: {type} is invalid")
                    return -1
                src_ext = p[1]
                dst_ext = p[2]

                file_name = f"{author_name}_{work_id:03}_{i:03}{src_ext}"

                res = requests.get(url, headers=self.headers)
                res.raise_for_status()

                with Path(sd_path / file_name).open(mode="wb") as fout:
                    fout.write(res.content)

                # 変換が必要なら行う(.webp->.png)
                dst_path = None
                if p[0]:
                    dst_path = self.ConvertWebp(sd_path / file_name, dst_ext)
                else:
                    dst_path = sd_path / file_name

                if dst_path:
                    logger.info("\t\t: " + dst_path.name + " -> done({}/{})".format(i + 1, work_num))
                else:
                    logger.info("\t\t: " + file_name + " -> done({}/{}) , but convert failed".format(i + 1, work_num))
                sleep(0.5)
        elif work_num == 1:  # 単一
            # {作者名}ディレクトリ作成
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル名設定
            url, type = source_list[0]

            # 変換処理用辞書
            # 変換処理が必要かどうか(Trueなら変換する), 変換前拡張子, 変換後拡張子
            p_dict = {
                "illust": (True, ".webp", ".png"),
                "video": (False, ".mp4", ".mp4"),
            }
            p = p_dict.get(type)
            if not p:
                logger.error(f"\t\t: {author_name}_{work_id:03}: {type} is invalid")
                return -1
            src_ext = p[1]
            dst_ext = p[2]

            file_name = f"{author_name}_{work_id:03}{dst_ext}"

            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / file_name).is_file():
                logger.info("Download Skeb work: " + file_name + " -> exist")
                return 1

            # DLする
            res = requests.get(url, headers=self.headers)
            res.raise_for_status()

            # {作者名}ディレクトリ直下に保存
            file_name = f"{author_name}_{work_id:03}{src_ext}"
            with Path(sd_path.parent / file_name).open(mode="wb") as fout:
                fout.write(res.content)

            # 変換が必要なら行う(.webp->.png)
            dst_path = None
            if p[0]:
                dst_path = self.ConvertWebp(sd_path.parent / file_name, dst_ext)
            else:
                dst_path = sd_path.parent / file_name

            if dst_path:
                logger.info("Download Skeb work: " + dst_path.name + " -> done")
            else:
                logger.info("Download Skeb work: " + file_name + " -> done , but convert failed")
        else:  # エラー
            return -1

        return 0

    def Process(self, url: str) -> int:
        source_list = self.GetWorkURLs(url)
        save_directory_path = self.MakeSaveDirectoryPath(url, self.base_path)
        res = self.DownloadWorks(source_list, save_directory_path)
        return 0 if (res in [0, 1]) else -1


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    sc = LSSkeb(config["skeb"]["twitter_id"], config["skeb"]["twitter_password"], config["skeb"]["save_base_path"])

    # イラスト（複数）
    work_url = "https://skeb.jp/@matsukitchi12/works/25"
    # 動画（単体）
    # work_url = "https://skeb.jp/@wata_lemon03/works/7"
    # gif画像（複数）
    # work_url = "https://skeb.jp/@_sa_ya_/works/55"
    sc.Process(work_url)

    pass
