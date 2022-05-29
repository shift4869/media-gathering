# coding: utf-8
from dataclasses import dataclass

import requests
import requests.cookies


@dataclass(frozen=True)
class NijieCookie():
    _cookies: requests.cookies.RequestsCookieJar
    _headers: dict

    NIJIE_TOP_URL = "http://nijie.info/index.php"

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("_cookies is not requests.cookies.RequestsCookieJar.")
        if not isinstance(self._headers, dict):
            raise TypeError("_cookies is not requests.cookies.RequestsCookieJar.")

        if not (self._headers and self._cookies):
            return ValueError("NijieCookie _headers or _cookies is invalid.")

        # トップページをGETしてクッキーが有効かどうか調べる
        res = requests.get(self.NIJIE_TOP_URL, headers=self._headers, cookies=self._cookies)
        res.raise_for_status()

        # 返ってきたレスポンスがトップページのものかチェック
        # 不正なクッキーだと年齢確認画面に飛ばされる（titleとurlから判別可能）
        if not (res.status_code == 200 and res.url == self.NIJIE_TOP_URL and "ニジエ - nijie" in res.text):
            raise ValueError("NijieCookie is invalid.")
        return True
