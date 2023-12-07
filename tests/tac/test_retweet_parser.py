import sys
import unittest
from pathlib import Path

import orjson
from mock import MagicMock

from media_gathering.link_search.link_searcher import LinkSearcher
from media_gathering.tac.retweet_parser import RetweetParser
from media_gathering.util import find_values


class TestRetweetParser(unittest.TestCase):
    def setUp(self):
        self.cache_path = Path(__file__).parent / "cache/expect/content_cache_timeline_test.json"
        self.fetched_tweets = orjson.loads(self.cache_path.read_bytes())

    def _make_instance(self) -> RetweetParser:
        fetched_tweets = [orjson.loads(self.cache_path.read_bytes())]
        link_searcher = MagicMock(spec=LinkSearcher)
        parser = RetweetParser(fetched_tweets, link_searcher)
        return parser

    def test_init(self):
        fetched_tweets = [orjson.loads(self.cache_path.read_bytes())]
        link_searcher = MagicMock(spec=LinkSearcher)
        parser = RetweetParser(fetched_tweets, link_searcher)

        self.assertEqual(fetched_tweets, parser.fetched_tweets)
        self.assertEqual(link_searcher, parser.link_searcher)

        params_list = [
            ("invalid_fetched_tweets", link_searcher),
            ([{}, "invalid_fetched_tweets"], link_searcher),
            (fetched_tweets, "invalid_link_searcher"),
        ]
        for params in params_list:
            with self.assertRaises(TypeError):
                parser = RetweetParser(params[0], params[1])

    def test_interpret(self):
        parser = self._make_instance()
        tweet_results: list[dict] = find_values(parser.fetched_tweets, "tweet_results")
        tweet_list = []
        for t in tweet_results:
            t1 = t.get("result", {})
            tweet_list.append(t1)

        def interpret(tweet):
            if "tweet" in tweet:
                tweet = tweet.get("tweet")

            result = []
            seen_id = []

            # (1)ツイートにメディアが添付されている場合
            if find_values(tweet, "media", False, ["legacy", "extended_entities"]):
                parser._interpret_resister(tweet, result, seen_id)

            # (2)ツイートに外部リンクが含まれている場合
            if urls_dict := find_values(tweet, "urls", False, ["legacy", "entities"]):
                urls_dict = urls_dict[0]
                if isinstance(urls_dict, list):
                    url_flags = [url_dict.get("expanded_url", "") != "" for url_dict in urls_dict]
                    if any(url_flags):
                        parser._interpret_resister(tweet, result, seen_id)

            # (3)メディアが添付されているツイートがRTされている場合
            if retweeted_tweet := find_values(tweet, "retweeted_status_result", False, ["legacy"]):
                retweeted_tweet = retweeted_tweet[0].get("result", {})
                parser._interpret_resister(retweeted_tweet, result, seen_id)

            # (4)メディアが添付されているツイートが引用RTされている場合
            if quoted_tweet := find_values(tweet, "quoted_status_result", False, [""]):
                quoted_tweet = quoted_tweet[0].get("result", {})
                parser._interpret_resister(quoted_tweet, result, seen_id)

            # (5)メディアが添付されているツイートの引用RTがRTされている場合
            retweeted_tweet = find_values(tweet, "retweeted_status_result", False)
            quoted_tweet = find_values(tweet, "quoted_status_result", False)
            if retweeted_tweet and quoted_tweet:
                quoted_tweet = quoted_tweet[0].get("result", {})
                parser._interpret_resister(quoted_tweet, result, seen_id)

            return result

        for tweet in tweet_list:
            actual = parser._interpret(tweet)
            expect = interpret(tweet)
            self.assertEqual(expect, actual)

        different_hierarchy_tweet_list = [
            {"tweet": t} for t in tweet_list
        ]
        for tweet in different_hierarchy_tweet_list:
            actual = parser._interpret(tweet)
            expect = interpret(tweet)
            self.assertEqual(expect, actual)

        with self.assertRaises(TypeError):
            actual = parser._interpret("invalid_tweet")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
