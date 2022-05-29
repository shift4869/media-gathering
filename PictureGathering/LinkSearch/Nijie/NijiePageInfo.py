# coding: utf-8
from dataclasses import dataclass
from logging import INFO, getLogger
import urllib.parse

from bs4 import BeautifulSoup
from PictureGathering.LinkSearch.Nijie.NijieIllustURLList import NijieIllustURLList
from PictureGathering.LinkSearch.Nijie.Authorname import Authorname
from PictureGathering.LinkSearch.Nijie.Authorid import Authorid
from PictureGathering.LinkSearch.Nijie.Illustname import Illustname


logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class NijiePageInfo():
    """NijiePageInfo

    Returns:
        NijiePageInfo: NijiePageInfoを表すValueObject
    """
    urls: NijieIllustURLList
    authorname: Authorname
    authorid: Authorid
    illustname: Illustname

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.urls, NijieIllustURLList):
            raise TypeError("urls must be NijieIllustURLList.")
        if not isinstance(self.authorname, Authorname):
            raise TypeError("authorname must be Authorname.")
        if not isinstance(self.authorid, Authorid):
            raise TypeError("authorid must be Authorid.")
        if not isinstance(self.illustname, Illustname):
            raise TypeError("illustname must be Illustname.")
        return True

    @classmethod
    def create(cls, soup: BeautifulSoup) -> "NijiePageInfo":
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

        # 取得失敗した場合はエラー値を返す
        if urls == []:
            logger.error("NijiePageInfo create error")
            raise ValueError("NijiePageInfo create error")

        # 作者IDを1枚目の直リンクから取得する
        ps = urllib.parse.urlparse(urls[0]).path
        pt = ps.split("/")[-3]
        author_id = int(pt)

        # 作品タイトル、作者名はページタイトルから取得する
        title_tag = soup.find("title")
        title = title_tag.text.split("|")
        illust_name = title[0].strip()
        author_name = title[1].strip()

        # ValueObject 変換
        urls = NijieIllustURLList.create(urls)
        author_name = Authorname(author_name)
        author_id = Authorid(author_id)
        illust_name = Illustname(illust_name)

        return NijiePageInfo(urls, author_name, author_id, illust_name)


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = NijiePageInfo.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
