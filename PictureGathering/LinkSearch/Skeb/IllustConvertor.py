# coding: utf-8
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class IllustConvertor():
    """.webpから.pngに変換するクラス
    """
    _source: Path
    _extension: str = ".png"

    def convert(self) -> Path:
        """.webpから.pngに変換する

        Image.open.convertで変換する
        元のファイルは削除される

        Returns:
            Path: 変換後のファイルパス
        """
        src_path = self._source
        img = Image.open(src_path).convert("RGB")
        dst_path = src_path.with_suffix(self._extension)
        img.save(dst_path)

        src_path.unlink(missing_ok=True)
        if not dst_path.is_file():
            raise ValueError("IllustConvertor convert failed.")

        return dst_path


if __name__ == "__main__":
    import configparser
    import logging.config

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
        work_url = "https://skeb.jp/@matsukitchi12/works/25?query=1"
        # 動画（単体）
        # work_url = "https://skeb.jp/@wata_lemon03/works/7"
        # gif画像（複数）
        # work_url = "https://skeb.jp/@_sa_ya_/works/55"

        fetcher.fetch(work_url)
