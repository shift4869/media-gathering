# coding: utf-8
import json
import re
import shutil
import sys
import unittest
import urllib.parse
from contextlib import ExitStack
from datetime import datetime, timedelta
from itertools import chain, repeat
from pathlib import Path

from mock import MagicMock, call, patch

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.Model import ExternalLink
from PictureGathering.noapi.NoAPILikeFetcher import NoAPILikeFetcher
from PictureGathering.noapi.TweetInfo import TweetInfo


class TestNoAPILikeFetcher(unittest.TestCase):
    def setUp(self):
        self.ct0 = "dummy_ct0"
        self.auth_token = "dummy_auth_token"
        self.target_screen_name = "dummy_target_screen_name"
        self.target_id = "99999999"  # dummy_target_id

        self.TWITTER_CACHE_PATH = Path(__file__).parent / "cache/actual"

        with ExitStack() as stack:
            # self.mock_twitter_session = stack.enter_context(patch("PictureGathering.noapi.NoAPILikeFetcher.TwitterSession.create"))
            # self.mock_twitter_session.side_effect = AsyncMock
            self.fetcher = NoAPILikeFetcher(self.ct0, self.auth_token, self.target_screen_name, self.target_id)
            self.fetcher.TWITTER_CACHE_PATH = self.TWITTER_CACHE_PATH

    def tearDown(self):
        if self.TWITTER_CACHE_PATH.exists():
            shutil.rmtree(self.TWITTER_CACHE_PATH)

    def _get_sample_json(self) -> list[dict]:
        TEST_CACHE_PATH = self.TWITTER_CACHE_PATH.parent / "expect"
        with (TEST_CACHE_PATH / "content_cache_likes_test.txt").open("r", encoding="utf8") as fin:
            return json.load(fin)

    def _get_tweets(self):
        data = self._get_sample_json()
        entries = data.get("data", {}) \
                      .get("user", {}) \
                      .get("result", {}) \
                      .get("timeline_v2", {}) \
                      .get("timeline", {}) \
                      .get("instructions", [{}])[0] \
                      .get("entries", [{}])

        def entry_to_tweet(entry) -> dict:
            match entry:
                case {
                    "content": {
                        "itemContent": {
                            "tweet_results": {
                                "result": result
                            }
                        }
                    }
                }:
                    return result
            return {}
        result = [entry_to_tweet(entry) for entry in entries]
        return result

    def test_init(self):
        self.assertEqual(self.TWITTER_CACHE_PATH, self.fetcher.TWITTER_CACHE_PATH)
        self.assertEqual(self.ct0, self.fetcher.ct0)
        self.assertEqual(self.auth_token, self.fetcher.auth_token)
        self.assertEqual(self.target_screen_name, self.fetcher.target_username.name)
        self.assertEqual(int(self.target_id), self.fetcher.target_id)

    def test_get_like_jsons(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch("PictureGathering.noapi.NoAPILikeFetcher.logger.info"))
            mock_scraper = stack.enter_context(patch("PictureGathering.noapi.NoAPILikeFetcher.Scraper"))
            r = MagicMock()

            DUP_NUM = 3
            sample_jsons = list(repeat(self._get_sample_json(), DUP_NUM))
            r.likes.side_effect = lambda user_ids, limit: sample_jsons
            mock_scraper.side_effect = lambda cookies, pbar: r

            limit = 400
            actual = self.fetcher.get_like_jsons(limit)
            self.assertEqual(sample_jsons, actual)

            expect = [f"likes_{i:02}.json" for i in range(DUP_NUM)]
            actual_cache = self.fetcher.TWITTER_CACHE_PATH.glob("likes*.json")
            actual = [p.name for p in actual_cache]
            expect.sort()
            actual.sort()
            self.assertEqual(expect, actual)

            mock_scraper.assert_called_once_with(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
            r.likes.assert_called_once_with([int(self.target_id)], limit=limit)

    def test_interpret_json(self):
        tweets = self._get_tweets()
        actual = []
        for tweet in tweets:
            actual.append(self.fetcher.interpret_json(tweet))
        expect = [
            [],
            [tweets[1]],
            [tweets[2]],
            [tweets[3]],
            [tweets[4]],
            [tweets[5]],
            [tweets[6]],
            [tweets[7].get("retweeted_status_result", {})
                      .get("result", {})],
            [tweets[8].get("quoted_status_result", {})
                      .get("result", {})],
            [tweets[9].get("retweeted_status_result", {})
                      .get("result", {})
                      .get("quoted_status_result", {})
                      .get("result", {})],
        ]
        self.assertEqual(expect, actual)

        with self.assertRaises(TypeError):
            self.fetcher.interpret_json(-1)

    def test_fetch(self):
        with ExitStack() as stack:
            mock_get_like_jsons = stack.enter_context(patch("PictureGathering.noapi.NoAPILikeFetcher.NoAPILikeFetcher.get_like_jsons"))
            actual = self.fetcher.fetch()
            mock_get_like_jsons.assert_called_once_with()

    def test_find_values(self):
        fetched_tweets = [self._get_sample_json()]
        actual = self.fetcher._find_values(fetched_tweets, "tweet_results")

        def find_tweet_results(fetched_tweets: list[dict]):
            target_data_list: list[dict] = []
            for r in fetched_tweets:
                r1 = r.get("data", {}) \
                      .get("user", {}) \
                      .get("result", {}) \
                      .get("timeline_v2", {}) \
                      .get("timeline", {}) \
                      .get("instructions", [{}])[0]
                if not r1:
                    continue
                entries: list[dict] = r1.get("entries", [])
                for entry in entries:
                    e1 = entry.get("content", {}) \
                              .get("itemContent", {}) \
                              .get("tweet_results", {})
                    target_data_list.append(e1)
            return target_data_list

        expect = find_tweet_results(fetched_tweets)
        self.assertEqual(expect, actual)

        actual = self.fetcher._find_values(fetched_tweets, "no_exist_key")
        self.assertEqual([], actual)

        actual = self.fetcher._find_values("invalid_object", "no_exist_key")
        self.assertEqual([], actual)

    def test_match_data(self):
        tweets = self._get_tweets()
        actual = [self.fetcher._match_data(tweet) for tweet in tweets]

        def match_data(data):
            match data:
                case {
                    "core": {"user_results": {"result": {"legacy": author}}},
                    "legacy": tweet,
                    "source": via_html,
                }:
                    via = re.findall("^<.+?>([^<]*?)<.+?>$", via_html)[0]
                    result = {
                        "author": author,
                        "tweet": tweet,
                        "via": via,
                    }
                    return result
            return {}

        expect = [match_data(tweet) for tweet in tweets]
        self.assertEqual(expect, actual)

        actual = self.fetcher._match_data({"invalid_struct_dict": "invalid"})
        self.assertEqual({}, actual)

        actual = self.fetcher._match_data(-1)
        self.assertEqual({}, actual)

    def test_match_extended_entities_tweet(self):
        tweets = self._get_tweets()
        actual = [self.fetcher._match_extended_entities_tweet(tweet.get("tweet", {}))
                  for tweet in tweets]

        def match_extended_entities_tweet(tweet: dict) -> dict:
            match tweet:
                case {
                    "created_at": created_at,
                    # "entities": entities,
                    "extended_entities": extended_entities,
                    "full_text": full_text,
                    "id_str": id_str,
                    "user_id_str": author_id,
                    # "source": via,
                }:
                    result = {
                        "author_id": author_id,
                        "created_at": created_at,
                        # "entities": entities,
                        "extended_entities": extended_entities,
                        "id_str": id_str,
                        "text": full_text,
                    }
                    return result
            return {}
        expect = [match_extended_entities_tweet(tweet.get("tweet", {}))
                  for tweet in tweets]
        self.assertEqual(expect, actual)

        actual = self.fetcher._match_extended_entities_tweet({"invalid_struct_dict": "invalid"})
        self.assertEqual({}, actual)

        actual = self.fetcher._match_extended_entities_tweet(-1)
        self.assertEqual({}, actual)

    def test_match_entities_tweet(self):
        tweets = self._get_tweets()
        actual = [self.fetcher._match_entities_tweet(tweet.get("tweet", {}))
                  for tweet in tweets]

        def match_entities_tweet(tweet: dict) -> dict:
            match tweet:
                case {
                    "created_at": created_at,
                    "entities": entities,
                    "full_text": full_text,
                    "id_str": id_str,
                    "user_id_str": author_id,
                    # "source": via,
                }:
                    r = {
                        "author_id": author_id,
                        "created_at": created_at,
                        "entities": entities,
                        "id_str": id_str,
                        "text": full_text,
                    }
                    return r
            return {}
        expect = [match_entities_tweet(tweet.get("tweet", {}))
                  for tweet in tweets]
        self.assertEqual(expect, actual)

        actual = self.fetcher._match_entities_tweet({"invalid_struct_dict": "invalid"})
        self.assertEqual({}, actual)

        actual = self.fetcher._match_entities_tweet(-1)
        self.assertEqual({}, actual)

    def test_match_entities(self):
        tweets = self._get_tweets()
        interpreted_tweets = [t if (t := self.fetcher.interpret_json(tweet)) != []
                              else [{}]
                              for tweet in tweets]
        tweet_list = [self.fetcher._match_data(data[0]).get("tweet", {})
                      for data in interpreted_tweets]
        entities_tweet = [self.fetcher._match_entities_tweet(tweet)
                          for tweet in tweet_list]
        actual = [self.fetcher._match_entities(entities.get("entities", {}))
                  for entities in entities_tweet]

        def match_entities_tweet(entities: dict) -> dict:
            match entities:
                case {"urls": urls_dict}:
                    expanded_urls = []
                    for url_dict in urls_dict:
                        expanded_url = url_dict.get("expanded_url", "")
                        if not expanded_url:
                            continue
                        expanded_urls.append(expanded_url)
                    return {"expanded_urls": expanded_urls}
            return {}
        expect = [match_entities_tweet(entities.get("entities", {}))
                  for entities in entities_tweet]
        self.assertEqual(expect, actual)

        actual = self.fetcher._match_entities_tweet({"invalid_struct_dict": "invalid"})
        self.assertEqual({}, actual)

        actual = self.fetcher._match_entities_tweet(-1)
        self.assertEqual({}, actual)

    def test_match_media(self):
        tweets = self._get_tweets()
        interpreted_tweets = [t if (t := self.fetcher.interpret_json(tweet)) != []
                              else [{}]
                              for tweet in tweets]
        tweet_list = [self.fetcher._match_data(data[0]).get("tweet", {})
                      for data in interpreted_tweets]
        extended_entities_tweet = [self.fetcher._match_extended_entities_tweet(tweet)
                                   for tweet in tweet_list]
        media_list = [extended_entities.get("extended_entities", {}).get("media", [{}])
                      for extended_entities in extended_entities_tweet]
        flattend_media_list = list(chain.from_iterable(media_list))
        actual = [self.fetcher._match_media(media)
                  for media in flattend_media_list]

        def match_media(media: dict) -> dict:
            match media:
                case {
                    "type": "photo",
                    "media_url_https": media_url,
                }:
                    media_filename = Path(media_url).name
                    media_thumbnail_url = media_url + ":large"
                    media_url = media_url + ":orig"
                    result = {
                        "media_filename": media_filename,
                        "media_url": media_url,
                        "media_thumbnail_url": media_thumbnail_url,
                    }
                    return result
                case {
                    "type": "video" | "animated_gif",
                    "video_info": {"variants": video_variants},
                    "media_url_https": media_thumbnail_url,
                }:
                    media_url = ""
                    bitrate = -sys.maxsize
                    for video_variant in video_variants:
                        if video_variant["content_type"] == "video/mp4":
                            if int(video_variant["bitrate"]) > bitrate:
                                media_url = video_variant["url"]
                                bitrate = int(video_variant["bitrate"])
                    url_path = Path(urllib.parse.urlparse(media_url).path)
                    media_url = urllib.parse.urljoin(media_url, url_path.name)
                    media_filename = Path(media_url).name
                    media_thumbnail_url = media_thumbnail_url + ":orig"
                    result = {
                        "media_filename": media_filename,
                        "media_url": media_url,
                        "media_thumbnail_url": media_thumbnail_url,
                    }
                    return result
            return {}

        expect = [match_media(media) for media in flattend_media_list]
        self.assertEqual(expect, actual)

        actual = self.fetcher._match_media({"invalid_struct_dict": "invalid"})
        self.assertEqual({}, actual)

        actual = self.fetcher._match_media(-1)
        self.assertEqual({}, actual)

    def test_to_convert_TweetInfo(self):
        fetched_tweets = [self._get_sample_json()]
        actual = self.fetcher.to_convert_TweetInfo(fetched_tweets)

        def to_convert_TweetInfo(fetched_tweets: list[dict]):
            target_data_list: list[dict] = []
            for r in fetched_tweets:
                r1 = r.get("data", {}) \
                      .get("user", {}) \
                      .get("result", {}) \
                      .get("timeline_v2", {}) \
                      .get("timeline", {}) \
                      .get("instructions", [{}])[0]
                if not r1:
                    continue
                entries: list[dict] = r1.get("entries", [])
                for entry in entries:
                    e1 = entry.get("content", {}) \
                              .get("itemContent", {}) \
                              .get("tweet_results", {}) \
                              .get("result", {})
                    t = self.fetcher.interpret_json(e1)
                    if not t:
                        continue
                    target_data_list.extend(t)

            if not target_data_list:
                return []

            seen_ids: list[str] = []
            result: list[TweetInfo] = []
            for data in target_data_list:
                data_dict = self.fetcher._match_data(data)
                if not data_dict:
                    continue
                author = data_dict.get("author", {})
                tweet = data_dict.get("tweet", {})
                via = data_dict.get("via", "")

                tweet_dict = self.fetcher._match_extended_entities_tweet(tweet)
                if not tweet_dict:
                    continue
                created_at = tweet_dict.get("created_at", "")
                extended_entities = tweet_dict.get("extended_entities", {})
                tweet_text = tweet_dict.get("text", "")
                author_id = tweet_dict.get("author_id", "")
                id_str = tweet_dict.get("id_str", "")

                liked_tweet_id = id_str
                tweet_via = via

                if liked_tweet_id in seen_ids:
                    continue

                user_id = author_id
                user_name, screan_name = author.get("name"), author.get("screen_name")
                tweet_url = extended_entities.get("media", [{}])[0].get("expanded_url", "")
                td_format = "%a %b %d %H:%M:%S +0000 %Y"
                dts_format = "%Y-%m-%d %H:%M:%S"
                jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
                dst = jst.strftime(dts_format)

                media_list = extended_entities.get("media", [])
                for media in media_list:
                    media_dict = self.fetcher._match_media(media)
                    if not media_dict:
                        continue
                    media_filename = media_dict.get("media_filename", "")
                    media_url = media_dict.get("media_url", "")
                    media_thumbnail_url = media_dict.get("media_thumbnail_url", "")
                    r = {
                        "media_filename": media_filename,
                        "media_url": media_url,
                        "media_thumbnail_url": media_thumbnail_url,
                        "tweet_id": liked_tweet_id,
                        "tweet_url": tweet_url,
                        "created_at": dst,
                        "user_id": user_id,
                        "user_name": user_name,
                        "screan_name": screan_name,
                        "tweet_text": tweet_text,
                        "tweet_via": tweet_via,
                    }
                    result.append(TweetInfo.create(r))

                    if liked_tweet_id not in seen_ids:
                        seen_ids.append(liked_tweet_id)
            result.reverse()
            return result

        expect = to_convert_TweetInfo(fetched_tweets)
        self.assertEqual(expect, actual)

        actual = self.fetcher.to_convert_TweetInfo([{"invalid_struct_dict": "invalid"}])
        self.assertEqual([], actual)

        actual = self.fetcher.to_convert_TweetInfo(["invalid_args"])
        self.assertEqual([], actual)

        actual = self.fetcher.to_convert_TweetInfo(-1)
        self.assertEqual([], actual)

    def test_to_convert_ExternalLink(self):
        class SimpleFetcher(FetcherBase):
            def is_target_url(self, url: URL):
                estimated_url = url.non_query_url
                f1 = re.search(r"^https://www.pixiv.net/artworks/[0-9]+", estimated_url) is not None
                f2 = re.search(r"^https://skeb.jp/\@(.+?)/works/([0-9]+)", estimated_url) is not None
                return f1 or f2

            def fetch(self):
                pass
        slf = SimpleFetcher()
        ls = LinkSearcher()
        ls.register(slf)

        fetched_tweets = [self._get_sample_json()]
        actual = self.fetcher.to_convert_ExternalLink(fetched_tweets, ls)

        def to_convert_ExternalLink(fetched_tweets: list[dict], link_searcher: LinkSearcher):
            target_data_list = []
            for r in fetched_tweets:
                r1 = r.get("data", {}) \
                      .get("user", {}) \
                      .get("result", {}) \
                      .get("timeline_v2", {}) \
                      .get("timeline", {}) \
                      .get("instructions", [{}])[0]
                if not r1:
                    continue
                entries: list[dict] = r1.get("entries", [])
                for entry in entries:
                    e1 = entry.get("content", {}) \
                              .get("itemContent", {}) \
                              .get("tweet_results", {}) \
                              .get("result", {})
                    t = self.fetcher.interpret_json(e1)
                    if not t:
                        continue
                    target_data_list.extend(t)

            if not target_data_list:
                # 辞書パースエラー or 1件もツイートが無かった
                # raise ValueError("no tweet included in fetched_tweets.")
                return []

            # target_data_list を入力として 外部リンク情報を収集
            # 外部リンク情報を含むかどうかを確認しつつ、対象ならば収集する
            seen_ids: list[str] = []
            result: list[ExternalLink] = []
            for data in target_data_list:
                data_dict = self.fetcher._match_data(data)
                if not data_dict:
                    continue
                author = data_dict.get("author", {})
                tweet = data_dict.get("tweet", {})
                via = data_dict.get("via", "")

                tweet_dict = self.fetcher._match_entities_tweet(tweet)
                if not tweet_dict:
                    continue
                created_at = tweet_dict.get("created_at", "")
                entities = tweet_dict.get("entities", {})
                tweet_text = tweet_dict.get("text", "")
                author_id = tweet_dict.get("author_id", "")
                id_str = tweet_dict.get("id_str", "")

                tweet_id = id_str
                tweet_via = via
                link_type = ""

                if tweet_id in seen_ids:
                    continue

                user_id = author_id
                user_name, screan_name = author.get("name"), author.get("screen_name")

                # tweet_url は screan_name と tweet_id から生成する
                tweet_url = f"https://twitter.com/{screan_name}/status/{tweet_id}"

                # created_at を解釈する
                # Like した時点の時間が取得できる？
                td_format = "%a %b %d %H:%M:%S +0000 %Y"
                dts_format = "%Y-%m-%d %H:%M:%S"
                jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
                dst = jst.strftime(dts_format)

                # 保存時間は現在時刻とする
                saved_created_at = datetime.now().strftime(dts_format)

                # expanded_url を収集する
                expanded_urls = self.fetcher._match_entities(entities).get("expanded_urls", [])

                # 外部リンクについて対象かどうか判定する
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
            result.reverse()
            return result

        expect = to_convert_ExternalLink(fetched_tweets, ls)
        self.assertEqual(expect, actual)

        actual = self.fetcher.to_convert_ExternalLink(
            [{"invalid_struct_dict": "invalid"}],
            ls
        )
        self.assertEqual([], actual)

        actual = self.fetcher.to_convert_ExternalLink(
            ["invalid_args"],
            ls
        )
        self.assertEqual([], actual)

        actual = self.fetcher.to_convert_ExternalLink(-1, ls)
        self.assertEqual([], actual)

        actual = self.fetcher.to_convert_ExternalLink(
            [{"invalid_struct_dict": "invalid"}],
            ls
        )
        self.assertEqual([], actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
