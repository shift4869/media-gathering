import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class FetcherBase(metaclass=ABCMeta):
    """外部リンク探索処理を担うクラスの基底クラス

    派生クラスはis_target_urlとfetchをオーバーライドして実装する必要がある
    """
    def __init__(self):
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
    def fetch(self, url: URL) -> None:
        """自分（担当者）が担当する処理

        派生クラスでオーバーライドする。

        Args:
            url (URL): 処理対象url
        """
        pass


if __name__ == "__main__":
    class ConcreteFetcher_0(FetcherBase):
        """具体的な担当者その0
        """
        def __init__(self):
            super().__init__()

        def is_target_url(self, url: URL) -> bool:
            pattern = r"^https://www.anyurl/sample/index_0.html$"
            is_target = re.search(pattern, url.original_url) is not None
            if is_target:
                print("ConcreteFetcher_0.is_target_url catch")
            return is_target

        def fetch(self, url: URL) -> None:
            print("ConcreteFetcher_0.fetch called")

    # 具体的な担当者のインスタンスを生成
    fetcher = ConcreteFetcher_0()
    url = URL("https://www.anyurl/sample/index_0.html")
    print(fetcher.is_target_url(url))
    print(fetcher.fetch(url))
