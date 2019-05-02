# coding: utf-8
from abc import ABCMeta, abstractmethod
import argparse
import configparser
from datetime import datetime
import json
import io
import os
import requests
from requests_oauthlib import OAuth1Session
import sqlite3
import sys
import time
import traceback
import urllib

import WriteHTML as WriteHTML
import DBControlar as DBControlar
import Crawler as Crawler
import FavCrawler as FavCrawler
import RetweetCrawler as RetweetCrawler


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
