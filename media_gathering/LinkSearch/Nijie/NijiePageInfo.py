import urllib.parse
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from media_gathering.LinkSearch.Nijie.Authorid import Authorid
from media_gathering.LinkSearch.Nijie.Authorname import Authorname
from media_gathering.LinkSearch.Nijie.NijieSourceList import NijieSourceList
from media_gathering.LinkSearch.Nijie.Worktitle import Worktitle


@dataclass(frozen=True)
class NijiePageInfo():
    """NijiePageInfo

    Returns:
        NijiePageInfo: NijiePageInfoを表すValueObject
    """
    urls: NijieSourceList    # nijie作品直リンクリスト
    author_name: Authorname  # 作者名
    author_id: Authorid      # 作者ID
    work_title: Worktitle    # 作品名

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.urls, NijieSourceList):
            raise TypeError("urls must be NijieSourceList.")
        if not isinstance(self.author_name, Authorname):
            raise TypeError("author_name must be Authorname.")
        if not isinstance(self.author_id, Authorid):
            raise TypeError("author_id must be Authorid.")
        if not isinstance(self.work_title, Worktitle):
            raise TypeError("work_title must be Worktitle.")
        return True

    @classmethod
    def create(cls, soup: BeautifulSoup) -> "NijiePageInfo":
        """nijie作品詳細ページを解析する

        画像はaタグから、うごイラはvideoタグから探す

        Args:
            soup (BeautifulSoup): 解析対象のBeautifulSoupインスタンス

        Returns:
            NijiePageInfo: nijieページの詳細情報オブジェクト
        """
        if not isinstance(soup, BeautifulSoup):
            raise TypeError("soup must be BeautifulSoup instance.")

        urls: list[str] = []

        # メディアへの直リンクを取得する
        # メディアは画像（jpg, png）、うごイラ（gif, mp4）などがある
        # メディアが置かれているdiv
        div_imgs: list[Tag] = soup.find_all("div", id="img_filter")
        for div_img in div_imgs:
            # うごイラがないかvideoタグを探す
            video_s: list[Tag] = div_img.find_all("video")
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
            a_s: list[Tag] = div_img.find_all("a")
            img_url = ""
            for a in a_s:
                if a.get("href") is not None:
                    img_url = "http:" + a.img["src"]
                    break
            if img_url != "":
                urls.append(img_url)

        if urls == []:
            raise ValueError("NijiePageInfo create error")

        # 作者IDを1枚目の直リンクから取得する
        ps: str = urllib.parse.urlparse(urls[0]).path
        pt: str = ps.split("/")[-3]
        author_id = int(pt)

        # 作品タイトル、作者名はページタイトルから取得する
        title_tag = soup.find("title")
        title = title_tag.text.split("|")
        illust_name = title[0].strip()
        author_name = title[1].strip()

        # ValueObject 変換
        source_list = NijieSourceList.create(urls)
        author_name = Authorname(author_name)
        author_id = Authorid(author_id)
        illust_name = Worktitle(illust_name)

        return NijiePageInfo(source_list, author_name, author_id, illust_name)


if __name__ == "__main__":
    import configparser
    from pathlib import Path

    from media_gathering.LinkSearch.Nijie.NijieFetcher import NijieFetcher
    from media_gathering.LinkSearch.Password import Password
    from media_gathering.LinkSearch.Username import Username

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["nijie"].getboolean("is_nijie_trace"):
        fetcher = NijieFetcher(Username(config["nijie"]["email"]), Password(config["nijie"]["password"]), base_path)

        illust_id = 251267  # 一枚絵
        # illust_id = 251197  # 漫画
        # illust_id = 414793  # うごイラ一枚
        # illust_id = 409587  # うごイラ複数

        illust_url = f"https://nijie.info/view_popup.php?id={illust_id}"
        fetcher.fetch(illust_url)
