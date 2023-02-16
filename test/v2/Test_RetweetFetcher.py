# coding: utf-8
import codecs
import json
import re
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta

from mock import MagicMock, patch

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.RetweetFetcher import RetweetFetcher, RetweetInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI
from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName


class TestRetweetFetcher(unittest.TestCase):
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

    def _tweet_lookup_sample(self):
        JSON_FILE_PATH = "./PictureGathering/v2/api_response_test_lookup.txt"
        lookuped_dict = {}
        with codecs.open(JSON_FILE_PATH, "r", "utf-8") as fin:
            lookuped_dict = json.load(fin)
        return lookuped_dict[0]

    def _mock_get_tweets_via(self, ids):
        result = [{
            "id": str(n),
            "via": "tweet via of " + str(n),
        } for n in ids]
        return result

    def test_RetweetFetcher_init(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()
        params = {
            "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id,attachments.media_keys",
            "tweet.fields": "id,attachments,author_id,referenced_tweets,entities,text,source,created_at",
            "user.fields": "id,name,username,url",
            "media.fields": "url,variants,preview_image_url,alt_text",
            "max_results": max_results,
        }
        api_endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.TIMELINE_TWEET, userid)

        fetcher = RetweetFetcher(userid, pages, max_results, twitter)

        self.assertEqual(userid, fetcher.userid)
        self.assertEqual(pages, fetcher.pages)
        self.assertEqual(max_results, fetcher.max_results)
        self.assertEqual(api_endpoint_url, fetcher.api_endpoint_url)
        self.assertEqual(params, fetcher.params)
        self.assertEqual(twitter, fetcher.twitter)

    def test_find_tweets(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = RetweetFetcher(userid, pages, max_results, twitter)

        input_dict = self._tweet_sample()
        tweets_list = input_dict[0].get("includes", {}).get("tweets", [])

        tweet_id = "10004"
        actual = fetcher._find_tweets(tweet_id, tweets_list)
        t_list = [tweets for tweets in tweets_list if tweets.get("id", "") == tweet_id]
        expect = t_list[0]
        self.assertEqual(expect, actual)

        tweet_id = "notfound_tweet_id"
        actual = fetcher._find_tweets(tweet_id, tweets_list)
        expect = {}
        self.assertEqual(expect, actual)

        actual = fetcher._find_tweets(-1, tweets_list)
        expect = {}
        self.assertEqual(expect, actual)

        tweet_id = "10004"
        with self.assertRaises(ValueError):
            actual = fetcher._find_tweets(tweet_id, "invalid_users_list")

        with self.assertRaises(ValueError):
            actual = fetcher._find_tweets(tweet_id, [])

        with self.assertRaises(ValueError):
            actual = fetcher._find_tweets(tweet_id, ["invalid_users_list"])

    def test_flatten(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = RetweetFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()

        def flatten(retweeted_tweet):
            data_list = []
            media_list = []
            tweets_list = []
            users_list = []
            for t in retweeted_tweet:
                match t:
                    case {"data": data, "includes": {"media": media, "tweets": tweets, "users": users}}:
                        # ページをまたいでそれぞれ重複しているかもしれないが以後の処理に影響はしない
                        data_list.extend(data)
                        media_list.extend(media)
                        tweets_list.extend(tweets)
                        users_list.extend(users)
                    case _:
                        # RTが1件もない場合、tweetsはおそらく空になる
                        # raise ValueError("argument retweeted_tweet is invalid.")
                        pass
            return data_list, media_list, tweets_list, users_list

        expect = flatten(input_dict)
        actual = fetcher._flatten(input_dict)
        self.assertEqual(expect, actual)

    def test_is_include_referenced_tweets(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = RetweetFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()
        data_list = input_dict[0].get("data", [])

        def is_include_referenced_tweets(data):
            if "referenced_tweets" in data:
                referenced_tweets = data.get("referenced_tweets", [])
                for referenced_tweet in referenced_tweets:
                    referenced_tweet_id = referenced_tweet.get("id", "")
                    referenced_tweet_type = referenced_tweet.get("type", "")
                    if referenced_tweet_id == "":
                        continue
                    if referenced_tweet_type in ["retweeted", "quoted"]:
                        return True
            return False

        for data in data_list:
            expect = is_include_referenced_tweets(data)
            actual = fetcher._is_include_referenced_tweets(data)
            self.assertEqual(expect, actual)

    def test_find_retweet_tree_with_attachments(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = RetweetFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()
        data_list, media_list, tweets_list, users_list = fetcher._flatten(input_dict)

        def find_retweet_tree_with_attachments(fetcher, data_with_referenced_tweets, tweets_list):
            query_need_ids = []
            query_need_tweets = []
            for data in data_with_referenced_tweets:
                referenced_tweets = data.get("referenced_tweets", [])
                for referenced_tweet in referenced_tweets:
                    referenced_tweet_id = referenced_tweet.get("id", "")
                    referenced_tweet_type = referenced_tweet.get("type", "")
                    if referenced_tweet_id == "":
                        continue
                    if referenced_tweet_type not in ["retweeted", "quoted"]:
                        continue

                    tweets = fetcher._find_tweets(referenced_tweet_id, tweets_list)
                    if not tweets:
                        continue

                    match tweets:
                        case {
                            "attachments": {"media_keys": media_keys},
                            "referenced_tweets": n_referenced_tweets,
                        }:
                            query_need_ids.append(referenced_tweet_id)
                            query_need_tweets.append(tweets)

                            for n_referenced_tweet in n_referenced_tweets:
                                query_need_id = n_referenced_tweet.get("id", "")
                                query_need_ids.append(query_need_id)
                        case {
                            "attachments": {"media_keys": media_keys},
                        }:
                            query_need_ids.append(referenced_tweet_id)
                            query_need_tweets.append(tweets)
                        case {
                            "referenced_tweets": n_referenced_tweets,
                        }:
                            for n_referenced_tweet in n_referenced_tweets:
                                query_need_id = n_referenced_tweet.get("id", "")
                                query_need_ids.append(query_need_id)
                        case _:
                            pass
            return query_need_ids, query_need_tweets

        expect = find_retweet_tree_with_attachments(fetcher, data_list, tweets_list)
        actual = fetcher._find_retweet_tree_with_attachments(data_list, tweets_list)
        self.assertEqual(expect, actual)

    def test_find_retweet_tree_with_entities(self):
        userid = "12345"
        pages = 3
        max_results = 100
        twitter = self._mock_twitter()

        fetcher = RetweetFetcher(userid, pages, max_results, twitter)
        input_dict = self._tweet_sample()
        data_list, media_list, tweets_list, users_list = fetcher._flatten(input_dict)

        def find_retweet_tree_with_entities(fetcher, data_with_referenced_tweets, tweets_list):
            query_need_ids = []
            first_level_tweets_list = []
            for data in data_with_referenced_tweets:
                referenced_tweets = data.get("referenced_tweets", [])
                for referenced_tweet in referenced_tweets:
                    referenced_tweet_id = referenced_tweet.get("id", "")
                    referenced_tweet_type = referenced_tweet.get("type", "")
                    if referenced_tweet_id == "":
                        continue
                    if referenced_tweet_type not in ["retweeted", "quoted"]:
                        continue

                    tweets = fetcher._find_tweets(referenced_tweet_id, tweets_list)
                    if not tweets:
                        continue

                    match tweets:
                        case {
                            "entities": {"urls": urls},
                            "referenced_tweets": n_referenced_tweets,
                        }:
                            first_level_tweets_list.append(tweets)
                            for n_referenced_tweet in n_referenced_tweets:
                                query_need_id = n_referenced_tweet.get("id", "")
                                query_need_ids.append(query_need_id)
                        case {
                            "entities": {"urls": urls},
                        }:
                            first_level_tweets_list.append(tweets)
                        case {
                            "referenced_tweets": n_referenced_tweets,
                        }:
                            for n_referenced_tweet in n_referenced_tweets:
                                query_need_id = n_referenced_tweet.get("id", "")
                                query_need_ids.append(query_need_id)
                        case _:
                            pass
            return query_need_ids, first_level_tweets_list

        expect = find_retweet_tree_with_entities(fetcher, data_list, tweets_list)
        actual = fetcher._find_retweet_tree_with_entities(data_list, tweets_list)
        self.assertEqual(expect, actual)

    def test_fetch_tweet_lookup(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.v2.RetweetFetcher.TwitterAPI.get"))
            mock_get.side_effect = lambda url, params: self._tweet_lookup_sample()

            userid = "12345"
            pages = 3
            max_results = 100
            twitter = self._mock_twitter()

            fetcher = RetweetFetcher(userid, pages, max_results, twitter)
            input_dict = self._tweet_sample()
            data_list, media_list, tweets_list, users_list = fetcher._flatten(input_dict)
            query_need_ids, _ = fetcher._find_retweet_tree_with_attachments(data_list, tweets_list)

            def fetch_tweet_lookup(fetcher, query_need_ids, MAX_IDS_NUM=100):
                data_list = []
                media_list = []
                users_list = []
                tweets_lookup_result = self._tweet_lookup_sample()
                match tweets_lookup_result:
                    case {"data": data, "includes": {"media": media, "users": users}}:
                        data_list.extend(data)
                        media_list.extend(media)
                        users_list.extend(users)
                    case _:
                        pass
                return data_list, media_list, users_list

            expect = fetch_tweet_lookup(fetcher, query_need_ids)
            actual = fetcher._fetch_tweet_lookup(query_need_ids)
            self.assertEqual(expect, actual)

    def test_to_convert_TweetInfo(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.v2.RetweetFetcher.TwitterAPI.get"))
            mock_get_tweets_via = stack.enter_context(patch("PictureGathering.v2.RetweetFetcher.RetweetFetcher._get_tweets_via"))
            mock_get.side_effect = lambda url, params: self._tweet_lookup_sample()
            mock_get_tweets_via.side_effect = self._mock_get_tweets_via

            userid = "12345"
            pages = 3
            max_results = 100
            twitter = self._mock_twitter()

            fetcher = RetweetFetcher(userid, pages, max_results, twitter)
            input_dict = self._tweet_sample()
            data_list, media_list, tweets_list, users_list = fetcher._flatten(input_dict)
            query_need_ids, _ = fetcher._find_retweet_tree_with_attachments(data_list, tweets_list)

            def to_convert_TweetInfo(fetcher, retweeted_tweet):
                data_list, media_list, tweets_list, users_list = fetcher._flatten(retweeted_tweet)

                data_with_referenced_tweets = [data for data in data_list if fetcher._is_include_referenced_tweets(data)]
                query_need_ids, query_need_tweets = fetcher._find_retweet_tree_with_attachments(data_with_referenced_tweets, tweets_list)
                seen_ids = []
                query_need_ids = [i for i in query_need_ids if i not in seen_ids and not seen_ids.append(i)]

                MAX_IDS_NUM = 100
                second_level_tweets_list, lookuped_media_list, lookuped_users_list = fetcher._fetch_tweet_lookup(query_need_ids, MAX_IDS_NUM)
                media_list.extend(lookuped_media_list)
                users_list.extend(lookuped_users_list)

                first_level_tweets_list = []
                first_level_tweets_list.extend(query_need_tweets)

                target_data_list = []
                target_data_list.extend(first_level_tweets_list)
                target_data_list.extend(second_level_tweets_list)

                seen_ids = []
                result = []
                for data in target_data_list:
                    match data:
                        case {
                            "attachments": {"media_keys": media_keys},
                            "author_id": author_id,
                            "created_at": created_at,
                            "entities": {"urls": urls},
                            "id": id_str,
                            # "source": via,
                            "text": text
                        }:
                            referenced_tweet_id = id_str
                            tweet_via = data.get("source", "unknown via")
                            tweet_text = text

                            if referenced_tweet_id in seen_ids:
                                continue

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
                                    "tweet_id": referenced_tweet_id,
                                    "tweet_url": tweet_url,
                                    "created_at": dst,
                                    "user_id": user_id,
                                    "user_name": user_name,
                                    "screan_name": screan_name,
                                    "tweet_text": tweet_text,
                                    "tweet_via": tweet_via,
                                }
                                result.append(RetweetInfo.create(r))

                                if referenced_tweet_id not in seen_ids:
                                    seen_ids.append(referenced_tweet_id)
                        case _:
                            continue

                via_list = fetcher._get_tweets_via(seen_ids)
                for i, r in enumerate(result):
                    if r.tweet_via == "unknown via":
                        via_element = [d for d in via_list if d.get("id") == r.tweet_id]
                        if len(via_element) == 0:
                            continue
                        via = via_element[0].get("via", "unknown via")
                        r_dict = r.to_dict()
                        r_dict["tweet_via"] = via
                        result[i] = RetweetInfo.create(r_dict)

                return result

            expect = to_convert_TweetInfo(fetcher, input_dict)
            actual = fetcher.to_convert_TweetInfo(input_dict)
            self.assertEqual(expect, actual)

    def test_to_convert_ExternalLink(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.v2.RetweetFetcher.TwitterAPI.get"))
            mock_get_tweets_via = stack.enter_context(patch("PictureGathering.v2.RetweetFetcher.RetweetFetcher._get_tweets_via"))
            mock_get.side_effect = lambda url, params: self._tweet_lookup_sample()
            mock_get_tweets_via.side_effect = self._mock_get_tweets_via

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

            fetcher = RetweetFetcher(userid, pages, max_results, twitter)
            input_dict = self._tweet_sample()
            data_list, media_list, tweets_list, users_list = fetcher._flatten(input_dict)
            query_need_ids, _ = fetcher._find_retweet_tree_with_attachments(data_list, tweets_list)

            def to_convert_ExternalLink(fetcher, retweeted_tweet, link_searcher):
                data_list, media_list, tweets_list, users_list = fetcher._flatten(retweeted_tweet)

                data_with_referenced_tweets = [data for data in data_list if fetcher._is_include_referenced_tweets(data)]
                query_need_ids, first_level_tweets_list = fetcher._find_retweet_tree_with_entities(data_with_referenced_tweets, tweets_list)
                seen_ids = []
                query_need_ids = [i for i in query_need_ids if i not in seen_ids and not seen_ids.append(i)]

                MAX_IDS_NUM = 100
                second_level_tweets_list, lookuped_media_list, lookuped_users_list = fetcher._fetch_tweet_lookup(query_need_ids, MAX_IDS_NUM)
                media_list.extend(lookuped_media_list)
                users_list.extend(lookuped_users_list)

                target_data_list = []
                target_data_list.extend(first_level_tweets_list)
                target_data_list.extend(second_level_tweets_list)

                seen_ids = []
                result = []
                for data in target_data_list:
                    match data:
                        case {
                            "author_id": author_id,
                            "created_at": created_at,
                            "entities": {"urls": urls},
                            "id": id_str,
                            # "source": via,
                            "text": text
                        }:
                            tweet_id = id_str
                            tweet_via = data.get("source", "unknown via")
                            tweet_text = text
                            link_type = ""

                            if tweet_id in seen_ids:
                                continue

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

                                # resultレコード作成
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

                                if tweet_id not in seen_ids:
                                    seen_ids.append(tweet_id)
                        case _:
                            continue

                via_list = fetcher._get_tweets_via(seen_ids)
                for i, r in enumerate(result):
                    if r.tweet_via == "unknown via":
                        via_element = [d for d in via_list if d.get("id") == r.tweet_id]
                        if len(via_element) == 0:
                            continue
                        via = via_element[0].get("via", "unknown via")
                        r_dict = r.to_dict()
                        r_dict["tweet_via"] = via
                        result[i] = ExternalLink.create(r_dict)

                return result

            expect = to_convert_ExternalLink(fetcher, input_dict, lsb)
            actual = fetcher.to_convert_ExternalLink(input_dict, lsb)
            self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
