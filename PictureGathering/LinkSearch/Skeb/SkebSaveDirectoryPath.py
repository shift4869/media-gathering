# coding: utf-8
from dataclasses import dataclass
from pathlib import Path

from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL


@dataclass(frozen=True)
class SkebSaveDirectoryPath():
    """skeb作品の保存先ディレクトリパス
    """
    path: Path  # 保存先ディレクトリパス

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, skeb_url: SkebURL, base_path: Path) -> "SkebSaveDirectoryPath":
        """skeb作品の保存先ディレクトリパスを生成する

        Args:
            skeb_url (SkebURL): skeb作品ページURL
            base_path (Path): 保存ディレクトリベースパス

        Returns:
            SkebSaveDirectoryPath: 保存先ディレクトリパス
                {base_path}/{作者名}/{作品ID}/の形を想定している
        """
        if not isinstance(skeb_url, SkebURL):
            raise TypeError("skeb_url is not SkebURL.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path is not Path.")

        author_name = skeb_url.author_name
        work_id = skeb_url.work_id

        # パス生成
        save_path = base_path
        sd_path = f"./{author_name.name}/{work_id.id:03}/"
        save_directory_path = save_path / sd_path
        return SkebSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    base_path = Path("./PictureGathering/LinkSearch/")
    skeb_url = SkebURL.create("https://skeb.jp/@matsukitchi12/works/25?query=1")

    save_directory_path = SkebSaveDirectoryPath.create(skeb_url, base_path)
    print(save_directory_path)
