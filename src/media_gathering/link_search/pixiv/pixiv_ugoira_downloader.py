import enum
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from time import sleep

from PIL import Image
from pixivpy3 import AppPixivAPI

from media_gathering.link_search.pixiv.workid import Workid
from media_gathering.link_search.pixiv.worktitle import Worktitle

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass(frozen=True)
class PixivUgoiraDownloader:
    """うごイラをDLするクラス"""

    aapi: AppPixivAPI  # 非公式pixivAPI操作インスタンス
    work_id: Workid  # 作品ID
    base_path: Path  # 保存ディレクトリベースパス

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.aapi, AppPixivAPI):
            raise TypeError("aapi is not AppPixivAPI.")
        if not isinstance(self.work_id, Workid):
            raise TypeError("work_id is not Workid.")
        if not isinstance(self.base_path, Path):
            raise TypeError("base_path is not Path.")
        return True

    def download(self) -> DownloadResult:
        """うごイラをダウンロードする

        Notes:
            {base_path}/{作品タイトル}({作品ID})/以下に各フレーム画像を保存
            {base_path}/{作品タイトル}({作品ID}).gifとしてアニメーションgifを保存

        Args:
            illust_id (int): 作品ID
            base_path (str): 保存先ベースフルパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        works = self.aapi.illust_detail(self.work_id.id)
        if works.error or (works.illust is None):
            raise ValueError("ugoira download failed.")
        work = works.illust

        if work.type != "ugoira":
            return DownloadResult.PASSED  # うごイラではなかった

        logger.info("\t\t: ugoira download -> see below ...")

        # ValueObject生成
        work_title = Worktitle(work.title).title

        # うごイラの各フレームを保存するディレクトリを生成
        sd_path = self.base_path / f"./{work_title}({self.work_id.id})/"
        if sd_path.is_dir():
            logger.info(f"\t\t: {str(sd_path)} exist -> skip")
            return DownloadResult.PASSED  # すでに取得済

        sd_path.mkdir(parents=True, exist_ok=True)

        # うごイラの情報をaapiから取得する
        # アドレスは以下の形になっている
        # https://{...}/{作品ID}_ugoira{画像の番号}.jpg
        ugoira = self.aapi.ugoira_metadata(self.work_id.id)
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
        name = f"{work_title}({self.work_id.id}).gif"
        first.save(
            fp=str(self.base_path / name),
            save_all=True,
            append_images=image_list,
            optimize=False,
            duration=delays,
            loop=0,
        )
        logger.info("\t\t: animated gif saved: " + name + " -> done")
        return DownloadResult.SUCCESS


if __name__ == "__main__":
    import logging.config

    import orjson

    from media_gathering.link_search.password import Password
    from media_gathering.link_search.pixiv.pixiv_fetcher import PixivFetcher
    from media_gathering.link_search.username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.json"
    config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())

    base_path = Path("./media_gathering/link_search/")
    if config["pixiv"]["is_pixiv_trace"]:
        pa_cont = PixivFetcher(Username(config["pixiv"]["username"]), Password(config["pixiv"]["password"]), base_path)
        work_url = "https://www.pixiv.net/artworks/86704541"
        pa_cont.fetch(work_url)
