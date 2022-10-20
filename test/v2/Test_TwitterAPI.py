# coding: utf-8
import json
import sys
import time
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger
from mock import MagicMock, patch
from unittest.mock import call

import requests
from requests_oauthlib import OAuth1Session
from freezegun import freeze_time

from PictureGathering.v2.TwitterAPI import TwitterAPI
from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName

logger = getLogger("root")
logger.setLevel(WARNING)


class TestTwitterAPI(unittest.TestCase):
    def setUp(self):
        pass

    def _get_instance(self) -> TwitterAPI:
        dummy_api_key = "dummy_api_key"
        dummy_api_secret = "dummy_api_secret"
        dummy_access_token_key = "dummy_access_token_key"
        dummy_access_token_secret = "dummy_access_token_secret"
        with patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"):
            instance = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
        return instance

    def test_TwitterAPI_init(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"))

            dummy_api_key = "dummy_api_key"
            dummy_api_secret = "dummy_api_secret"
            dummy_access_token_key = "dummy_access_token_key"
            dummy_access_token_secret = "dummy_access_token_secret"

            actual = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            self.assertEqual(dummy_api_key, actual.api_key)
            self.assertEqual(dummy_api_secret, actual.api_secret)
            self.assertEqual(dummy_access_token_key, actual.access_token_key)
            self.assertEqual(dummy_access_token_secret, actual.access_token_secret)
            self.assertTrue(isinstance(actual.oauth, OAuth1Session))

            with self.assertRaises(TypeError):
                actual = TwitterAPI(None, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            with self.assertRaises(TypeError):
                actual = TwitterAPI(dummy_api_key, None, dummy_access_token_key, dummy_access_token_secret)
            with self.assertRaises(TypeError):
                actual = TwitterAPI(dummy_api_key, dummy_api_secret, None, dummy_access_token_secret)
            with self.assertRaises(TypeError):
                actual = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, None)

    def test_wait(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "debug"))
            mock_sys = stack.enter_context(patch("sys.stdout.flush"))
            mock_sleep = stack.enter_context(patch("time.sleep"))

            twitter = self._get_instance()
            wait_time = 5
            dt_unix = time.mktime(datetime.now().timetuple()) + wait_time
            actual = twitter._wait(dt_unix)
            mock_sys.assert_called()
            mock_sleep.assert_called()

    def test_wait_until_reset(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "debug"))
            mock_wait = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI._wait"))

            dt_format = "%Y-%m-%d %H:%M:%S"
            now_time_str = "2022-10-19 10:00:00"
            mock_freezegun = stack.enter_context(freeze_time(now_time_str))

            twitter = self._get_instance()

            wait_time = 5
            reset_dt_unix = time.mktime(datetime.strptime(now_time_str, dt_format).timetuple()) + wait_time
            dummy_response = MagicMock()
            dummy_response.headers = {
                "x-rate-limit-limit": 75,
                "x-rate-limit-remaining": 70,
                "x-rate-limit-reset": reset_dt_unix,
            }
            actual = twitter._wait_until_reset(dummy_response)
            mock_wait.assert_not_called()

            dummy_response.headers = {
                "x-rate-limit-limit": 75,
                "x-rate-limit-remaining": 0,
                "x-rate-limit-reset": reset_dt_unix,
            }
            actual = twitter._wait_until_reset(dummy_response)
            mock_wait.assert_called_once_with(reset_dt_unix + 3)

            dummy_response.headers = {}
            with self.assertRaises(requests.HTTPError):
                actual = twitter._wait_until_reset(dummy_response)

    def test_request(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "warning"))
            mock_oauth_get = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.OAuth1Session.get"))
            mock_oauth_post = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.OAuth1Session.post"))
            mock_oauth_delete = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.OAuth1Session.delete"))
            mock_wait_until_reset = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI._wait_until_reset"))
            mock_wait = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI._wait"))

            endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
            dummy_params = {"dummy_params": "dummy_params"}

            r = MagicMock()
            r.text = '{"dummy_response_text": "get_dummy_response_text"}'
            mock_oauth_get.side_effect = lambda endpoint_url, params: r
            mock_oauth_post.side_effect = lambda endpoint_url, json: r
            mock_oauth_delete.side_effect = lambda endpoint_url, params: r

            twitter = self._get_instance()
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "GET")
            self.assertEqual(expect, actual)
            mock_oauth_get.assert_called_once_with(endpoint_url, params=dummy_params)
            mock_oauth_get.reset_mock()

            endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.POST_TWEET)
            r.text = '{"dummy_response_text": "post_dummy_response_text"}'
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "POST")
            self.assertEqual(expect, actual)
            mock_oauth_post.assert_called_once_with(endpoint_url, json=dummy_params)
            mock_oauth_post.reset_mock()

            endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.DELETE_TWEET, "00000")
            r.text = '{"dummy_response_text": "delete_dummy_response_text"}'
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "DELETE")
            self.assertEqual(expect, actual)
            mock_oauth_delete.assert_called_once_with(endpoint_url, params=dummy_params)
            mock_oauth_delete.reset_mock()

            RETRY_NUM = 5
            endpoint_url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
            r.text = '{"dummy_response_text": "get_dummy_response_text"}'
            expect = json.loads(r.text)
            mock_oauth_get.side_effect = [None, None, r]
            actual = twitter.request(endpoint_url, dummy_params, "GET")
            self.assertEqual(expect, actual)
            called = mock_oauth_get.mock_calls
            self.assertEqual(4, len(called))
            self.assertEqual(call(endpoint_url, params=dummy_params), called[1])
            self.assertEqual(call(endpoint_url, params=dummy_params), called[2])
            self.assertEqual(call(endpoint_url, params=dummy_params), called[3])
            mock_oauth_get.reset_mock()

            RETRY_NUM = 5
            mock_oauth_get.side_effect = [None, None, None, None, None, r]
            with self.assertRaises(requests.HTTPError):
                actual = twitter.request(endpoint_url, dummy_params, "GET")
            mock_oauth_get.reset_mock()

            with self.assertRaises(ValueError):
                actual = twitter.request("INVALID_ENDPOINT", dummy_params, "GET")

    def test_get(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.request"))

            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = self._get_instance()
            expect = (dummy_endpoint_url, dummy_params, "GET")
            actual = twitter.get(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="GET")

    def test_post(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.request"))

            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = self._get_instance()
            expect = (dummy_endpoint_url, dummy_params, "POST")
            actual = twitter.post(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="POST")

    def test_delete(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.request"))

            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = self._get_instance()
            expect = (dummy_endpoint_url, dummy_params, "DELETE")
            actual = twitter.delete(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="DELETE")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
