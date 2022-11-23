# coding: utf-8
import re
from dataclasses import dataclass
from pathlib import Path

from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo


@dataclass(frozen=True)
class NicoSeigaSaveDirectoryPath():
    """ニコニコ静画作品の保存先ディレクトリパス
    """
    path: Path  # 保存先ディレクトリパス

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("argument is not Path.")
        return True

    @classmethod
    def create(cls, illust_info: NicoSeigaInfo, base_path: Path) -> "NicoSeigaSaveDirectoryPath":
        """ニコニコ静画作品の保存先ディレクトリパスを生成する

        Args:
            illust_info (NicoSeigaInfo): 対象の静画情報
            base_path (Path): 保存ディレクトリベースパス

        Returns:
            NicoSeigaSaveDirectoryPath: 保存先ディレクトリパス
                {base_path}/{作者名}({作者ID})/{作品タイトル}({作品ID})/の形を想定している
        """
        illust_id = illust_info.illust_id.id
        illust_name = illust_info.illust_name.name
        author_id = illust_info.author_id.id
        author_name = illust_info.author_name.name

        # 既に{作者ID}が一致するディレクトリがあるか調べる
        sd_path = ""
        save_path = Path(base_path)
        filelist = []
        filelist_tp = [(sp.stat().st_mtime, sp.name) for sp in save_path.glob("*") if sp.is_dir()]
        for mtime, path in sorted(filelist_tp, reverse=True):
            filelist.append(path)

        regex = re.compile(r'.*\(([0-9]*)\)$')
        for dir_name in filelist:
            result = regex.match(dir_name)
            if result:
                ai = result.group(1)
                if ai == str(author_id):
                    sd_path = f"./{dir_name}/{illust_name}({illust_id})/"
                    break

        if sd_path == "":
            sd_path = f"./{author_name}({author_id})/{illust_name}({illust_id})/"

        save_directory_path = save_path / sd_path
        return NicoSeigaSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
    from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
    from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
    from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname

    illust_id = Illustid(1234567)
    illust_name = Illustname("作品名1")
    author_id = Authorid(12345678)
    author_name = Authorname("作者名1")
    illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

    base_path = Path("./PictureGathering/LinkSearch/")
    save_directory_path = NicoSeigaSaveDirectoryPath.create(illust_info, base_path)
    print(save_directory_path)
