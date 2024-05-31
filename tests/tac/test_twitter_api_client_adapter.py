"""TwitterAPIClientAdapter のテスト

TwitterAPIClientとのアダプタを担うクラスのテスト
"""

import sys
import unittest
from contextlib import ExitStack

from mock import MagicMock, call, patch

from media_gathering.tac.twitter_api_client_adapter import TwitterAPIClientAdapter


class TestTwitterAPIClientAdapter(unittest.TestCase):
    def setUp(self):
        self.ct0 = "dummy_ct0"
        self.auth_token = "dummy_auth_token"
        self.target_screen_name = "dummy_target_screen_name"
        self.target_id = 99999999  # dummy_target_id

    def tearDown(self):
        pass

    def test_TwitterAPIClientAdapter(self):
        twitter = TwitterAPIClientAdapter(self.ct0, self.auth_token, self.target_screen_name, self.target_id)
        self.assertEqual(self.ct0, twitter.ct0)
        self.assertEqual(self.auth_token, twitter.auth_token)
        self.assertEqual(self.target_screen_name, twitter.target_screen_name.name)
        self.assertEqual(self.target_id, twitter.target_id)

        with self.assertRaises(ValueError):
            twitter = TwitterAPIClientAdapter(-1, self.auth_token, self.target_screen_name, self.target_id)
        with self.assertRaises(ValueError):
            twitter = TwitterAPIClientAdapter(self.ct0, -1, self.target_screen_name, self.target_id)
        with self.assertRaises(ValueError):
            twitter = TwitterAPIClientAdapter(self.ct0, self.auth_token, -1, self.target_id)
        with self.assertRaises(ValueError):
            twitter = TwitterAPIClientAdapter(self.ct0, self.auth_token, self.target_screen_name, "invalid_target_id")

    def test_scraper(self):
        with ExitStack() as stack:
            mock_scraper = stack.enter_context(patch("media_gathering.tac.twitter_api_client_adapter.Scraper"))
            mock_scraper.return_value = "dummy_scraper"
            twitter = TwitterAPIClientAdapter(self.ct0, self.auth_token, self.target_screen_name, self.target_id)

            actual = twitter.scraper
            self.assertEqual("dummy_scraper", actual)
            mock_scraper.assert_called_once_with(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
            mock_scraper.reset_mock()

            actual = twitter.scraper
            self.assertEqual("dummy_scraper", actual)
            mock_scraper.assert_not_called()
            mock_scraper.reset_mock()

    def test_account(self):
        with ExitStack() as stack:
            mock_account = stack.enter_context(patch("media_gathering.tac.twitter_api_client_adapter.Account"))
            mock_account.return_value = "dummy_account"
            twitter = TwitterAPIClientAdapter(self.ct0, self.auth_token, self.target_screen_name, self.target_id)

            actual = twitter.account
            self.assertEqual("dummy_account", actual)
            mock_account.assert_called_once_with(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
            mock_account.reset_mock()

            actual = twitter.account
            self.assertEqual("dummy_account", actual)
            mock_account.assert_not_called()
            mock_account.reset_mock()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
