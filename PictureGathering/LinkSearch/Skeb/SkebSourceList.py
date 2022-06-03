# coding: utf-8
from dataclasses import dataclass
from typing import Iterable

from requests_html import HTMLSession

from PictureGathering.LinkSearch.Skeb.CallbackURL import CallbackURL
from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.Skeb.SkebSourceInfo import SkebSourceInfo
from PictureGathering.LinkSearch.Skeb.SkebToken import SkebToken
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class SkebSourceList(Iterable):
    _list: list[SkebSourceInfo]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
    }

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._list, list):
            raise TypeError("list is not list[], invalid SkebSourceList.")
        if self._list:
            if not all([isinstance(r, SkebSourceInfo) for r in self._list]):
                raise ValueError("include not URL element, invalid SkebSourceList")

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()

    def __getitem__(self, i):
        return self._list.__getitem__(i)

    @classmethod
    def create(cls, skeb_url: SkebURL, top_url: URL, token: SkebToken) -> "SkebSourceList":
        url = skeb_url.non_query_url
        # リクエスト用のURLを作成する
        # tokenを付与したコールバックURLを作成する
        work_path = url.replace(top_url.non_query_url, "")
        request_url = CallbackURL.create(top_url, work_path, token)

        # 作品ページを取得して解析する
        session = HTMLSession()
        source_list = []

        r = session.get(request_url.callback_url, headers=SkebSourceList.HEADERS)
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
                source = SkebSourceInfo(URL(src_url), Extension.WEBP)
                source_list.append(source)

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
                source = SkebSourceInfo(URL(src_url), Extension.MP4)
                source_list.append(source)

        # 動画
        # type="video/mp4"属性を持つsourceタグのsrc属性
        src_tags = r.html.find("source")
        for src_tag in src_tags:
            type = src_tag.attrs.get("type", "")
            src_url = src_tag.attrs.get("src", "")
            if type == "video/mp4" and src_url != "":
                source = SkebSourceInfo(URL(src_url), Extension.MP4)
                source_list.append(source)

        if len(source_list) == 0:
            ValueError("GetWorkURLs : html analysis failed")

        return SkebSourceList(source_list)


if __name__ == "__main__":
    pass
