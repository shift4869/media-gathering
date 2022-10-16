# coding: utf-8
import codecs
import json
import sys
import unittest
import urllib
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import patch
from pathlib import Path

import requests

from PictureGathering.v2.LikeFetcher import LikeFetcher
from PictureGathering.v2.TwitterAPI import TwitterAPI, TwitterAPIEndpoint


class TestLikeFetcher(unittest.TestCase):
    def setUp(self):
        pass

    def _mock_twitter(self):
        dummy_api_key = "dummy_api_key"
        dummy_api_secret = "dummy_api_secret"
        dummy_access_token_key = "dummy_access_token_key"
        dummy_access_token_secret = "dummy_access_token_secret"

        twitter = None
        with patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"):
            twitter = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
        return twitter

    def _tweet_sample(self):
        JSON_FILE_PATH = "./PictureGathering/v2/api_response_test.txt"
        input_dict = {}
        with codecs.open(JSON_FILE_PATH, "r", "utf-8") as fin:
            input_dict = json.load(fin)
        return input_dict

    def test_LikeFetcher_init(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()
        params = {
            "expansions": "author_id,attachments.media_keys",
            "tweet.fields": "id,attachments,author_id,entities,text,source,created_at",
            "user.fields": "id,name,username,url",
            "media.fields": "url,variants,preview_image_url,alt_text",
            "max_results": max_results,
        }
        api_endpoint_url = TwitterAPIEndpoint.LIKED_TWEET.value[0].format(userid)

        fetcher = LikeFetcher(userid, pages, max_results, twitter)

        self.assertEqual(userid, fetcher.userid)
        self.assertEqual(pages, fetcher.pages)
        self.assertEqual(max_results, fetcher.max_results)
        self.assertEqual(api_endpoint_url, fetcher.api_endpoint_url)
        self.assertEqual(params, fetcher.params)
        self.assertEqual(twitter, fetcher.twitter)

    def test_flatten(self):
        pass

    def test_to_convert_TweetInfo(self):
        pass

    def test_to_convert_ExternalLink(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
