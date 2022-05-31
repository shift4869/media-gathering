# coding: utf-8
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class NicoSeigaSession():
    _session: requests.Session
    _headers: dict

    IMAGE_INFO_API_ENDPOINT_BASE = "http://seiga.nicovideo.jp/api/illust/info?id="
    USERNAME_API_ENDPOINT_BASE = "https://seiga.nicovideo.jp/api/user/info?id="
    IMAGE_SOUECE_API_ENDPOINT_BASE = "http://seiga.nicovideo.jp/image/source?id="

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._session, requests.Session):
            raise TypeError("_session is not requests.Session.")
        if not isinstance(self._headers, dict):
            raise TypeError("_headers is not requests.cookies.RequestsCookieJar.")

        if not (self._headers and self._session):
            return ValueError("NicoSeigaSession _headers or _session is invalid.")
        return True

    def get_author_id(self, illust_id: Illustid) -> Authorid:
        # 静画情報を取得する
        info_url = self.IMAGE_INFO_API_ENDPOINT_BASE + str(illust_id.id)
        response = self._session.get(info_url, headers=self._headers)
        response.raise_for_status()

        # 静画情報解析
        soup = BeautifulSoup(response.text, "lxml-xml")
        xml_image = soup.find("image")
        author_id = int(xml_image.find("user_id").text)
        return Authorid(author_id)

    def get_author_name(self, author_id: Authorid) -> Authorname:
        # 作者情報を取得する
        username_info_url = self.USERNAME_API_ENDPOINT_BASE + str(author_id.id)
        response = self._session.get(username_info_url, headers=self._headers)
        response.raise_for_status()

        # 作者情報解析
        soup = BeautifulSoup(response.text, "lxml-xml")
        xml_user = soup.find("user")
        author_name = xml_user.find("nickname").text
        return Authorname(author_name)

    def get_illust_title(self, illust_id: Illustid) -> Illustname:
        # 静画情報を取得する
        info_url = self.IMAGE_INFO_API_ENDPOINT_BASE + str(illust_id.id)
        response = self._session.get(info_url, headers=self._headers)
        response.raise_for_status()

        # 静画情報解析
        soup = BeautifulSoup(response.text, "lxml-xml")
        xml_image = soup.find("image")
        illust_title = xml_image.find("title").text
        return Illustname(illust_title)

    def get_source_url(self, illust_id: Illustid) -> URL:
        # ニコニコ静画ページ取得（画像表示部分のみ）
        source_page_url = self.IMAGE_SOUECE_API_ENDPOINT_BASE + str(illust_id.id)
        response = self._session.get(source_page_url, headers=self._headers)
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
        # 画像DL
        response = self._session.get(source_url.original_url, headers=self._headers)
        response.raise_for_status()
        return response.content
