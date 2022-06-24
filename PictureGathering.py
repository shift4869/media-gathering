# coding: utf-8
import argparse
import logging.config
from logging import INFO, getLogger

import PictureGathering.FavCrawler as FavCrawler
import PictureGathering.GoogleDrive as GoogleDrive
import PictureGathering.RetweetCrawler as RetweetCrawler

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    # すべてのライブラリのログ出力を抑制
    # print("logger", name)
    getLogger(name).disabled = True
logger = getLogger("root")
logger.setLevel(INFO)

# python PictureGathering.py --type="Fav"
# python PictureGathering.py --type="RT"

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Twitter Crawler")
    arg_parser.add_argument("--type", choices=["Fav", "RT"], default="Fav",
                            help="Crawl target: Fav or RT")
    args = arg_parser.parse_args()

    c = None
    if args.type == "Fav":
        logger.info("Fav Crawler run.")
        c = FavCrawler.FavCrawler()
    elif args.type == "RT":
        logger.info("Retweet Crawler run.")
        c = RetweetCrawler.RetweetCrawler()

    if c is not None:
        c.Crawl()
    else:
        arg_parser.print_help()
