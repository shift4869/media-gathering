# coding: utf-8
import pprint
import re
from dataclasses import dataclass
from http.cookiejar import Cookie
from pathlib import Path

import requests.cookies


@dataclass(frozen=True)
class Cookies():
    """Twitterセッションで使うクッキー
    """
    _cookies: requests.cookies.RequestsCookieJar

    # クッキーファイルパス
    TWITTER_COOKIE_PATH = "./config/twitter_cookie.ini"
    # クッキーに含まれるキー一覧
    COOKIE_KEYS_LIST = ["name", "value", "expires", "path", "domain", "httponly", "secure"]

    def __post_init__(self) -> None:
        if not self._cookies:
            raise ValueError("Cookies is None.")
        if not isinstance(self._cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("cookies is not RequestsCookieJar, invalid Cookies.")
        if not self._is_valid_cookies():
            raise ValueError("Cookies is invalid.")

    def _is_valid_cookies(self) -> bool:
        for cookie in self._cookies:
            line = self.cookie_to_string(cookie)
            if not self.validate_line(line):
                return False

            sc = {}
            elements = re.split("[,\n]", line)
            for element in elements:
                if not self.validate_element(element):
                    break

                element = element.strip().replace('"', "")  # 左右の空白とダブルクォートを除去
                if element == "":
                    break

                key, val = element.split("=", 1)  # =で分割
                sc[key] = val

            if set(list(sc.keys())) != set(self.COOKIE_KEYS_LIST):
                return False
        return True

    @property
    def cookies(self) -> requests.cookies.RequestsCookieJar:
        return self._cookies

    @classmethod
    def cookies_list_to_requests_cookie_jar(cls, cookies_list: list[dict]) -> requests.cookies.RequestsCookieJar:
        if cookies_list == []:
            raise ValueError("cookies_list is empty.")
        if not isinstance(cookies_list, list):
            raise TypeError("cookies_list is not list.")
        if not isinstance(cookies_list[0], dict):
            raise TypeError("cookies_list is not list[dict].")

        result_cookies = requests.cookies.RequestsCookieJar()
        for c in cookies_list:
            match c:
                case {
                    "name": name,
                    "value": value,
                    "expires": expires,
                    "path": path,
                    "domain": domain,
                    "secure": secure,
                    "httpOnly": httponly,
                }:
                    result_cookies.set(
                        name,
                        value,
                        expires=expires,
                        path=path,
                        domain=domain,
                        secure=secure,
                        rest={"HttpOnly": httponly}
                    )
                case _:
                    raise ValueError("cookie is not acceptable dict.")
        return result_cookies

    @classmethod
    def cookie_to_string(cls, cookie: Cookie) -> str:
        name = cookie.name
        value = cookie.value
        expires = cookie.expires
        path = cookie.path
        domain = cookie.domain
        httponly = cookie._rest["HttpOnly"]
        secure = cookie.secure
        return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}", httponly="{httponly}", secure="{secure}"'

    @classmethod
    def validate_line(cls, line) -> bool:
        pattern = 'name="(.*)", value="(.*)", expires=(.*), path="(.*)", domain="(.*)", httponly="(.*)", secure="(.*)"'
        if re.findall(pattern, line):
            return True
        return False

    @classmethod
    def validate_element(cls, element) -> bool:
        pattern = "^[\s]?(.*?)=(.*)$"
        if result_group := re.findall(pattern, element):
            if len(result_group) != 1:
                return False
            if len(result_group[0]) != 2:
                return False
            key, _ = result_group[0]
            return (key in cls.COOKIE_KEYS_LIST)
        return False

    @classmethod
    def load(cls) -> requests.cookies.RequestsCookieJar:
        # アクセスに使用するクッキーファイル置き場
        scp = Path(Cookies.TWITTER_COOKIE_PATH)
        if not scp.exists():
            # クッキーファイルが存在しない = 初回起動
            raise FileNotFoundError

        # クッキーを読み込む
        cookies = requests.cookies.RequestsCookieJar()
        with scp.open(mode="r") as fin:
            for line in fin:
                if not cls.validate_line(line):
                    break

                sc = {}
                elements = re.split("[,\n]", line)
                for element in elements:
                    if not cls.validate_element(element):
                        break

                    element = element.strip().replace('"', "")  # 左右の空白とダブルクォートを除去
                    if element == "":
                        break

                    key, val = element.split("=", 1)  # =で分割
                    sc[key] = val

                if set(list(sc.keys())) != set(cls.COOKIE_KEYS_LIST):
                    raise ValueError(f"{Cookies.TWITTER_COOKIE_PATH} : key format error.")

                cookies.set(
                    sc["name"],
                    sc["value"],
                    expires=sc["expires"],
                    path=sc["path"],
                    domain=sc["domain"],
                    secure=bool(sc["secure"]),
                    rest={"HttpOnly": bool(sc["httponly"])}
                )
        return cookies

    @classmethod
    def save(cls, cookies: requests.cookies.RequestsCookieJar | list[dict]) -> requests.cookies.RequestsCookieJar:
        if cookies and isinstance(cookies, list) and isinstance(cookies[0], dict):
            cookies = cls.cookies_list_to_requests_cookie_jar(cookies)

        if not isinstance(cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("cookies is not RequestsCookieJar | list[dict].")

        # クッキー情報をファイルに保存する
        scp = Path(Cookies.TWITTER_COOKIE_PATH)
        with scp.open(mode="w") as fout:
            for c in cookies:
                fout.write(cls.cookie_to_string(c) + "\n")

        return cookies

    @classmethod
    def create(cls) -> "Cookies":
        return cls(cls.load())


if __name__ == "__main__":
    try:
        cookies = Cookies.create()
        # Cookies.save(c.cookies)
        for cookie in cookies.cookies:
            pprint.pprint(cookie)
    except Exception as e:
        pprint.pprint(e)
