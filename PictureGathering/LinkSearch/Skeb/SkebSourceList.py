# coding: utf-8
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.Skeb.SkebSession import SkebSession
from PictureGathering.LinkSearch.Skeb.SkebSourceInfo import SkebSourceInfo
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class SkebSourceList(Iterable):
    """skebの直リンク情報リスト
    """
    _list: list[SkebSourceInfo]

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
    def create(cls, skeb_url: SkebURL, session: SkebSession) -> "SkebSourceList":
        """skebの直リンク情報を収集する

        Args:
            skeb_url (SkebURL): skeb作品URL
            top_url (URL): skebトップページURL
            cookies (SkebCookie): 接続用クッキー
            headers (dict): 接続用ヘッダー

        Returns:
            SkebSourceList: skebの直リンク情報リスト
        """
        source_list = []

        # loop = asyncio.new_event_loop()
        response = session.get(skeb_url.non_query_url)

        # イラスト
        # imgタグ、src属性のリンクURL形式が次のいずれかの場合
        # TODO:対象URLの形式を正規表現でまとめる
        img_tags = response.html.find("img")
        for img_tag in img_tags:
            src_url = img_tag.attrs.get("src", "")
            if "https://skeb.imgix.net/uploads/" in src_url or \
               "https://skeb.imgix.net/requests/" in src_url or \
               "https://si.imgix.net/" in src_url:
                source = SkebSourceInfo(URL(src_url), Extension.WEBP)
                source_list.append(source)

        # gif
        # videoタグのsrc属性
        # 動画として保存する
        src_tags = response.html.find("video")
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
        src_tags = response.html.find("source")
        for src_tag in src_tags:
            type = src_tag.attrs.get("type", "")
            src_url = src_tag.attrs.get("src", "")
            if type == "video/mp4" and src_url != "":
                source = SkebSourceInfo(URL(src_url), Extension.MP4)
                source_list.append(source)

        # 小説
        # urlの後ろに?p="{本文}"として付与する（力技）
        src_tags = response.html.find(".p")
        for src_tag in src_tags:
            text = src_tag.full_text
            if len(text) > 0:
                src_url = skeb_url.non_query_url + f"?p={text}"
                source = SkebSourceInfo(URL(src_url), Extension.TXT)
                source_list.append(source)

        if len(source_list) == 0:
            raise ValueError("SkebSourceList: html analysis failed.")

        return SkebSourceList(source_list)


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path

    from PictureGathering.LinkSearch.Password import Password
    from PictureGathering.LinkSearch.Skeb.SkebFetcher import SkebFetcher
    from PictureGathering.LinkSearch.Username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["skeb"].getboolean("is_skeb_trace"):
        fetcher = SkebFetcher(Username(config["skeb"]["twitter_id"]), Password(config["skeb"]["twitter_password"]), base_path)

        # イラスト（複数）
        # work_url = "https://skeb.jp/@matsukitchi12/works/25?query=1"
        # 動画（単体）
        # work_url = "https://skeb.jp/@wata_lemon03/works/7"
        # gif画像（複数）
        # work_url = "https://skeb.jp/@_sa_ya_/works/55"
        # 小説
        work_url = "https://skeb.jp/@ba77_chiriny/works/6"

        fetcher.fetch(work_url)
