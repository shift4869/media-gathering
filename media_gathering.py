import argparse
import logging.config
from logging import INFO, getLogger
from pathlib import Path

from media_gathering.FavCrawler import FavCrawler
from media_gathering.log_message import MSG
from media_gathering.RetweetCrawler import RetweetCrawler

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    # 自分以外のすべてのライブラリのログ出力を抑制
    if "media_gathering" not in name:
        getLogger(name).disabled = True
logger = getLogger(__name__)
logger.setLevel(INFO)

PREVENT_MULTIPLE_RUN_PATH = "./prevent_multiple_run"

# python MediaGathering.py --type="Fav"
# python MediaGathering.py --type="RT"

if __name__ == "__main__":
    logger.info(MSG.HORIZONTAL_LINE.value)
    logger.info(MSG.APPLICATION_START.value)

    arg_parser = argparse.ArgumentParser(description="Twitter Crawler")
    arg_parser.add_argument("--type", choices=["Fav", "RT"], default="Fav",
                            help="Crawl target: Fav or RT")
    args = arg_parser.parse_args()

    c = None
    if args.type == "Fav":
        c = FavCrawler()
    elif args.type == "RT":
        c = RetweetCrawler()

    if c is not None:
        p = Path(PREVENT_MULTIPLE_RUN_PATH)
        try:
            if not p.exists():
                p.touch()
                c.crawl()
            else:
                logger.warning(MSG.APPLICATION_MULTIPLE_RUN.value)
        except Exception as e:
            logger.exception(e)
        finally:
            p.unlink(missing_ok=True)
    else:
        arg_parser.print_help()

    logger.info(MSG.APPLICATION_DONE.value)
    logger.info(MSG.HORIZONTAL_LINE.value)
