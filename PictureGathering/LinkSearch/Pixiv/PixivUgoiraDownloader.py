# coding: utf-8
import enum
import re
from pathlib import Path
from dataclasses import dataclass
from logging import INFO, getLogger
from time import sleep
from typing import ClassVar

import emoji
from pixivpy3 import AppPixivAPI
from PIL import Image

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()
    FAILED = enum.auto()


@dataclass(frozen=True)
class PixivUgoiraDownloader():
    aapi: AppPixivAPI
    illust_id: int
    base_path: Path
    result: ClassVar[DownloadResult]

    def __post_init__(self):
        self._is_valid()
        object.__setattr__(self, "result", self.download_ugoira())

    def _is_valid(self):
        if not isinstance(self.aapi, AppPixivAPI):
            raise TypeError("aapi is not AppPixivAPI.")
        if not isinstance(self.illust_id, int):
            raise TypeError("illust_id is not int.")
        if not isinstance(self.base_path, Path):
            raise TypeError("base_path is not Path.")
        return True

    def download_ugoira(self) -> DownloadResult:
        works = self.aapi.illust_detail(self.illust_id)
        if works.error or (works.illust is None):
            raise ValueError("ugoira download failed.")
        work = works.illust

        if work.type != "ugoira":
            return DownloadResult.PASSED  # うごイラではなかった
        
        logger.info("\t\t: ugoira download -> see below ...")

        # サニタイズ
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", work.user.name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(work.user.id)
        illust_title = regex.sub("", work.title)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

        # うごイラの各フレームを保存するディレクトリを生成
        sd_path = self.base_path / "./{}({})/".format(illust_title, self.illust_id)
        sd_path.mkdir(parents=True, exist_ok=True)

        # うごイラの情報をaapiから取得する
        # アドレスは以下の形になっている
        # https://{...}/{イラストID}_ugoira{画像の番号}.jpg
        # illust = self.aapi.illust_detail(self.illust_id)
        ugoira = self.aapi.ugoira_metadata(self.illust_id)
        ugoira_url = work.meta_single_page.original_image_url.rsplit("0", 1)
        frames_len = len(ugoira.ugoira_metadata.frames)
        delays = [f["delay"] for f in ugoira.ugoira_metadata.frames]

        # 各フレーム画像DL
        for i in range(frames_len):
            frame_url = ugoira_url[0] + str(i) + ugoira_url[1]
            self.aapi.download(frame_url, path=str(sd_path))
            logger.info("\t\t: " + frame_url.rsplit("/", 1)[1] + " -> done({}/{})".format(i + 1, frames_len))
            sleep(0.5)
        
        # DLした各フレーム画像のパスを収集
        frames = []
        fr = [(sp.stat().st_mtime, str(sp)) for sp in sd_path.glob("*") if sp.is_file()]
        for mtime, path in sorted(fr, reverse=False):
            frames.append(path)

        # うごイラをanimated gifとして保存
        first = Image.open(frames[0])
        first = first.copy()
        image_list = []
        for f in frames[1:]:
            buf = Image.open(f)
            buf = buf.copy()
            # buf = buf.quantize(method=0)  # ディザリング抑制
            image_list.append(buf)
        name = "{}({}).gif".format(illust_title, self.illust_id)
        first.save(
            fp=str(self.base_path / name),
            save_all=True,
            append_images=image_list,
            optimize=False,
            duration=delays,
            loop=0
        )
        logger.info("\t\t: animated gif saved: " + name + " -> done")
        return DownloadResult.SUCCESS


if __name__ == "__main__":
    pass
