# coding: utf-8
import json
import pprint
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path


class TwitterAPIEndpointName(Enum):
    # ツイート取得(userid)
    TIMELINE_TWEET = auto()

    # ツイート投稿
    POST_TWEET = auto()

    # ツイート削除(tweetid)
    DELETE_TWEET = auto()

    # ユーザー詳細取得
    USER_LOOKUP = auto()

    # ユーザー詳細取得(screen_name)
    USER_LOOKUP_BY_USERNAME = auto()

    # ツイート詳細取得
    TWEETS_LOOKUP = auto()

    # like取得(userid)
    LIKED_TWEET = auto()

    # 認証ユーザー詳細取得
    USER_LOOKUP_ME = auto()

    # レートリミット


@dataclass
class TwitterAPIEndpoint():
    # 設定ファイルパス
    SETTING_JSON_PATH = "./PictureGathering/v2/twitter_api_setting.json"

    # def __init__(self) -> None:
    #     with Path(self.SETTING_JSON_PATH).open("r") as fin:
    #         self.setting_dict = json.loads(fin.read())

    @classmethod
    def load(cls) -> None:
        with Path(cls.SETTING_JSON_PATH).open("r") as fin:
            cls.setting_dict = json.loads(fin.read())

    @classmethod
    def reload(cls) -> None:
        cls.load()

    @classmethod
    def get_setting_dict(cls) -> dict:
        if not hasattr(cls, "setting_dict"):
            cls.load()
            return cls.setting_dict
        else:
            return cls.setting_dict

    @classmethod
    def _get(cls, name: str) -> list[dict]:
        setting_dict: dict = cls.get_setting_dict()
        res = setting_dict.get(name)
        if not isinstance(res, list):
            res = [res]
        return res

    @classmethod
    def get_util(cls) -> dict:
        return cls._get("util")[0]

    @classmethod
    def get_endpoint_list(cls) -> list[dict]:
        return cls._get("endpoint")

    @classmethod
    def get_endpoint(cls, name: TwitterAPIEndpointName) -> dict:
        endpoint_list = cls.get_endpoint_list()
        res = [endpoint for endpoint in endpoint_list if endpoint.get("name", "") == name.name]
        if not res:
            return []
        return res[0]

    @classmethod
    def get_name(cls, estimated_endpoint_url: str, estimated_method: str) -> TwitterAPIEndpointName | None:
        for name in TwitterAPIEndpointName:
            template = cls.get_template(name)
            method = cls.get_method(name)
            if re.findall(f"^{template}$", estimated_endpoint_url) != []:
                if method == estimated_method:
                    return name
        return None

    @classmethod
    def get_method(cls, name: TwitterAPIEndpointName, *args) -> str:
        endpoint = cls.get_endpoint(name)
        return endpoint.get("method", "")

    @classmethod
    def make_url(cls, name: TwitterAPIEndpointName, *args) -> str:
        endpoint = cls.get_endpoint(name)

        path_params_num = endpoint.get("path_params_num")
        url = endpoint.get("url", "")

        if path_params_num > 0:
            if path_params_num != len(args):
                raise ValueError("*args error")
            url = url.format(*args)
        return url

    @classmethod
    def get_template(cls, name: TwitterAPIEndpointName) -> str:
        endpoint = cls.get_endpoint(name)
        return endpoint.get("template", "")

    @classmethod
    def validate(cls, estimated_endpoint_url: str, estimated_method: str = None) -> bool:
        for name in TwitterAPIEndpointName:
            template = cls.get_template(name)
            method = cls.get_method(name)
            if re.findall(f"^{template}$", estimated_endpoint_url) != []:
                if estimated_method is None or method == estimated_method:
                    return True
        return False

    @classmethod
    def raise_for_tweet_cap_limit_over(cls) -> None | ValueError:
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        now_count = cls.get_tweet_cap_now_count()
        max_count = int(setting_dict.get("util", {}).get("tweet_cap", {}).get("max", -1))

        if max_count < now_count:
            raise ValueError(f"tweet caps is over: caps = {max_count} < now_count = {now_count}.")

    @classmethod
    def set_tweet_cap_now_count(cls, count: int) -> int:
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        setting_dict["util"]["tweet_cap"]["estimated_now_count"] = int(count)

        cls.save(setting_dict)
        cls.reload()

        return cls.get_tweet_cap_now_count()

    @classmethod
    def get_tweet_cap_now_count(cls) -> int:
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        count = int(setting_dict.get("util", {}).get("tweet_cap", {}).get("estimated_now_count", -1))
        return count

    @classmethod
    def increase_tweet_cap(cls, amount: int) -> int:
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        now_count = cls.get_tweet_cap_now_count()
        setting_dict["util"]["tweet_cap"]["estimated_now_count"] = now_count + int(amount)

        cls.save(setting_dict)
        cls.reload()

        now_count = cls.get_tweet_cap_now_count()
        max_count = int(setting_dict.get("util", {}).get("tweet_cap", {}).get("max", -1))
        reset_date = int(setting_dict.get("util", {}).get("tweet_cap", {}).get("reset_date", -1))
        reset_date = "{:02}".format(reset_date)
        now_date = "{:02}".format((datetime.now() - timedelta(hours=9)).day)

        cls.raise_for_tweet_cap_limit_over()

        if now_date == reset_date:
            cls.set_tweet_cap_now_count(0)

        return cls.get_tweet_cap_now_count()

    @classmethod
    def save(cls, updated_setting_dict: dict) -> None:
        match updated_setting_dict:
            case {"util": _,
                  "endpoint": _}:
                with Path(cls.SETTING_JSON_PATH).open("w") as fout:
                    json.dump(updated_setting_dict, fout, indent=4)


if __name__ == "__main__":
    import configparser
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_token_keys_v2"]
    url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
    pprint.pprint(url)

    count = TwitterAPIEndpoint.get_tweet_cap_now_count()
    pprint.pprint(count)
    TwitterAPIEndpoint.raise_for_tweet_cap_limit_over()
    count = TwitterAPIEndpoint.increase_tweet_cap(1)
    pprint.pprint(count)
