import urllib.parse
from dataclasses import dataclass
from http.cookiejar import Cookie
from logging import INFO, getLogger
from pathlib import Path

import httpx
import orjson

from media_gathering.link_search.fetcher_base import FetcherBase
from media_gathering.link_search.nijie.nijie_cookie import NijieCookie
from media_gathering.link_search.nijie.nijie_downloader import NijieDownloader
from media_gathering.link_search.nijie.nijie_url import NijieURL
from media_gathering.link_search.password import Password
from media_gathering.link_search.url import URL
from media_gathering.link_search.username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class NijieFetcher(FetcherBase):
    """nijie作品を取得するクラス"""

    cookies: NijieCookie  # nijieで使用するクッキー
    base_path: Path  # 保存ディレクトリベースパス

    # 接続時に使用するヘッダー
    agent_browser = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    agent_webkit = "AppleWebKit/537.36 (KHTML, like Gecko)"
    agent_chrome = "Chrome/88.0.4324.190 Safari/537.36"
    HEADERS = {"User-Agent": " ".join([agent_browser, agent_webkit, agent_chrome])}
    # ログイン情報を保持するクッキーファイル置き場
    NIJIE_COOKIE_PATH = "./config/nijie_cookie.json"

    def __init__(self, username: Username, password: Password, base_path: Path):
        """初期化処理

        バリデーションとクッキー取得

        Args:
            username (Username): nijieログイン用ユーザーID
            password (Password):  nijieログイン用パスワード
            base_path (Path): 保存ディレクトリベースパス
        """
        super().__init__()

        if not isinstance(username, Username):
            raise TypeError("username is not Username.")
        if not isinstance(password, Password):
            raise TypeError("password is not Password.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path is not Path.")

        object.__setattr__(self, "cookies", self.login(username, password))
        object.__setattr__(self, "base_path", base_path)

    def login(self, username: Username, password: Password) -> NijieCookie:
        """nijieページにログインし、ログイン情報を保持したクッキーを返す

        Args:
            username (Username): nijieユーザーID(登録したemailアドレス)
            password (Password): nijieユーザーIDのパスワード

        Returns:
            cookies (NijieCookie): ログイン情報を保持したクッキー
        """
        if not isinstance(username, Username):
            raise TypeError("username is not Username.")
        if not isinstance(password, Password):
            raise TypeError("password is not Password.")

        ncp = Path(self.NIJIE_COOKIE_PATH)
        if ncp.is_file():
            # クッキーが既に存在している場合
            try:
                # クッキーを読み込む
                cookies_dict: list[dict] = orjson.loads(ncp.read_bytes())
                cookies = httpx.Cookies()
                for c in cookies_dict:
                    # TODO::expires を反映させたい場合は cookies.jar.set_cookie を参照
                    cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])

                # クッキーが有効かチェック
                res = NijieCookie(cookies, self.HEADERS)
                return res
            except Exception:
                pass

        # クッキーが存在していない場合、または有効なクッキーではなかった場合
        # 年齢確認で「はい」を選択したあとのURLにアクセス
        auth_url = "https://nijie.info/age_jump.php?url="
        response = httpx.get(auth_url, headers=self.HEADERS, follow_redirects=True)
        response.raise_for_status()

        # 認証用URLクエリを取得する
        response_url = str(response.url)
        qs = urllib.parse.urlparse(response_url).query
        qd = urllib.parse.parse_qs(qs)
        url_param = qd["url"][0]

        # ログイン時に必要な情報
        payload = {"email": username.name, "password": password.password, "save": "on", "ticket": "", "url": url_param}

        # ログインする
        login_url = "https://nijie.info/login_int.php"
        response = httpx.post(login_url, data=payload, follow_redirects=True)
        response.raise_for_status()

        # 以降はクッキーに認証情報が含まれているため、これを用いて各ページをGETする
        cookies: httpx.Cookies = response.cookies

        # クッキーが有効かチェック
        res = NijieCookie(cookies, self.HEADERS)

        # クッキー解析
        cookies_dict: list[dict] = []
        cookies_jar: dict[str, dict[str, dict[str, Cookie]]] = cookies.jar._cookies
        for domain, domain_dict in cookies_jar.items():
            for path, path_dict in domain_dict.items():
                for name, cookie in path_dict.items():
                    cookies_dict.append({
                        "name": name,
                        "value": cookie.value,
                        "expires": int(cookie.expires) if cookie.expires else None,
                        "path": path,
                        "domain": domain,
                    })

        # クッキー情報をファイルに保存する
        ncp.write_bytes(orjson.dumps(cookies_dict, option=orjson.OPT_INDENT_2))
        return res

    def is_target_url(self, url: URL) -> bool:
        """担当URLかどうか判定する

        FetcherBaseオーバーライド

        Args:
            url (URL): 処理対象url

        Returns:
            bool: 担当urlだった場合True, そうでない場合False
        """
        if not isinstance(url, URL):
            raise TypeError("url is not URL.")
        return NijieURL.is_valid(url.original_url)

    def fetch(self, url: str | URL) -> None:
        """担当処理：nijie作品を取得する

        FetcherBaseオーバーライド

        Args:
            url (URL): 処理対象url
        """
        if not isinstance(url, str | URL):
            raise TypeError("url is not str | URL.")
        novel_url = NijieURL.create(url)
        NijieDownloader(novel_url, self.base_path, self.cookies).download()


if __name__ == "__main__":
    import logging.config

    import orjson

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.json"
    config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())

    base_path = Path("./media_gathering/link_search/")
    if config["nijie"]["is_nijie_trace"]:
        fetcher = NijieFetcher(Username(config["nijie"]["email"]), Password(config["nijie"]["password"]), base_path)

        illust_id = 251267  # 一枚絵
        # illust_id = 251197  # 漫画
        # illust_id = 414793  # うごイラ一枚
        # illust_id = 409587  # うごイラ複数

        illust_url = f"https://nijie.info/view_popup.php?id={illust_id}"
        fetcher.fetch(illust_url)
