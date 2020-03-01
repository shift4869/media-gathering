# coding: utf-8
import argparse

import PictureGathering.FavCrawler as FavCrawler
import PictureGathering.RetweetCrawler as RetweetCrawler


# python PictureGathering.py --type="Fav"
# python PictureGathering.py --type="RT"

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Twitter Crawler")
    arg_parser.add_argument("--type", choices=["Fav", "RT"], default="Fav",
                            help='Crawl target: Fav or RT')
    args = arg_parser.parse_args()

    c = None
    if args.type == "Fav":
        c = FavCrawler.FavCrawler()
    elif args.type == "RT":
        c = RetweetCrawler.RetweetCrawler()

    if c is not None:
        c.Crawl()
    else:
        arg_parser.print_help()
