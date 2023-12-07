import shutil
import sys
import unittest
from contextlib import ExitStack
from itertools import repeat
from pathlib import Path

import orjson
from mock import MagicMock, patch

from media_gathering.tac.RetweetFetcher import RetweetFetcher


class TestRetweetFetcher(unittest.TestCase):
    def setUp(self):
        self.ct0 = "dummy_ct0"
        self.auth_token = "dummy_auth_token"
        self.target_screen_name = "dummy_target_screen_name"
        self.target_id = 99999999  # dummy_target_id

        self.CACHE_PATH = Path(__file__).parent / "cache/actual"

        with ExitStack() as stack:
            mock_twitter = stack.enter_context(patch("media_gathering.tac.fetcher_base.TwitterAPIClientAdapter"))
            self.mock_twitter = MagicMock()
            mock_twitter.side_effect = lambda ct0, auth_token, target_screen_name, target_id: self.mock_twitter

            self.fetcher = RetweetFetcher(self.ct0, self.auth_token, self.target_screen_name, self.target_id)
            self.fetcher.CACHE_PATH = self.CACHE_PATH

            mock_twitter.assert_called_once_with(self.ct0, self.auth_token, self.target_screen_name, self.target_id)

    def tearDown(self):
        if self.CACHE_PATH.exists():
            shutil.rmtree(self.CACHE_PATH)

    def _get_sample_json(self) -> list[dict]:
        cache_path = self.CACHE_PATH.parent / "expect"
        return orjson.loads((cache_path / "content_cache_timeline_test.json").read_bytes())

    def test_init(self):
        self.assertEqual(self.CACHE_PATH, self.fetcher.CACHE_PATH)
        self.assertEqual(self.mock_twitter, self.fetcher.twitter)

    def test_get_retweet_jsons(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch("media_gathering.tac.RetweetFetcher.logger.info"))
            r = MagicMock()

            DUP_NUM = 3
            sample_jsons = list(repeat(self._get_sample_json(), DUP_NUM))
            r.tweets_and_replies.side_effect = lambda user_ids, limit: sample_jsons
            self.fetcher.twitter.scraper = r
            self.fetcher.twitter.target_id = self.target_id

            limit = 400
            actual = self.fetcher.get_retweet_jsons(limit)
            self.assertEqual(sample_jsons, actual)

            expect = [f"timeline_tweets_{i:02}.json" for i in range(DUP_NUM)]
            actual_cache = self.fetcher.CACHE_PATH.glob("timeline_tweets*.json")
            actual = [p.name for p in actual_cache]
            expect.sort()
            actual.sort()
            self.assertEqual(expect, actual)

            r.tweets_and_replies.assert_called_once_with([int(self.target_id)], limit=limit)

    def test_fetch(self):
        with ExitStack() as stack:
            mock_get_retweet_jsons = stack.enter_context(patch("media_gathering.tac.RetweetFetcher.RetweetFetcher.get_retweet_jsons"))
            actual = self.fetcher.fetch()
            mock_get_retweet_jsons.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
