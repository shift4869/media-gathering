# coding: utf-8
import codecs
import json
import re
import sys
import unittest
from datetime import datetime, timedelta
from mock import patch

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.LikeFetcher import LikeFetcher, LikeInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI
from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName


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
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.LIKED_TWEET, userid)

        fetcher = LikeFetcher(userid, pages, max_results, twitter)

        self.assertEqual(userid, fetcher.userid)
        self.assertEqual(pages, fetcher.pages)
        self.assertEqual(max_results, fetcher.max_results)
        self.assertEqual(api_endpoint_url, fetcher.api_endpoint_url)
        self.assertEqual(params, fetcher.params)
        self.assertEqual(twitter, fetcher.twitter)

    def test_flatten(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = LikeFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()

        def flatten(liked_tweet):
            data_list = []
            media_list = []
            users_list = []
            for t in liked_tweet:
                match t:
                    case {"data": data, "includes": {"media": media, "users": users}}:
                        data_list.extend(data)
                        media_list.extend(media)
                        users_list.extend(users)
                    case _:
                        continue
            return data_list, media_list, users_list

        expect = flatten(input_dict)
        actual = fetcher._flatten(input_dict)
        self.assertEqual(expect, actual)

    def test_to_convert_TweetInfo(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = LikeFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()

        def to_convert_TweetInfo(fetcher, liked_tweet):
            data_list, media_list, users_list = fetcher._flatten(liked_tweet)
            result = []
            for data in data_list:
                match data:
                    case {
                        "attachments": {"media_keys": media_keys},
                        "author_id": author_id,
                        "created_at": created_at,
                        "entities": {"urls": urls},
                        "id": id_str,
                        "source": via,
                        "text": text
                    }:
                        tweet_id = id_str
                        tweet_via = via
                        tweet_text = text

                        user_id = author_id
                        user_name, screan_name = fetcher._find_name(user_id, users_list)

                        tweet_url = fetcher._match_tweet_url(urls)

                        dts_format = "%Y-%m-%d %H:%M:%S"
                        zoned_created_at = str(created_at).replace("Z", "+00:00")
                        utc = datetime.fromisoformat(zoned_created_at)
                        jst = utc + timedelta(hours=9)
                        dst = jst.strftime(dts_format)

                        for media_key in media_keys:
                            media_filename = ""
                            media_url = ""
                            media_thumbnail_url = ""

                            media = fetcher._find_media(media_key, media_list)
                            media_filename, media_url, media_thumbnail_url = fetcher._match_media_info(media)

                            if media_filename == "" or media_url == "" or media_thumbnail_url == "":
                                continue

                            r = {
                                "media_filename": media_filename,
                                "media_url": media_url,
                                "media_thumbnail_url": media_thumbnail_url,
                                "tweet_id": tweet_id,
                                "tweet_url": tweet_url,
                                "created_at": dst,
                                "user_id": user_id,
                                "user_name": user_name,
                                "screan_name": screan_name,
                                "tweet_text": tweet_text,
                                "tweet_via": tweet_via,
                            }
                            result.append(LikeInfo.create(r))
                    case _:
                        continue
            return result

        expect = to_convert_TweetInfo(fetcher, input_dict)
        actual = fetcher.to_convert_TweetInfo(input_dict)
        self.assertEqual(expect, actual)

        expect = to_convert_TweetInfo(fetcher, [])
        actual = fetcher.to_convert_TweetInfo([])
        self.assertEqual(expect, actual)

    def test_to_convert_ExternalLink(self):
        class SampleLinksearcher(FetcherBase):
            def is_target_url(self, url: URL) -> bool:
                PIXIV_URL_PATTERN = r"^https://www.pixiv.net/artworks/[0-9]+"
                return re.search(PIXIV_URL_PATTERN, url.original_url) is not None

            def fetch(self, url: URL) -> None:
                pass

        lsb = LinkSearcher()
        lsb.register(SampleLinksearcher())

        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = LikeFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()

        def to_convert_ExternalLink(fetcher, liked_tweet, link_searcher):
            data_list, media_list, users_list = fetcher._flatten(liked_tweet)
            result = []
            for data in data_list:
                match data:
                    case {
                        "author_id": author_id,
                        "created_at": created_at,
                        "entities": {"urls": urls},
                        "id": id_str,
                        "source": via,
                        "text": text
                    }:
                        tweet_id = id_str
                        tweet_via = via
                        tweet_text = text
                        link_type = ""

                        user_id = author_id
                        user_name, screan_name = fetcher._find_name(user_id, users_list)

                        tweet_url = f"https://twitter.com/{screan_name}/status/{tweet_id}"

                        dts_format = "%Y-%m-%d %H:%M:%S"
                        zoned_created_at = str(created_at).replace("Z", "+00:00")
                        utc = datetime.fromisoformat(zoned_created_at)
                        jst = utc + timedelta(hours=9)
                        dst = jst.strftime(dts_format)

                        saved_created_at = datetime.now().strftime(dts_format)

                        expanded_urls = fetcher._match_expanded_url(urls)

                        for expanded_url in expanded_urls:
                            if not link_searcher.can_fetch(expanded_url):
                                continue
                            r = {
                                "external_link_url": expanded_url,
                                "tweet_id": tweet_id,
                                "tweet_url": tweet_url,
                                "created_at": dst,
                                "user_id": user_id,
                                "user_name": user_name,
                                "screan_name": screan_name,
                                "tweet_text": tweet_text,
                                "tweet_via": tweet_via,
                                "saved_created_at": saved_created_at,
                                "link_type": link_type,
                            }
                            result.append(ExternalLink.create(r))
                    case _:
                        continue
            return result

        expect = to_convert_ExternalLink(fetcher, input_dict, lsb)
        actual = fetcher.to_convert_ExternalLink(input_dict, lsb)
        self.assertEqual(expect, actual)

        expect = to_convert_ExternalLink(fetcher, [], lsb)
        actual = fetcher.to_convert_ExternalLink([], lsb)
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
