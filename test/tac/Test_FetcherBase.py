import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, patch

from media_gathering.tac.FetcherBase import FetcherBase
from media_gathering.tac.Username import Username


class ConcreteFetcher(FetcherBase):
    def __init__(self,
                 ct0: str,
                 auth_token: str,
                 target_screen_name: Username | str,
                 target_id: int) -> None:
        super().__init__(ct0, auth_token, target_screen_name, target_id)

    def fetch(self) -> list[dict]:
        return [{"status": "ok"}]


class TestFetcherBase(unittest.TestCase):
    def setUp(self):
        self.ct0 = "dummy_ct0"
        self.auth_token = "dummy_auth_token"
        self.target_screen_name = "dummy_target_screen_name"
        self.target_id = 99999999  # dummy_target_id

        self.CACHE_PATH = Path(__file__).parent / "cache/actual"

        with ExitStack() as stack:
            mock_twitter = stack.enter_context(patch("PictureGathering.tac.FetcherBase.TwitterAPIClientAdapter"))
            self.mock_twitter = MagicMock()
            mock_twitter.side_effect = lambda ct0, auth_token, target_screen_name, target_id: self.mock_twitter

            self.fetcher = ConcreteFetcher(self.ct0, self.auth_token, self.target_screen_name, self.target_id)
            self.fetcher.CACHE_PATH = self.CACHE_PATH

            mock_twitter.assert_called_once_with(self.ct0, self.auth_token, self.target_screen_name, self.target_id)

    def test_init(self):
        self.assertEqual(self.CACHE_PATH, self.fetcher.CACHE_PATH)
        self.assertEqual(self.mock_twitter, self.fetcher.twitter)

    def test_fetch(self):
        actual = self.fetcher.fetch()
        expect = [{"status": "ok"}]
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
