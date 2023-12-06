from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class NijieCookie():
    """nijieのクッキー
    """
    _cookies: httpx.Cookies  # クッキー
    _headers: dict           # ヘッダー

    # nijieトップページ
    NIJIE_TOP_URL = "http://nijie.info/index.php"

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._cookies, httpx.Cookies):
            raise TypeError("_cookies is not httpx.Cookies.")
        if not isinstance(self._headers, dict):
            raise TypeError("_headers is not dict.")

        if not (self._headers and self._cookies):
            raise ValueError("NijieCookie _headers or _cookies is invalid.")

        # トップページをGETしてクッキーが有効かどうか調べる
        response = httpx.get(
            self.NIJIE_TOP_URL,
            headers=self._headers,
            cookies=self._cookies,
            follow_redirects=True
        )
        response.raise_for_status()

        # 返ってきたレスポンスがトップページのものかチェック
        # 不正なクッキーだと年齢確認画面に飛ばされる（titleとurlから判別可能）
        if not all([response.status_code == 200,
                    str(response.url) == self.NIJIE_TOP_URL,
                    "ニジエ - nijie" in response.text]):
            raise ValueError("NijieCookie is invalid.")
        return True


if __name__ == "__main__":
    import configparser
    from pathlib import Path

    from media_gathering.link_search.Nijie.NijieFetcher import NijieFetcher
    from media_gathering.link_search.Password import Password
    from media_gathering.link_search.Username import Username

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/link_search/")
    if config["nijie"].getboolean("is_nijie_trace"):
        fetcher = NijieFetcher(Username(config["nijie"]["email"]), Password(config["nijie"]["password"]), base_path)

        illust_id = 251267  # 一枚絵
        # illust_id = 251197  # 漫画
        # illust_id = 414793  # うごイラ一枚
        # illust_id = 409587  # うごイラ複数

        illust_url = f"https://nijie.info/view_popup.php?id={illust_id}"
        print(fetcher.cookies)
