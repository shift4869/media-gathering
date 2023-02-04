# coding: utf-8
import codecs
import json
import sys
import unittest
import urllib
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, patch
from pathlib import Path

import requests

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.TweetInfo import TweetInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI
from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName
from PictureGathering.v2.V2Base import V2Base


logger = getLogger("PictureGathering.v2.V2Base")
logger.setLevel(WARNING)


class ConcreteV2Base(V2Base):
    def to_convert_TweetInfo(self, fetched_tweets: list[dict]) -> list[TweetInfo]:
        return []

    def to_convert_ExternalLink(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        return []


class TestV2Base(unittest.TestCase):
    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)

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

    def test_V2Base_init(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        self.assertEqual(api_endpoint_url, fetcher.api_endpoint_url)
        self.assertEqual(params, fetcher.params)
        self.assertEqual(pages, fetcher.pages)
        self.assertEqual(twitter, fetcher.twitter)

        with self.assertRaises(ValueError):
            fetcher = ConcreteV2Base("invalid_endpoint_url", params, pages, twitter)

    def test_fetch(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "info"))
            mock_twitter = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"))

            api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
            params = {"dummy_params": "dummy_params"}
            pages = 3
            twitter = self._mock_twitter()

            fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

            input_dict = self._tweet_sample()
            mock_twitter.side_effect = input_dict
            expect = input_dict
            actual = fetcher.fetch()
            self.assertEqual(expect, actual)

            mock_twitter.side_effect = requests.exceptions.RequestException
            with self.assertRaises(requests.exceptions.RequestException):
                actual = fetcher.fetch()

    def test_find_name(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        input_dict = self._tweet_sample()
        users_list = input_dict[0].get("includes", {}).get("users", [])

        user_id = "001"
        actual = fetcher._find_name(user_id, users_list)
        expect = ("test_user", "test_user_screenname")
        self.assertEqual(expect, actual)

        user_id = "notfound_user_id"
        actual = fetcher._find_name(user_id, users_list)
        expect = ("<null>", "<null>")
        self.assertEqual(expect, actual)

        user_id = "123456789"
        with self.assertRaises(ValueError):
            actual = fetcher._find_name(user_id, "invalid_users_list")

        with self.assertRaises(ValueError):
            actual = fetcher._find_name(user_id, [])

        with self.assertRaises(ValueError):
            actual = fetcher._find_name(user_id, ["invalid_users_list"])

    def test_find_media(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        input_dict = self._tweet_sample()
        media_list = input_dict[0].get("includes", {}).get("media", [])

        media_key = "0001"
        actual = fetcher._find_media(media_key, media_list)
        expect = {
            "media_key": "0001",
            "url": "https://pbs.twimg.com/media/test_file_name_0001.jpg",
            "type": "photo"
        }
        self.assertEqual(expect, actual)

        media_key = "notfound_media_key"
        actual = fetcher._find_media(media_key, media_list)
        expect = {}
        self.assertEqual(expect, actual)

        media_key = "1_123456789"
        with self.assertRaises(ValueError):
            actual = fetcher._find_media(media_key, "invalid_media_list")

        with self.assertRaises(ValueError):
            actual = fetcher._find_media(media_key, [])

        with self.assertRaises(ValueError):
            actual = fetcher._find_media(media_key, ["invalid_media_list"])

        with self.assertRaises(ValueError):
            actual = fetcher._find_media(123456789, media_list)

    def test_match_tweet_url(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        input_dict = self._tweet_sample()
        data_list = input_dict[0].get("data", [])
        entities = data_list[0].get("entities")

        urls = entities.get("urls", [])
        actual = fetcher._match_tweet_url(urls)
        expect = "https://twitter.com/test_user/status/00001/photo/1"
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = fetcher._match_tweet_url([{}])

        with self.assertRaises(ValueError):
            actual = fetcher._match_tweet_url("invalid_urls")

        with self.assertRaises(ValueError):
            actual = fetcher._match_tweet_url([])

        with self.assertRaises(ValueError):
            actual = fetcher._match_tweet_url(["invalid_urls"])

    def test_match_media_info(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        input_dict = self._tweet_sample()
        media_list = input_dict[0].get("includes", {}).get("media", [])

        media = media_list[0]
        actual = fetcher._match_media_info(media)
        e_m_url = "https://pbs.twimg.com/media/test_file_name_0001.jpg"
        expect = (
            Path(e_m_url).name,
            e_m_url + ":orig",
            e_m_url + ":large",
        )
        self.assertEqual(expect, actual)

        media = media_list[1]
        actual = fetcher._match_media_info(media)
        e_p_url = "https://pbs.twimg.com/ext_tw_video_thumb/123456789123456789/pu/img/test_thumbnail_file_name.jpg"
        e_m_url = fetcher._match_video_url(media.get("variants", []))
        e_media_thumbnail_url = e_p_url + ":orig"
        url_path = Path(urllib.parse.urlparse(e_m_url).path)
        e_media_url = urllib.parse.urljoin(e_m_url, url_path.name)
        e_media_filename = Path(e_media_url).name
        expect = (
            e_media_filename,
            e_media_url,
            e_media_thumbnail_url,
        )
        self.assertEqual(expect, actual)

        media = {}
        actual = fetcher._match_media_info(media)
        expect = ("", "", "")
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = fetcher._match_media_info("invalid_media")

    def test_match_video_url(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        input_dict = self._tweet_sample()
        media_list = input_dict[0].get("includes", {}).get("media", [])
        media = media_list[1]
        variants = media.get("variants", [])

        actual = fetcher._match_video_url(variants)
        expect = "https://video.twimg.com/ext_tw_video/123456789123456789/pu/vid/882x720/test_file_name.mp4?tag=10"
        self.assertEqual(expect, actual)

        actual = fetcher._match_video_url([{}])
        expect = ""
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = fetcher._match_video_url("invalid_variants")

        with self.assertRaises(ValueError):
            actual = fetcher._match_video_url([])

        with self.assertRaises(ValueError):
            actual = fetcher._match_video_url(["invalid_variants"])

    def test_match_expanded_url(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        input_dict = self._tweet_sample()
        data_list = input_dict[0].get("data", [])
        entities = data_list[0].get("entities")

        urls = entities.get("urls", [])
        actual = fetcher._match_expanded_url(urls)
        expect = ["https://twitter.com/test_user/status/00001/photo/1"]
        self.assertEqual(expect, actual)

        expect = []
        actual = fetcher._match_expanded_url([{}])
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = fetcher._match_expanded_url("invalid_urls")

        with self.assertRaises(ValueError):
            actual = fetcher._match_expanded_url([])

        with self.assertRaises(ValueError):
            actual = fetcher._match_expanded_url(["invalid_urls"])

    def test_get_tweets_via(self):
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        params = {"dummy_params": "dummy_params"}
        pages = 3
        twitter = self._mock_twitter()

        fetcher = ConcreteV2Base(api_endpoint_url, params, pages, twitter)

        def make_tweet_dict(url, params):
            ids = params.get("id").split(",")
            res = [{
                "id_str": str(n),
                "source": "<a>" + "tweet via of " + str(n) + "</a>",
            } for n in ids]
            return res

        fetcher.twitter = MagicMock()
        fetcher.twitter.get = make_tweet_dict

        ids = ["1619144454337892353", "1619144806143500289"]
        actual = fetcher._get_tweets_via(ids)
        expect = [{
            "id": str(n),
            "via": "tweet via of " + str(n),
        } for n in ids]
        self.assertEqual(expect, actual)

        ids = []
        actual = fetcher._get_tweets_via(ids)
        expect = []
        self.assertEqual(expect, actual)

        def make_exception(url, params):
            raise Exception(url, params)

        ids = ["1619144454337892353", "1619144806143500289"]
        fetcher.twitter.get = make_exception
        with self.assertRaises(Exception):
            actual = fetcher._get_tweets_via(ids)

if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
