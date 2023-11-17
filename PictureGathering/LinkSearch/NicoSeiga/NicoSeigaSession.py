from dataclasses import dataclass

import httpx
import xmltodict
from bs4 import BeautifulSoup

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username
from PictureGathering.Util import find_values


@dataclass(frozen=True)
class NicoSeigaSession():
    """認証済セッションクラス

    生成時にusernameとpasswordを受け取り、login()にてセッションを開始し、認証・ログインする
    画像情報等ニコニコ静画とのやりとりには以後この認証済セッションを使う
    """
    _session: httpx.Client  # 認証済セッション

    # 接続時に使用するヘッダー
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
    # ログインエンドポイント
    LOGIN_ENDPOINT = "https://account.nicovideo.jp/api/v1/login?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url=&mail_or_tel=1"
    # 画像情報取得エンドポイントベース
    IMAGE_INFO_API_ENDPOINT_BASE = "http://seiga.nicovideo.jp/api/illust/info?id="
    # ユーザー情報取得エンドポイントベース
    USERNAME_API_ENDPOINT_BASE = "https://seiga.nicovideo.jp/api/user/info?id="
    # 静画直リンクエンドポイントベース
    IMAGE_SOUECE_API_ENDPOINT_BASE = "http://seiga.nicovideo.jp/image/source?id="

    def __init__(self, username: Username, password: Password) -> None:
        object.__setattr__(self, "_session", self.login(username, password))
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._session, httpx.Client):
            raise TypeError("_session is not httpx.Client.")
        return True

    def login(self, username: Username, password: Password) -> httpx.Client:
        """セッションを開始し、認証・ログインする

        Args:
            username (Username): ニコニコログイン用ユーザーID
            password (Password):  ニコニコログイン用パスワード

        Returns:
            session (NicoSeigaSession): 認証済セッション
        """
        # セッション開始
        transport = httpx.HTTPTransport(retries=5)
        session = httpx.Client(follow_redirects=True, timeout=60.0, transport=transport)

        # ログイン
        params = {
            "mail_tel": username.name,
            "password": password.password,
        }
        response = session.post(self.LOGIN_ENDPOINT, data=params, headers=self.HEADERS)
        response.raise_for_status()
        return session

    def get_author_id(self, illust_id: Illustid) -> Authorid:
        """作者IDを取得する

        Args:
            illust_id (Illustid): イラストID

        Returns:
            Authorid: 作者ID
        """
        # 静画情報を取得する
        info_url = self.IMAGE_INFO_API_ENDPOINT_BASE + str(illust_id.id)
        response = self._session.get(info_url, headers=self.HEADERS)
        response.raise_for_status()

        # 静画情報解析
        response_dict = xmltodict.parse(response.text)
        author_id_str = find_values(response_dict, "user_id", True, [], [])
        author_id = int(author_id_str)
        return Authorid(author_id)

    def get_author_name(self, author_id: Authorid) -> Authorname:
        """作者名を取得する

        Args:
            illust_id (Illustid): イラストID

        Returns:
            Authorname: 作者名
        """
        # 作者情報を取得する
        username_info_url = self.USERNAME_API_ENDPOINT_BASE + str(author_id.id)
        response = self._session.get(username_info_url, headers=self.HEADERS)
        response.raise_for_status()

        # 作者情報解析
        response_dict = xmltodict.parse(response.text)
        author_name = find_values(response_dict, "nickname", True, [], [])
        return Authorname(author_name)

    def get_illust_title(self, illust_id: Illustid) -> Illustname:
        """イラストタイトルを取得する

        Args:
            illust_id (Illustid): イラストID

        Returns:
            Illustname: イラストタイトル
        """
        # 静画情報を取得する
        info_url = self.IMAGE_INFO_API_ENDPOINT_BASE + str(illust_id.id)
        response = self._session.get(info_url, headers=self.HEADERS)
        response.raise_for_status()

        # 静画情報解析
        response_dict = xmltodict.parse(response.text)
        illust_title = find_values(response_dict, "title", True, [], [])
        return Illustname(illust_title)

    def get_source_url(self, illust_id: Illustid) -> URL:
        """直リンクを取得する

        Args:
            illust_id (Illustid): イラストID

        Returns:
            URL: 画像への直リンク
        """
        # ニコニコ静画ページ取得（画像表示部分のみ）
        source_page_url = self.IMAGE_SOUECE_API_ENDPOINT_BASE + str(illust_id.id)
        response = self._session.get(source_page_url, headers=self.HEADERS)
        response.raise_for_status()

        # ニコニコ静画ページを解析して画像直リンクを取得する
        source_url = ""
        soup = BeautifulSoup(response.text, "html.parser")
        div_contents = soup.find_all("div", id="content")
        for div_content in div_contents:
            div_illust = div_content.find(class_="illust_view_big")
            source_url = div_illust.get("data-src")
            break
        return URL(source_url)

    def get_illust_binary(self, source_url: URL) -> bytes:
        """画像の実体（バイナリ）をDLする

        Args:
            source_url (URL): 画像への直リンク

        Returns:
            bytes: 画像の実体（バイナリ）
        """
        # 画像DL
        response = self._session.get(source_url.original_url, headers=self.HEADERS)
        response.raise_for_status()
        return response.content

if __name__ == "__main__":
    import configparser
    from pathlib import Path

    from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaFetcher import NicoSeigaFetcher

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    username = Username(config["nico_seiga"]["email"])
    password = Password(config["nico_seiga"]["password"])
    fetcher = NicoSeigaFetcher(username, password, base_path)
    illust_id = 11308865
    illust_url = f"https://seiga.nicovideo.jp/seiga/im{illust_id}?query=1"
    fetcher.fetch(illust_url)
