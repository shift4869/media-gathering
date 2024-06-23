import re
import sys
import unittest
import urllib.parse
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

from mock import patch
import orjson

from media_gathering.link_search.fetcher_base import FetcherBase
from media_gathering.link_search.link_searcher import LinkSearcher
from media_gathering.link_search.url import URL
from media_gathering.model import ExternalLink
from media_gathering.tac.parser_base import ParserBase
from media_gathering.tac.tweet_info import TweetInfo
from media_gathering.util import Result, find_values


class SampleFetcher(FetcherBase):
    def is_target_url(self, url: URL):
        estimated_url = url.non_query_url
        f1 = re.search(r"^https://www.pixiv.net/artworks/[0-9]+", estimated_url) is not None
        # f2 = re.search(r"^https://skeb.jp/\@(.+?)/works/([0-9]+)", estimated_url) is not None
        return f1

    def fetch(self):
        pass


class ConcreteParserBase(ParserBase):
    def _interpret(self, tweet: dict) -> list[dict]:
        result = []
        seen_id = []

        # (1)ツイートにメディアが添付されている場合
        if find_values(tweet, "media", False, ["legacy", "extended_entities"]):
            self._interpret_resister(tweet, result, seen_id)
        return result


class TestParserBase(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("media_gathering.link_search.link_searcher.logger"))
        self.cache_path = Path(__file__).parent / "cache/expect/content_cache_likes_test.json"
        self.fetched_tweets = orjson.loads(self.cache_path.read_bytes())

    def _make_instance(self) -> ConcreteParserBase:
        fetched_tweets = [orjson.loads(self.cache_path.read_bytes())]
        sample_fetcher = SampleFetcher()
        link_searcher = LinkSearcher()
        link_searcher.register(sample_fetcher)
        parser = ConcreteParserBase(fetched_tweets, link_searcher)
        return parser

    def test_init(self):
        fetched_tweets = [orjson.loads(self.cache_path.read_bytes())]
        sample_fetcher = SampleFetcher()
        link_searcher = LinkSearcher()
        link_searcher.register(sample_fetcher)
        parser = ConcreteParserBase(fetched_tweets, link_searcher)

        self.assertEqual(fetched_tweets, parser.fetched_tweets)
        self.assertEqual(link_searcher, parser.link_searcher)

        params_list = [
            ("invalid_fetched_tweets", link_searcher),
            ([{}, "invalid_fetched_tweets"], link_searcher),
            (fetched_tweets, "invalid_link_searcher"),
        ]
        for params in params_list:
            with self.assertRaises(TypeError):
                parser = ConcreteParserBase(params[0], params[1])

    def test_interpret_resister(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t.get("result", {})
            tweet_list.append(t1)

        def interpret_resister(tweet: dict, e_result: list[dict], e_seen_id: list[str]) -> Result:
            try:
                data = parser._match_data(tweet)
                if not data:
                    return Result.failed

                extended_entities = find_values(tweet, "extended_entities", False, ["legacy"])
                if not extended_entities:
                    entities = find_values(tweet, "entities", False, ["legacy"])
                    if not entities:
                        return Result.failed

                id_str = find_values(tweet, "id_str", True, ["legacy"])
                if id_str in e_seen_id:
                    return Result.failed

                e_result.append(tweet)
                e_seen_id.append(id_str)
                return Result.success
            except Exception:
                return Result.failed

        result, e_result = [], []
        seen_id, e_seen_id = [], []
        for _ in range(2):
            for tweet in tweet_list:
                actual = parser._interpret_resister(tweet, result, seen_id)
                expect = interpret_resister(tweet, e_result, e_seen_id)
                self.assertEqual(expect, actual)
        self.assertEqual(e_result, result)
        self.assertEqual(e_seen_id, seen_id)

        actual = parser._interpret_resister({"invalid_key": "invalid_value"}, [], [])
        self.assertEqual(Result.failed, actual)

        del tweet_list[1]["legacy"]["id_str"]
        actual = parser._interpret_resister(tweet_list[1], [], [])
        self.assertEqual(Result.failed, actual)

    def test_interpret(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t.get("result", {})
            tweet_list.append(t1)

        def interpret(tweet):
            result = []
            seen_id = []

            # (1)ツイートにメディアが添付されている場合
            if find_values(tweet, "media", False, ["legacy", "extended_entities"]):
                parser._interpret_resister(tweet, result, seen_id)
            return result

        for tweet in tweet_list:
            actual = parser._interpret(tweet)
            expect = interpret(tweet)
            self.assertEqual(expect, actual)

    def test_match_data(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t.get("result", {})
            tweet_list.append(t1)

        def match_data(data: dict) -> dict:
            match data:
                case {
                    "core": {"user_results": {"result": {"legacy": author}}},
                    "legacy": tweet,
                    "source": via_html,
                }:
                    via = re.findall(r"^<.+?>([^<]*?)<.+?>$", via_html)[0]
                    result = {
                        "author": author,
                        "tweet": tweet,
                        "via": via,
                    }
                    return result
            return {}

        for tweet in tweet_list:
            actual = parser._match_data(tweet)
            expect = match_data(tweet)
            self.assertEqual(expect, actual)

        tweet = {"invalid_key": "invalid_value"}
        actual = parser._match_data(tweet)
        expect = match_data(tweet)
        self.assertEqual(expect, actual)

        actual = parser._match_data(-1)
        expect = match_data(-1)
        self.assertEqual(expect, actual)

    def test_match_extended_entities_tweet(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t["result"]["legacy"]
            tweet_list.append(t1)

        def match_extended_entities_tweet(e_tweet: dict) -> dict:
            match e_tweet:
                case {
                    "created_at": created_at,
                    "extended_entities": extended_entities,
                    "full_text": full_text,
                    "id_str": id_str,
                    "user_id_str": author_id,
                }:
                    result = {
                        "author_id": author_id,
                        "created_at": created_at,
                        "extended_entities": extended_entities,
                        "id_str": id_str,
                        "text": full_text,
                    }
                    return result
            return {}

        for tweet in tweet_list:
            actual = parser._match_extended_entities_tweet(tweet)
            expect = match_extended_entities_tweet(tweet)
            self.assertEqual(expect, actual)

        tweet = {"invalid_key": "invalid_value"}
        actual = parser._match_extended_entities_tweet(tweet)
        expect = match_extended_entities_tweet(tweet)
        self.assertEqual(expect, actual)

        actual = parser._match_extended_entities_tweet(-1)
        expect = match_extended_entities_tweet(-1)
        self.assertEqual(expect, actual)

    def test_match_entities_tweet(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t["result"]["legacy"]
            tweet_list.append(t1)

        def match_entities_tweet(e_tweet: dict) -> dict:
            match e_tweet:
                case {
                    "created_at": created_at,
                    "entities": entities,
                    "full_text": full_text,
                    "id_str": id_str,
                    "user_id_str": author_id,
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

        for tweet in tweet_list:
            actual = parser._match_entities_tweet(tweet)
            expect = match_entities_tweet(tweet)
            self.assertEqual(expect, actual)

        tweet = {"invalid_key": "invalid_value"}
        actual = parser._match_entities_tweet(tweet)
        expect = match_entities_tweet(tweet)
        self.assertEqual(expect, actual)

        actual = parser._match_entities_tweet(-1)
        expect = match_entities_tweet(-1)
        self.assertEqual(expect, actual)

    def test_match_entities(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t["result"]["legacy"].get("entities", {})
            if not t1:
                continue
            tweet_list.append(t1)

        def match_entities(entities: dict) -> dict:
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

        for tweet in tweet_list:
            actual = parser._match_entities(tweet)
            expect = match_entities(tweet)
            self.assertEqual(expect, actual)

        tweet = {"invalid_key": "invalid_value"}
        actual = parser._match_entities(tweet)
        expect = match_entities(tweet)
        self.assertEqual(expect, actual)

        actual = parser._match_entities(-1)
        expect = match_entities(-1)
        self.assertEqual(expect, actual)

    def test_match_media(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = [t["result"]["legacy"] for t in tweet_results]
        media_list = find_values(tweet_list, "media", False, ["extended_entities"])
        flattend_media_list = list(chain.from_iterable(media_list))

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

        for media in flattend_media_list:
            actual = parser._match_media(media)
            expect = match_media(media)
            self.assertEqual(expect, actual)

        media = {"invalid_struct_dict": "invalid"}
        actual = parser._match_media(media)
        expect = match_media(media)
        self.assertEqual(expect, actual)

        actual = parser._match_media(-1)
        expect = match_media(-1)
        self.assertEqual(expect, actual)

    def test_parse_to_TweetInfo(self):
        parser = self._make_instance()

        def parse_to_TweetInfo():
            target_data_list: list[dict] = []
            tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
            for t in tweet_results:
                t1 = t.get("result", {})
                if t2 := parser._interpret(t1):
                    target_data_list.extend(t2)

            if not target_data_list:
                return []

            seen_ids: list[str] = []
            result: list[TweetInfo] = []
            for data in target_data_list:
                try:
                    data_dict = parser._match_data(data)
                    if not data_dict:
                        continue
                    author = data_dict["author"]
                    tweet = data_dict["tweet"]
                    via = data_dict["via"]
                    user_name, screan_name = author["name"], author["screen_name"]
                    tweet_via = via

                    tweet_dict = parser._match_extended_entities_tweet(tweet)
                    if not tweet_dict:
                        continue
                    author_id = tweet_dict["author_id"]
                    created_at = tweet_dict["created_at"]
                    extended_entities = tweet_dict["extended_entities"]
                    id_str = tweet_dict["id_str"]
                    tweet_text = tweet_dict["text"]
                    user_id = author_id

                    if id_str in seen_ids:
                        continue

                    tweet_url = extended_entities["media"][0]["expanded_url"]
                    td_format = "%a %b %d %H:%M:%S +0000 %Y"
                    dts_format = "%Y-%m-%d %H:%M:%S"
                    jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
                    dst = jst.strftime(dts_format)

                    media_list = extended_entities["media"]
                    for media in media_list:
                        media_dict = parser._match_media(media)
                        if not media_dict:
                            continue
                        media_filename = media_dict["media_filename"]
                        media_url = media_dict["media_url"]
                        media_thumbnail_url = media_dict["media_thumbnail_url"]

                        tweet = {
                            "media_filename": media_filename,
                            "media_url": media_url,
                            "media_thumbnail_url": media_thumbnail_url,
                            "tweet_id": id_str,
                            "tweet_url": tweet_url,
                            "created_at": dst,
                            "user_id": user_id,
                            "user_name": user_name,
                            "screan_name": screan_name,
                            "tweet_text": tweet_text,
                            "tweet_via": tweet_via,
                        }
                        result.append(TweetInfo.create(tweet))

                        if id_str not in seen_ids:
                            seen_ids.append(id_str)
                except KeyError:
                    continue
            result.reverse()
            return result

        actual = parser.parse_to_TweetInfo()
        expect = parse_to_TweetInfo()
        self.assertEqual(expect, actual)

        parser.fetched_tweets = [{"invalid_key": "invalid_value"}]
        actual = parser.parse_to_TweetInfo()
        expect = parse_to_TweetInfo()
        self.assertEqual(expect, actual)

        parser.fetched_tweets = ["invalid_args"]
        actual = parser.parse_to_TweetInfo()
        expect = parse_to_TweetInfo()
        self.assertEqual(expect, actual)

        parser.fetched_tweets = -1
        actual = parser.parse_to_TweetInfo()
        expect = parse_to_TweetInfo()
        self.assertEqual(expect, actual)

    def test_parse_to_ExternalLink(self):
        parser = self._make_instance()

        def parse_to_ExternalLink():
            target_data_list: list[dict] = []
            tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
            for t in tweet_results:
                t1 = t.get("result", {})
                if t2 := parser._interpret(t1):
                    target_data_list.extend(t2)

            if not target_data_list:
                # 辞書パースエラー or 1件もツイートが無かった
                # raise ValueError("no tweet included in fetched_tweets.")
                return []

            # target_data_list を入力として 外部リンク情報を収集
            # 外部リンク情報を含むかどうかを確認しつつ、対象ならば収集する
            seen_ids: list[str] = []
            result: list[ExternalLink] = []
            for data in target_data_list:
                try:
                    data_dict = parser._match_data(data)
                    if not data_dict:
                        continue
                    author = data_dict["author"]
                    tweet = data_dict["tweet"]
                    via = data_dict["via"]
                    user_name, screan_name = author["name"], author["screen_name"]
                    tweet_via = via

                    tweet_dict = parser._match_entities_tweet(tweet)
                    if not tweet_dict:
                        continue
                    author_id = tweet_dict["author_id"]
                    created_at = tweet_dict["created_at"]
                    entities = tweet_dict["entities"]
                    tweet_text = tweet_dict["text"]
                    id_str = tweet_dict["id_str"]
                    user_id = author_id
                    tweet_id = id_str

                    if tweet_id in seen_ids:
                        continue

                    # tweet_url は screan_name と tweet_id から生成する
                    tweet_url = f"https://twitter.com/{screan_name}/status/{tweet_id}"

                    # created_at を解釈する
                    td_format = "%a %b %d %H:%M:%S +0000 %Y"
                    dts_format = "%Y-%m-%d %H:%M:%S"
                    jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
                    dst = jst.strftime(dts_format)

                    # 保存時間は現在時刻とする
                    saved_created_at = datetime.now().strftime(dts_format)

                    # expanded_url を収集する
                    expanded_urls = parser._match_entities(entities).get("expanded_urls", [])
                    link_type = ""

                    # 外部リンクについて対象かどうか判定する
                    for expanded_url in expanded_urls:
                        if not parser.link_searcher.can_fetch(expanded_url):
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
                except KeyError:
                    continue
            result.reverse()
            return result

        actual = parser.parse_to_ExternalLink()
        expect = parse_to_ExternalLink()
        self.assertEqual(expect, actual)

        parser.fetched_tweets = [{"invalid_key": "invalid_value"}]
        actual = parser.parse_to_ExternalLink()
        expect = parse_to_ExternalLink()
        self.assertEqual(expect, actual)

        parser.fetched_tweets = ["invalid_args"]
        actual = parser.parse_to_ExternalLink()
        expect = parse_to_ExternalLink()
        self.assertEqual(expect, actual)

        parser.fetched_tweets = -1
        actual = parser.parse_to_ExternalLink()
        expect = parse_to_ExternalLink()
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
