# coding: utf-8
import asyncio
import json
import re
import shutil
import sys
import unittest
import urllib.parse
from contextlib import ExitStack
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

from mock import AsyncMock, MagicMock, call, patch

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.Model import ExternalLink
from PictureGathering.noapi.NoAPIRetweetFetcher import NoAPIRetweetFetcher
from PictureGathering.noapi.Password import Password
from PictureGathering.noapi.TweetInfo import TweetInfo
from PictureGathering.noapi.TwitterSession import TwitterSession
from PictureGathering.noapi.Username import Username


class TestNoAPIRetweetFetcher(unittest.TestCase):
    def setUp(self):
        self.username: Username = Username("dummy_username")
        self.password: Password = Password("dummy_password")
        self.target_username: Username = Username("dummy_target_username")
        self.TWITTER_CACHE_PATH = Path(__file__).parent / "cache/actual"

        with ExitStack() as stack:
            self.mock_twitter_session = stack.enter_context(patch("PictureGathering.noapi.NoAPIRetweetFetcher.TwitterSession.create"))
            self.mock_twitter_session.side_effect = AsyncMock
            self.fetcher = NoAPIRetweetFetcher(self.username.name, self.password.password, self.target_username.name)
            self.fetcher.TWITTER_CACHE_PATH = self.TWITTER_CACHE_PATH

    def tearDown(self):
        if self.TWITTER_CACHE_PATH.exists():
            shutil.rmtree(self.TWITTER_CACHE_PATH)

    def _get_sample_json(self) -> list[dict]:
        TEST_CACHE_PATH = self.TWITTER_CACHE_PATH.parent / "expect"
        with (TEST_CACHE_PATH / "content_cache_timeline_test.txt").open("r", encoding="utf8") as fin:
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
        self.assertEqual(self.username, self.fetcher.username)
        self.assertEqual(self.password, self.fetcher.password)
        self.assertEqual(self.target_username, self.fetcher.target_username)

        self.mock_twitter_session.assert_called_with(username=self.username, password=self.password)
        # self.assertEqual(self.mock_twitter_session, self.fetcher.twitter_session)

    def test_response_listener(self):
        response_url = "https://test.com/UserTweetsAndReplies"
        content = {"content_cache": "content_cache"}
        r = MagicMock()
        r1 = AsyncMock()
        r1.side_effect = lambda: content
        r.url = response_url
        r.headers = {"content-type": "application/json"}
        r.json = r1
        self.fetcher.redirect_urls = []
        self.fetcher.content_list = []
        loop = asyncio.new_event_loop()
        actual = loop.run_until_complete(
            self.fetcher._response_listener(r)
        )
        self.assertEqual(1, len(self.fetcher.redirect_urls))
        self.assertEqual(response_url, self.fetcher.redirect_urls[0])
        self.assertEqual(1, len(self.fetcher.content_list))
        self.assertEqual(content, self.fetcher.content_list[0])

        expect = [f"content_cache{i}.txt" for i in range(1)]
        actual_cache = self.fetcher.TWITTER_CACHE_PATH.glob("content_cache*.txt")
        actual = [p.name for p in actual_cache]
        expect.sort()
        actual.sort()
        self.assertEqual(expect, actual)

    def test_get_retweet_jsons(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch("PictureGathering.noapi.NoAPIRetweetFetcher.logger.info"))
            mock_random = stack.enter_context(patch("PictureGathering.noapi.NoAPIRetweetFetcher.random.random"))
            mock_random.return_value = 0.5

            r = AsyncMock()
            r1 = AsyncMock()
            r2 = AsyncMock()
            self.count = 0

            def evaluate(function_script):
                count = self.count
                self.fetcher.redirect_urls.append(f"https://test.com/{count}")
                content = {"content_cache": f"sample_{count}"}
                n = len(self.fetcher.content_list)
                with Path(self.fetcher.TWITTER_CACHE_PATH / f"content_cache{n}.txt").open("w", encoding="utf8") as fout:
                    json.dump(content, fout)
                self.fetcher.content_list.append(content)
                self.count = count + 1
                return function_script
            r2.evaluate.side_effect = evaluate
            r1.html.page = r2
            r.RETWEET_URL_TEMPLATE = TwitterSession.RETWEET_URL_TEMPLATE
            r.get.side_effect = lambda url: r1
            self.fetcher.twitter_session = r
            self.fetcher.TWITTER_CACHE_PATH = self.TWITTER_CACHE_PATH
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(
                self.fetcher.get_retweet_jsons()
            )
            del self.count

            max_scroll = 40
            each_scroll_wait = 1.5
            expect = [{"content_cache": f"sample_{i}"} for i in range(max_scroll)]
            self.assertEqual(expect, actual)

            expect = [f"content_cache{i}.txt" for i in range(max_scroll)]
            actual_cache = self.fetcher.TWITTER_CACHE_PATH.glob("content_cache*.txt")
            actual = [p.name for p in actual_cache]
            expect.sort()
            actual.sort()
            self.assertEqual(expect, actual)

            expect = "redirect_urls.txt"
            actual_redirect_urls = self.fetcher.TWITTER_CACHE_PATH.glob("redirect_urls.txt")
            actual_redirect_urls = list(actual_redirect_urls)
            self.assertEqual(1, len(actual_redirect_urls))
            actual = actual_redirect_urls[0].name
            self.assertEqual(expect, actual)

            s_calls = self.fetcher.twitter_session.mock_calls
            url = TwitterSession.RETWEET_URL_TEMPLATE.format(self.fetcher.target_username.name)
            self.assertEqual(2, len(s_calls))
            self.assertEqual(call.prepare(), s_calls[0])
            self.assertEqual(call.get(url), s_calls[1])

            p_calls = r2.mock_calls
            self.assertEqual(max_scroll * 2 + 2, len(p_calls))
            self.assertEqual("on", p_calls[0][0])
            self.assertEqual("response", p_calls[0][1][0])
            self.assertEqual(True, callable(p_calls[0][1][1]))
            for p_call in p_calls[2::2]:
                self.assertAlmostEqual(
                    call.waitFor(each_scroll_wait * 1000),
                    p_call
                )
            self.assertAlmostEqual(call.waitFor(2000), p_calls[-1])

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
            [tweets[7].get("legacy", {})
                      .get("retweeted_status_result", {})
                      .get("result", {})],
            [tweets[8].get("quoted_status_result", {})
                      .get("result", {})],
            [tweets[9].get("legacy", {})
                      .get("retweeted_status_result", {})
                      .get("result", {})
                      .get("quoted_status_result", {})
                      .get("result", {})],
        ]
        self.assertEqual(expect, actual)

        with self.assertRaises(TypeError):
            self.fetcher.interpret_json(-1)

    def test_fetch(self):
        with ExitStack() as stack:
            mock_get_retweet_jsons = stack.enter_context(patch("PictureGathering.noapi.NoAPIRetweetFetcher.NoAPIRetweetFetcher.get_retweet_jsons"))
            actual = self.fetcher.fetch()
            mock_get_retweet_jsons.assert_called_once_with()

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
                # Retweet した時点の時間が取得できる？
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
