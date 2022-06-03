# coding: utf-8
from dataclasses import dataclass

import requests
import requests.cookies


@dataclass(frozen=True)
class NijieCookie():
    """nijieのクッキー
    """
    _cookies: requests.cookies.RequestsCookieJar  # クッキー
    _headers: dict                                # ヘッダー

    # nijieトップページ
    NIJIE_TOP_URL = "http://nijie.info/index.php"

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._cookies, requests.cookies.RequestsCookieJar):
            raise TypeError("_cookies is not requests.cookies.RequestsCookieJar.")
        if not isinstance(self._headers, dict):
            raise TypeError("_headers is not dict.")

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


if __name__ == "__main__":
    import configparser
    from pathlib import Path
    from PictureGathering.LinkSearch.Password import Password
    from PictureGathering.LinkSearch.Nijie.NijieFetcher import NijieFetcher
    from PictureGathering.LinkSearch.Username import Username

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["nijie"].getboolean("is_nijie_trace"):
        fetcher = NijieFetcher(Username(config["nijie"]["email"]), Password(config["nijie"]["password"]), base_path)

        illust_id = 251267  # 一枚絵
        # illust_id = 251197  # 漫画
        # illust_id = 414793  # うごイラ一枚
        # illust_id = 409587  # うごイラ複数

        illust_url = f"https://nijie.info/view_popup.php?id={illust_id}"
        print(fetcher.cookies)
