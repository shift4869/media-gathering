# coding: utf-8
import json
import pprint
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path


class TwitterAPIEndpointName(Enum):
    """エンドポイント名一覧
    
        指定のエンドポイントurlを取得したい場合は以下のように使用する
            url = TwitterAPIEndpoint.make_url(TwitterAPIEndpointName.USER_LOOKUP_ME)
        TwitterAPIEndpoint.SETTING_JSON_PATH で示されるjsonファイル内の
        endpoint[].name に対応する
    """
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

    # レートリミット(未実装)


@dataclass
class TwitterAPIEndpoint():
    """エンドポイントに関わる情報を管理するクラス

        TwitterAPIEndpoint.SETTING_JSON_PATH にあるjsonファイルを参照する
        インスタンスは作らず、クラスメソッドのみで機能を使用する
        self.setting_dict はシングルトン
    """
    # 設定ファイルパス
    SETTING_JSON_PATH = "./PictureGathering/v2/twitter_api_setting.json"

    @classmethod
    def _is_json_util_struct_match(cls, estimated_util_dict: dict) -> bool:
        """指定辞書の util 構造部分について判定する

        Args:
            estimated_util_dict (dict): util 構造をしていると思われる辞書

        Returns:
            bool: util 構造が正しいならばTrue, 不正ならばFalse
        """
        match estimated_util_dict:
            case {
                    "tweet_cap": {
                        "access_level": access_level,
                        "max": max_tweet_cap,
                        "reset_date": reset_date,
                        "estimated_now_count": estimated_now_count
                    }}:
                if not (isinstance(access_level, str) and access_level in ["Essential", "Elevated"]):
                    return False
                if not (isinstance(max_tweet_cap, int) and max_tweet_cap in [500000, 2000000]):
                    return False
                if not (isinstance(reset_date, int) and 1 <= reset_date and reset_date <= 31):
                    return False
                if not (isinstance(estimated_now_count, int) and 0 <= estimated_now_count and estimated_now_count <= max_tweet_cap):
                    return False
                return True
        return False

    @classmethod
    def _is_json_endpoint_struct_match(cls, estimated_endpoint_dict: dict) -> bool:
        """指定辞書の endpoint 構造部分について判定する

        Args:
            estimated_endpoint_dict (dict): endpoint 構造をしていると思われる辞書(単体)

        Returns:
            bool: endpoint 構造が正しいならばTrue, 不正ならばFalse
        """
        match estimated_endpoint_dict:
            case {"name": name,
                  "method": method,
                  "path_params_num": path_params_num,
                  "template": template,
                  "url": url}:
                if not isinstance(name, str):
                    return False
                if not isinstance(method, str):
                    return False
                if not isinstance(path_params_num, int):
                    return False
                if not isinstance(template, str):
                    return False
                if not isinstance(url, str):
                    return False
                return True
        return False

    @classmethod
    def _raise_for_json_struct_match(cls, estimated_setting_dict: dict) -> None:
        """指定辞書の構造が正しいか判定する

        Args:
            estimated_setting_dict (dict): 対象の辞書

        Raises:
            ValueError: 辞書構造が不正な場合
        """
        if not isinstance(estimated_setting_dict, dict):
            raise ValueError("setting_dict must be dict.")
        if "util" not in estimated_setting_dict:
            raise ValueError('invalid setting_dict, must have "util".')
        if "endpoint" not in estimated_setting_dict:
            raise ValueError('invalid setting_dict, must have "endpoint".')

        util = estimated_setting_dict.get("util", {})
        if not util:
            raise ValueError('invalid setting_dict, must have "util".')
        if not cls._is_json_util_struct_match(util):
            raise ValueError('invalid setting_dict, must have valid "util" struct.')

        endpoint_list = estimated_setting_dict.get("endpoint", [])
        if not endpoint_list:
            raise ValueError('invalid setting_dict, must have "endpoint".')
        valid_endpoint_struct = [cls._is_json_endpoint_struct_match(endpoint) for endpoint in endpoint_list]
        if not all(valid_endpoint_struct):
            raise ValueError('invalid setting_dict, must have valid "endpoint" struct.')

    @classmethod
    def _get(cls, key: str) -> list[dict]:
        """指定 key を持つ辞書の一部を返す

        Args:
            key (str): 探索対象のキー

        Returns:
            list[dict]: 見つかった辞書（単体でもリストとして返す）
        """
        if not isinstance(key, str):
            raise ValueError("key must be str.")
        setting_dict: dict = cls.get_setting_dict()
        res = setting_dict.get(key)
        if not isinstance(res, list):
            res = [res]
        return res

    @classmethod
    def load(cls) -> None:
        """jsonファイルをロードして cls.setting_dict を使用可能にする

            設定jsonファイルは cls.SETTING_JSON_PATH
            ロード後の cls.setting_dict の構造もチェックする
        """
        with Path(cls.SETTING_JSON_PATH).open("r") as fin:
            cls.setting_dict = json.loads(fin.read())
        cls._raise_for_json_struct_match(cls.setting_dict)

    @classmethod
    def reload(cls) -> None:
        """リロード

            load のエイリアス
        """
        cls.load()

    @classmethod
    def get_setting_dict(cls) -> dict:
        """cls.setting_dict を返す

            初回呼び出し時は load する（シングルトン）
            2回目以降は保持している cls.setting_dict をそのまま返す

        Returns:
            dict: cls.setting_dict
        """
        if not hasattr(cls, "setting_dict"):
            cls.load()
            return cls.setting_dict
        else:
            return cls.setting_dict

    @classmethod
    def get_util(cls) -> dict:
        """cls.setting_dict["util"] を返す

        Returns:
            dict: cls.setting_dict["util"]
        """
        return cls._get("util")[0]

    @classmethod
    def get_endpoint_list(cls) -> list[dict]:
        """cls.setting_dict["endpoint"] を返す

        Returns:
            list[dict]: cls.setting_dict["endpoint"]
        """
        return cls._get("endpoint")

    @classmethod
    def get_endpoint(cls, name: TwitterAPIEndpointName) -> dict:
        """指定 name を持つ cls.setting_dict["endpoint"] の要素を返す

        Args:
            name (TwitterAPIEndpointName): 探索対象の name

        Returns:
            dict: cls.setting_dict["endpoint"] の要素のうち、"name" が引数と一致する要素
                  見つからなかった場合は空辞書を返す
        """
        if not isinstance(name, TwitterAPIEndpointName):
            raise ValueError("name must be TwitterAPIEndpointName.")
        endpoint_list = cls.get_endpoint_list()
        res = [endpoint for endpoint in endpoint_list if endpoint.get("name", "") == name.name]
        if not res:
            return {}
        return res[0]

    @classmethod
    def get_name(cls, estimated_endpoint_url: str, estimated_method: str) -> TwitterAPIEndpointName:
        """指定 endpoint_url と method から TwitterAPIEndpointName を返す

            指定 endpoint_url が template に一致、かつ、methodが一致する TwitterAPIEndpointName を探索する
            同じ endpoint_url で、異なる method を持つものもあるため、両方ペアで指定が必要

        Args:
            estimated_endpoint_url (str): 探索対象の endpoint_url
            estimated_method (str): 探索対象の method

        Returns:
            TwitterAPIEndpointName: 指定の(endpoint_url, method)に紐づく TwitterAPIEndpointName
        """
        if not isinstance(estimated_endpoint_url, str):
            raise ValueError("estimated_endpoint_url must be str.")
        if not isinstance(estimated_method, str):
            raise ValueError("estimated_method must be str.")

        for name in TwitterAPIEndpointName:
            template = cls.get_template(name)
            method = cls.get_method(name)
            if re.findall(f"^{template}$", estimated_endpoint_url) != []:
                if method == estimated_method:
                    return name
        raise ValueError(f"{estimated_method} {estimated_endpoint_url} : is not Twitter API Endpoint or invalid method.")

    @classmethod
    def get_method(cls, name: TwitterAPIEndpointName) -> str:
        """指定 name からメソッド名を返す

        Args:
            name (TwitterAPIEndpointName): 探索対象の name

        Returns:
            str: 指定の name に紐づくメソッド名
        """
        if not isinstance(name, TwitterAPIEndpointName):
            raise ValueError("name must be TwitterAPIEndpointName.")
        endpoint = cls.get_endpoint(name)
        return endpoint.get("method", "")

    @classmethod
    def make_url(cls, name: TwitterAPIEndpointName, *args) -> str:
        """指定 name からエンドポイントURLを返す

        Args:
            name (TwitterAPIEndpointName): 探索対象の name

        Returns:
            str: 指定の name に紐づくエンドポイントURL
        """
        if not isinstance(name, TwitterAPIEndpointName):
            raise ValueError("name must be TwitterAPIEndpointName.")
        endpoint = cls.get_endpoint(name)

        path_params_num = int(endpoint.get("path_params_num", 0))
        url = endpoint.get("url", "")

        if path_params_num > 0:
            if path_params_num != len(args):
                raise ValueError(f"*args len must be {path_params_num}, len(args) = {len(args)}.")
            url = url.format(*args)
        return url

    @classmethod
    def get_template(cls, name: TwitterAPIEndpointName) -> str:
        """指定 name からURL判定用テンプレートを返す

        Args:
            name (TwitterAPIEndpointName): 探索対象の name

        Returns:
            str: 指定の name に紐づくURL判定用テンプレート
        """
        if not isinstance(name, TwitterAPIEndpointName):
            raise ValueError("name must be TwitterAPIEndpointName.")
        endpoint = cls.get_endpoint(name)
        return endpoint.get("template", "")

    @classmethod
    def validate(cls, estimated_endpoint_url: str, estimated_method: str = None) -> bool:
        """指定 endpoint_url と method が正しいペアかどうかを判定する

            指定 endpoint_url が template に一致、かつ、methodが一致する TwitterAPIEndpointName がどうかを探索する
            同じ endpoint_url で、異なる method を持つものもあるため、両方ペアで指定が必要

        Args:
            estimated_endpoint_url (str): 探索対象の endpoint_url
            estimated_method (str): 探索対象の method

        Returns:
            bool: 指定の(endpoint_url, method)が正しい場合True, そうでない場合False
        """
        if not isinstance(estimated_endpoint_url, str):
            raise ValueError("estimated_endpoint_url must be str.")
        if not isinstance(estimated_method, str):
            raise ValueError("estimated_method must be str.")
        for name in TwitterAPIEndpointName:
            template = cls.get_template(name)
            method = cls.get_method(name)
            if re.findall(f"^{template}$", estimated_endpoint_url) != []:
                if estimated_method is None or method == estimated_method:
                    return True
        return False

    @classmethod
    def raise_for_tweet_cap_limit_over(cls) -> None | ValueError:
        """util 内、現在の推定カウントがツイートキャップ上限を超えていないか調べる

        Raises:
            ValueError: 現在の推定カウントがツイートキャップ上限を超えている場合
        """
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        now_count = cls.get_tweet_cap_now_count()
        max_count = int(setting_dict.get("util", {}).get("tweet_cap", {}).get("max", -1))

        if max_count < now_count:
            raise ValueError(f"tweet caps is over: caps = {max_count} < now_count = {now_count}.")

    @classmethod
    def get_tweet_cap_now_count(cls) -> int:
        """現在の推定カウントを取得する

        Returns:
            int: 現在のツイートキャップ推定カウント数
        """
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        count = int(setting_dict.get("util", {}).get("tweet_cap", {}).get("estimated_now_count", -1))
        return count

    @classmethod
    def set_tweet_cap_now_count(cls, count: int) -> int:
        """現在の推定カウントを設定する

            util.tweet_cap.estimated_now_count の値を count に設定する
            主に月一の初期化用

        Args:
            count (int): 設定値

        Returns:
            int: 現在のツイートキャップ推定カウント数(=count)
        """
        if not isinstance(count, int):
            raise ValueError("count must be integer.")
        setting_dict = TwitterAPIEndpoint.get_setting_dict()
        setting_dict["util"]["tweet_cap"]["estimated_now_count"] = int(count)

        cls.save(setting_dict)
        cls.reload()

        return cls.get_tweet_cap_now_count()

    @classmethod
    def increase_tweet_cap(cls, amount: int) -> int:
        """現在の推定カウントを加算する

            util.tweet_cap.estimated_now_count の値に amount を加算する
            現在の日と util.tweet_cap.reset_date が一致しているならばツイートキャップ推定カウントを0に設定する

        Args:
            amount (int): 加算カウント量

        Raises:
            ValueError: 加算結果がツイートキャップ上限を超えた場合(raise_for_tweet_cap_limit_over)

        Returns:
            int: 現在のツイートキャップ推定カウント数(=count)
        """
        if not isinstance(amount, int):
            raise ValueError("amount must be integer.")
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
        """指定辞書の内容で新しいjsonファイルとして上書きする

        Args:
            updated_setting_dict (dict): 新しくjsonとして保存する辞書

        Raises:
            ValueError: updated_setting_dict の構造が不正な場合(_raise_for_json_struct_match)
        """
        cls._raise_for_json_struct_match(updated_setting_dict)
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
