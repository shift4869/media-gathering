# coding: utf-8
import json
import sys
import unittest
import warnings
from contextlib import ExitStack
from mock import MagicMock, patch
from unittest.mock import call

import requests
from requests_oauthlib import OAuth1Session

from PictureGathering.v2.TwitterAPI import TwitterAPI, TwitterAPIEndpoint


class TestTwitterAPI(unittest.TestCase):
    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)

    def test_TwitterAPIEndpoint(self):
        expect_endpoint_dict = {
            "TIMELINE_TWEET": ["https://api.twitter.com/2/users/{}/tweets", "GET"],
            "POST_TWEET": ["https://api.twitter.com/2/tweets", "POST"],
            "DELETE_TWEET": ["https://api.twitter.com/2/tweets/{}", "DELETE"],
            "USER_LOOKUP": ["https://api.twitter.com/2/users", "GET"],
            "USER_LOOKUP_BY_USERNAME": ["https://api.twitter.com/2/users/by/username/{}", "GET"],
            "TWEETS_LOOKUP": ["https://api.twitter.com/2/tweets", "GET"],
            "LIKED_TWEET": ["https://api.twitter.com/2/users/{}/liked_tweets", "GET"],
            "USER_ME": ["https://api.twitter.com/2/users/me", "GET"],
        }
        for actual_endpoint in TwitterAPIEndpoint:
            key = actual_endpoint.name
            expect_endpoint = expect_endpoint_dict.get(key, [])
            self.assertEqual(expect_endpoint, actual_endpoint.value)

    def test_validate_endpoint_url(self):
        for actual_endpoint in TwitterAPIEndpoint:
            endpoint_url = actual_endpoint.value[0] if "{}" not in actual_endpoint.value[0] else actual_endpoint.value[0].format("12345")
            method = actual_endpoint.value[1]
            actual = TwitterAPIEndpoint.validate_endpoint_url(endpoint_url, method)
            self.assertTrue(actual)

        endpoint_url = "invalid_endpoint_url"
        method = "GET"
        actual = TwitterAPIEndpoint.validate_endpoint_url(endpoint_url, method)
        self.assertFalse(actual)

        endpoint_url = TwitterAPIEndpoint.USER_ME.value[0]
        method = "incalid_method"
        actual = TwitterAPIEndpoint.validate_endpoint_url(endpoint_url, method)
        self.assertFalse(actual)

        endpoint_url = TwitterAPIEndpoint.USER_ME.value[0]
        method = "GET"
        actual = TwitterAPIEndpoint.validate_endpoint_url(-1, method)
        self.assertFalse(actual)
        actual = TwitterAPIEndpoint.validate_endpoint_url(endpoint_url, -1)
        self.assertFalse(actual)

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

            mock_get.side_effect = lambda url, params: {}
            with self.assertRaises(ValueError):
                actual = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)

    def test_request(self):
        with ExitStack() as stack:
            mock_oauth_get = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.OAuth1Session.get"))
            mock_oauth_post = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.OAuth1Session.post"))
            mock_oauth_delete = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.OAuth1Session.delete"))

            dummy_api_key = "dummy_api_key"
            dummy_api_secret = "dummy_api_secret"
            dummy_access_token_key = "dummy_access_token_key"
            dummy_access_token_secret = "dummy_access_token_secret"
            endpoint_url = TwitterAPIEndpoint.USER_ME.value[0]
            dummy_params = {"dummy_params": "dummy_params"}

            r = MagicMock()
            r.text = '{"dummy_response_text": "get_dummy_response_text"}'
            mock_oauth_get.side_effect = lambda endpoint_url, params: r
            mock_oauth_post.side_effect = lambda endpoint_url, json: r
            mock_oauth_delete.side_effect = lambda endpoint_url, params: r

            twitter = None
            with patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"):
                twitter = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "GET")
            self.assertEqual(expect, actual)
            mock_oauth_get.assert_called_once_with(endpoint_url, params=dummy_params)
            mock_oauth_get.reset_mock()

            endpoint_url = TwitterAPIEndpoint.POST_TWEET.value[0]
            r.text = '{"dummy_response_text": "post_dummy_response_text"}'
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "POST")
            self.assertEqual(expect, actual)
            mock_oauth_post.assert_called_once_with(endpoint_url, json=dummy_params)
            mock_oauth_post.reset_mock()

            endpoint_url = TwitterAPIEndpoint.DELETE_TWEET.value[0].format("00000")
            r.text = '{"dummy_response_text": "delete_dummy_response_text"}'
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "DELETE")
            self.assertEqual(expect, actual)
            mock_oauth_delete.assert_called_once_with(endpoint_url, params=dummy_params)
            mock_oauth_delete.reset_mock()

            RETRY_NUM = 5
            endpoint_url = TwitterAPIEndpoint.USER_ME.value[0]
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
                actual = twitter.request(endpoint_url, dummy_params, "INVALID_METHOD")

            with self.assertRaises(ValueError):
                actual = twitter.request("INVALID_ENDPOINT", dummy_params, "GET")

    def test_get(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.request"))

            dummy_api_key = "dummy_api_key"
            dummy_api_secret = "dummy_api_secret"
            dummy_access_token_key = "dummy_access_token_key"
            dummy_access_token_secret = "dummy_access_token_secret"
            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = None
            with patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"):
                twitter = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            expect = (dummy_endpoint_url, dummy_params, "GET")
            actual = twitter.get(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="GET")

    def test_post(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.request"))

            dummy_api_key = "dummy_api_key"
            dummy_api_secret = "dummy_api_secret"
            dummy_access_token_key = "dummy_access_token_key"
            dummy_access_token_secret = "dummy_access_token_secret"
            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = None
            with patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"):
                twitter = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            expect = (dummy_endpoint_url, dummy_params, "POST")
            actual = twitter.post(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="POST")

    def test_delete(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("PictureGathering.v2.TwitterAPI.TwitterAPI.request"))

            dummy_api_key = "dummy_api_key"
            dummy_api_secret = "dummy_api_secret"
            dummy_access_token_key = "dummy_access_token_key"
            dummy_access_token_secret = "dummy_access_token_secret"
            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = None
            with patch("PictureGathering.v2.TwitterAPI.TwitterAPI.get"):
                twitter = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            expect = (dummy_endpoint_url, dummy_params, "DELETE")
            actual = twitter.delete(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="DELETE")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")