# coding: utf-8
import re
from abc import ABCMeta, abstractmethod

from PictureGathering.LinkSearch.URL import URL


class FetcherBase(metaclass=ABCMeta):
    """外部リンク探索処理を担うクラスの基底クラス

    派生クラスはis_target_urlとrunをオーバーライドして実装する必要がある
    """
    def __init__(self):
        # self.url = url
        pass

    @abstractmethod
    def is_target_url(self, url: URL) -> bool:
        """自分（担当者）が処理できるurlかどうか返す関数

        派生クラスでオーバーライドする

        Args:
            url (URL): 処理対象url

        Returns:
            bool: 担当urlだった場合True, そうでない場合False
        """
        return False

    @abstractmethod
    def run(self, url: URL) -> None:
        """自分（担当者）が担当する処理

        派生クラスでオーバーライドする。

        Args:
            url (URL): 処理対象url
        """
        pass


class ConcreteFetcher_0(FetcherBase):
    """具体的な担当者その0
    """
    def __init__(self):
        super().__init__()

    def is_target_url(self, url: URL) -> bool:
        pattern = r"^https://www.anyurl/sample/index_0.html$"
        regex = re.compile(pattern)
        is_target = not (regex.findall(url) == [])
        if is_target:
            print("ConcreteFetcher_0.is_target_url catch")
        return is_target

    def run(self, url: URL) -> None:
        print("ConcreteFetcher_0.run called")


if __name__ == "__main__":
    ls_base = FetcherBase()
    url = "https://www.pixiv.net/artworks/86704541"
    # url = "http://nijie.info/view_popup.php?id=409587"
    # url = "https://www.anyurl/sample/index_{}.html"

    # 具体的な担当者のインスタンスを生成
    lsc = ConcreteFetcher_0()
