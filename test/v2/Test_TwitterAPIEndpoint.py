# coding: utf-8
import json
import re
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, patch
from pathlib import Path
from unittest.mock import call, mock_open

from freezegun import freeze_time

from PictureGathering.v2.TwitterAPIEndpoint import TwitterAPIEndpoint, TwitterAPIEndpointName

logger = getLogger(__name__)
logger.setLevel(WARNING)


class TestTwitterAPI(unittest.TestCase):
    def setUp(self):
        pass

    def _get_expect_setting_dict(self):
        expect = {}
        with Path(TwitterAPIEndpoint.SETTING_JSON_PATH).open("r") as fin:
            expect = json.loads(fin.read())
        return expect

    def test_TwitterAPIEndpointName(self):
        expect = [
            "TIMELINE_TWEET",
            "POST_TWEET",
            "DELETE_TWEET",
            "USER_LOOKUP",
            "USER_LOOKUP_BY_USERNAME",
            "TWEETS_LOOKUP",
            "LIKED_TWEET",
            "USER_LOOKUP_ME",
        ]
        actual = [name.name for name in TwitterAPIEndpointName]
        self.assertEqual(expect, actual)

    def test_TwitterAPIEndpoint(self):
        expect = "./PictureGathering/v2/twitter_api_setting.json"
        actual = TwitterAPIEndpoint.SETTING_JSON_PATH
        self.assertEqual(expect, actual)

    def test_is_json_util_struct_match(self):
        expect_dict = self._get_expect_setting_dict()
        util_dict = expect_dict.get("util", {})

        actual = TwitterAPIEndpoint._is_json_util_struct_match(util_dict)
        self.assertTrue(actual)

        util_dict["tweet_cap"]["estimated_now_count"] = 2000001
        actual = TwitterAPIEndpoint._is_json_util_struct_match(util_dict)
        self.assertFalse(actual)

        util_dict["tweet_cap"]["reset_date"] = 32
        actual = TwitterAPIEndpoint._is_json_util_struct_match(util_dict)
        self.assertFalse(actual)

        util_dict["tweet_cap"]["max_tweet_cap"] = 1234567
        actual = TwitterAPIEndpoint._is_json_util_struct_match(util_dict)
        self.assertFalse(actual)

        util_dict["tweet_cap"]["access_level"] = "invalid_access_level"
        actual = TwitterAPIEndpoint._is_json_util_struct_match(util_dict)
        self.assertFalse(actual)

        del util_dict["tweet_cap"]
        actual = TwitterAPIEndpoint._is_json_util_struct_match(util_dict)
        self.assertFalse(actual)

    def test_is_json_endpoint_struct_match(self):
        expect_dict = self._get_expect_setting_dict()
        endpoint_list = expect_dict.get("endpoint", [])

        for endpoint in endpoint_list:
            actual = TwitterAPIEndpoint._is_json_endpoint_struct_match(endpoint)
            self.assertTrue(actual)

        endpoint = endpoint_list[0]
        endpoint["url"] = -1
        actual = TwitterAPIEndpoint._is_json_endpoint_struct_match(endpoint)
        self.assertFalse(actual)

        endpoint["template"] = -1
        actual = TwitterAPIEndpoint._is_json_endpoint_struct_match(endpoint)
        self.assertFalse(actual)

        endpoint["path_params_num"] = "1"
        actual = TwitterAPIEndpoint._is_json_endpoint_struct_match(endpoint)
        self.assertFalse(actual)

        endpoint["method"] = -1
        actual = TwitterAPIEndpoint._is_json_endpoint_struct_match(endpoint)
        self.assertFalse(actual)

        endpoint["name"] = -1
        actual = TwitterAPIEndpoint._is_json_endpoint_struct_match(endpoint)
        self.assertFalse(actual)

        actual = TwitterAPIEndpoint._is_json_endpoint_struct_match({})
        self.assertFalse(actual)

    def test_get(self):
        expect_dict = self._get_expect_setting_dict()
        expect = [expect_dict.get("util", "")]
        actual = TwitterAPIEndpoint._get("util")
        self.assertEqual(expect, actual)

        expect = expect_dict.get("endpoint", "")
        actual = TwitterAPIEndpoint._get("endpoint")
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint._get(-1)

    def test_load(self):
        self.assertTrue(Path(TwitterAPIEndpoint.SETTING_JSON_PATH).is_file())

        expect = self._get_expect_setting_dict()

        TwitterAPIEndpoint.load()
        actual = TwitterAPIEndpoint.setting_dict

        self.assertEqual(expect, actual)

    def test_reload(self):
        with ExitStack() as stack:
            mock_load = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.load"))

            TwitterAPIEndpoint.reload()
            mock_load.assert_called_once()

    def test_get_setting_dict(self):
        with ExitStack() as stack:
            expect = self._get_expect_setting_dict()
            actual = TwitterAPIEndpoint.get_setting_dict()
            self.assertEqual(expect, actual)

            mock_load = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.load"))
            expect = self._get_expect_setting_dict()
            actual = TwitterAPIEndpoint.get_setting_dict()
            self.assertEqual(expect, actual)
            mock_load.assert_not_called()

    def test_get_util(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint._get"))

            actual = TwitterAPIEndpoint.get_util()
            calls = mock_get.mock_calls
            self.assertEqual(2, len(calls))
            self.assertEqual(call("util"), calls[0])
            self.assertEqual(call().__getitem__(0), calls[1])

    def test_get_endpoint_list(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint._get"))

            actual = TwitterAPIEndpoint.get_endpoint_list()
            mock_get.assert_called_once_with("endpoint")

    def test_get_endpoint(self):
        expect_dict = self._get_expect_setting_dict()
        endpoint_list = expect_dict.get("endpoint", [])
        for name in TwitterAPIEndpointName:
            expect = [endpoint for endpoint in endpoint_list if endpoint.get("name", "") == name.name][0]
            actual = TwitterAPIEndpoint.get_endpoint(name)
            self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_endpoint("invalid_name")

    def test_get_name(self):
        expect_tuples = [
            ("TIMELINE_TWEET", "GET"),
            ("POST_TWEET", "POST"),
            ("DELETE_TWEET", "DELETE"),
            ("USER_LOOKUP", "GET"),
            ("USER_LOOKUP_BY_USERNAME", "GET"),
            ("TWEETS_LOOKUP", "GET"),
            ("LIKED_TWEET", "GET"),
            ("USER_LOOKUP_ME", "GET"),
        ]
        dummy_id = "00000"
        for name, expect_tuple in zip(TwitterAPIEndpointName, expect_tuples):
            url = TwitterAPIEndpoint.make_url(name, dummy_id)
            expect = name
            actual = TwitterAPIEndpoint.get_name(url, expect_tuple[1])
            self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_name(-1, "GET")

        with self.assertRaises(ValueError):
            url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
            actual = TwitterAPIEndpoint.get_name(url, -1)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_name("invalid_url", "GET")

        with self.assertRaises(ValueError):
            url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
            actual = TwitterAPIEndpoint.get_name(url, "invalid_method")

    def test_get_method(self):
        expect_tuples = [
            ("TIMELINE_TWEET", "GET"),
            ("POST_TWEET", "POST"),
            ("DELETE_TWEET", "DELETE"),
            ("USER_LOOKUP", "GET"),
            ("USER_LOOKUP_BY_USERNAME", "GET"),
            ("TWEETS_LOOKUP", "GET"),
            ("LIKED_TWEET", "GET"),
            ("USER_LOOKUP_ME", "GET"),
        ]
        for name, expect_tuple in zip(TwitterAPIEndpointName, expect_tuples):
            expect = expect_tuple[1]
            actual = TwitterAPIEndpoint.get_method(name)
            self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_method(-1)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_method("invalid_method")

    def test_make_url(self):
        dummy_id = "00000"
        expect_dict = self._get_expect_setting_dict()
        endpoint_list = expect_dict.get("endpoint", [])

        def make_url(name: TwitterAPIEndpointName, *args) -> str:
            endpoint = [endpoint for endpoint in endpoint_list if endpoint.get("name", "") == name.name][0]
            path_params_num = int(endpoint.get("path_params_num", 0))
            url = endpoint.get("url", "")

            if path_params_num > 0:
                url = url.format(*args)
            return url

        for name in TwitterAPIEndpointName:
            expect = make_url(name, dummy_id)
            actual = TwitterAPIEndpoint.make_url(name, dummy_id)
            self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            name = TwitterAPIEndpointName.TIMELINE_TWEET
            actual = TwitterAPIEndpoint.make_url(name)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.make_url("invlid_name", dummy_id)

    def test_get_template(self):
        expect_dict = self._get_expect_setting_dict()
        endpoint_list = expect_dict.get("endpoint", [])

        for name in TwitterAPIEndpointName:
            endpoint = [endpoint for endpoint in endpoint_list if endpoint.get("name", "") == name.name][0]
            expect = endpoint.get("template", "")
            actual = TwitterAPIEndpoint.get_template(name)
            self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_template(-1)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.get_template("invalid_method")

    def test_validate(self):
        expect_tuples = [
            ("TIMELINE_TWEET", "GET"),
            ("POST_TWEET", "POST"),
            ("DELETE_TWEET", "DELETE"),
            ("USER_LOOKUP", "GET"),
            ("USER_LOOKUP_BY_USERNAME", "GET"),
            ("TWEETS_LOOKUP", "GET"),
            ("LIKED_TWEET", "GET"),
            ("USER_LOOKUP_ME", "GET"),
        ]
        dummy_id = "00000"
        expect_dict = self._get_expect_setting_dict()
        endpoint_list = expect_dict.get("endpoint", [])

        def validate(estimated_endpoint_url: str, estimated_method: str = None) -> bool:
            for name in TwitterAPIEndpointName:
                endpoint = [endpoint for endpoint in endpoint_list if endpoint.get("name", "") == name.name][0]
                template = endpoint.get("template", "")
                method = endpoint.get("method", "")
                if re.findall(f"^{template}$", estimated_endpoint_url) != []:
                    if estimated_method is None or method == estimated_method:
                        return True
            return False

        for name, expect_tuple in zip(TwitterAPIEndpointName, expect_tuples):
            url = TwitterAPIEndpoint.make_url(name, dummy_id)
            method = expect_tuple[1]
            expect = validate(url, method)
            actual = TwitterAPIEndpoint.validate(url, method)
            self.assertEqual(expect, actual)

        name = TwitterAPIEndpointName.USER_LOOKUP_ME
        url = TwitterAPIEndpoint.make_url(name)
        expect = False
        actual = TwitterAPIEndpoint.validate(url, "invalid_method")
        self.assertEqual(expect, actual)

        expect = False
        actual = TwitterAPIEndpoint.validate("invlid_url", "GET")
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            name = TwitterAPIEndpointName.USER_LOOKUP_ME
            url = TwitterAPIEndpoint.make_url(name)
            actual = TwitterAPIEndpoint.validate(url, -1)
            self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.validate(-1, "GET")
            self.assertEqual(expect, actual)

    def test_raise_for_tweet_cap_limit_over(self):
        TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["max"] = 2000000
        TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"] = 0
        actual = TwitterAPIEndpoint.raise_for_tweet_cap_limit_over()
        self.assertIsNone(actual)

        TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["max"] = 0
        TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"] = 100
        with self.assertRaises(ValueError):
            actual = TwitterAPIEndpoint.raise_for_tweet_cap_limit_over()

        TwitterAPIEndpoint.reload()

    def test_get_tweet_cap_now_count(self):
        expect_dict = self._get_expect_setting_dict()
        expect = int(expect_dict.get("util", {}).get("tweet_cap", {}).get("estimated_now_count", -100))
        actual = TwitterAPIEndpoint.get_tweet_cap_now_count()
        self.assertEqual(expect, actual)

    def test_set_tweet_cap_now_count(self):
        with ExitStack() as stack:
            mock_save = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.save"))
            mock_reload = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.reload"))

            SET_VALUE = 200
            expect = SET_VALUE
            TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"] = 100
            actual_res = TwitterAPIEndpoint.set_tweet_cap_now_count(SET_VALUE)
            actual = TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"]
            self.assertEqual(expect, actual_res)
            self.assertEqual(expect, actual)
            mock_save.assert_called_once()
            mock_reload.assert_called_once()

            with self.assertRaises(ValueError):
                actual = TwitterAPIEndpoint.set_tweet_cap_now_count("invalid_count")
        TwitterAPIEndpoint.reload()

    def test_increase_tweet_cap(self):
        with ExitStack() as stack:
            RESET_DAY = 9
            dt_format = "%Y-%m-%d %H:%M:%S"
            now_time_str = f"2022-10-{RESET_DAY:02} 10:00:00"
            mock_freezegun = stack.enter_context(freeze_time(now_time_str))
            mock_save = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.save"))
            mock_reload = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.reload"))
            mock_raise = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.raise_for_tweet_cap_limit_over"))
            mock_set = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.TwitterAPIEndpoint.set_tweet_cap_now_count"))

            INCREASE_AMOUNT = 50
            expect = 150
            TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["reset_date"] = RESET_DAY + 1
            TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"] = 100
            actual_res = TwitterAPIEndpoint.increase_tweet_cap(INCREASE_AMOUNT)
            actual = TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"]
            self.assertEqual(expect, actual_res)
            self.assertEqual(expect, actual)
            mock_save.assert_called_once()
            mock_reload.assert_called_once()
            mock_raise.assert_called_once()
            mock_set.assert_not_called()
            mock_save.reset_mock()
            mock_reload.reset_mock()
            mock_raise.reset_mock()
            mock_set.reset_mock()

            expect = 150
            TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["reset_date"] = RESET_DAY
            TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"] = 100
            actual_res = TwitterAPIEndpoint.increase_tweet_cap(INCREASE_AMOUNT)
            actual = TwitterAPIEndpoint.setting_dict["util"]["tweet_cap"]["estimated_now_count"]
            self.assertEqual(expect, actual_res)
            self.assertEqual(expect, actual)
            mock_save.assert_called_once()
            mock_reload.assert_called_once()
            mock_raise.assert_called_once()
            mock_set.assert_called_once()
            mock_save.reset_mock()
            mock_reload.reset_mock()
            mock_raise.reset_mock()
            mock_set.reset_mock()

            with self.assertRaises(ValueError):
                actual = TwitterAPIEndpoint.increase_tweet_cap("invalid_amount")
        TwitterAPIEndpoint.reload()

    def test_save(self):
        with ExitStack() as stack:
            expect_dict = self._get_expect_setting_dict()

            mock_dump = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.json.dump"))
            mock_json_file_open: MagicMock = stack.enter_context(patch("PictureGathering.v2.TwitterAPIEndpoint.Path.open", mock_open()))

            TwitterAPIEndpoint.save(expect_dict)
            mock_json_file_open.assert_called_once()
            mock_dump.assert_called_once()
            mock_json_file_open.reset_mock()
            mock_dump.reset_mock()

            del expect_dict["endpoint"][0]["method"]
            with self.assertRaises(ValueError):
                TwitterAPIEndpoint.save(expect_dict)

            expect_dict["endpoint"] = []
            with self.assertRaises(ValueError):
                TwitterAPIEndpoint.save(expect_dict)

            del expect_dict["endpoint"]
            with self.assertRaises(ValueError):
                TwitterAPIEndpoint.save(expect_dict)

            del expect_dict["util"]
            with self.assertRaises(ValueError):
                TwitterAPIEndpoint.save(expect_dict)

            with self.assertRaises(ValueError):
                TwitterAPIEndpoint.save(-1)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
