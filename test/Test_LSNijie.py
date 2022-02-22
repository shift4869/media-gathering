# coding: utf-8
import configparser
import random
import re
import shutil
import sys
import unittest
import urllib.parse
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, PropertyMock, mock_open, patch
from pathlib import Path

from PictureGathering import LSNijie


logger = getLogger("root")
logger.setLevel(WARNING)


class TestLSNijie(unittest.TestCase):

    def setUp(self):
        """コンフィグファイルからパスワードを取得する
        """
        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.email = config["nijie"]["email"]
        self.password = config["nijie"]["password"]
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

        self.TEST_BASE_PATH = "./test/PG_Nijie"
        self.TBP = Path(self.TEST_BASE_PATH)

    def tearDown(self):
        """後始末：テスト用ディレクトリを削除する
        """
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if self.TBP.is_dir():
            shutil.rmtree(self.TBP)

    def __GetIllustData(self, illust_id: int) -> tuple[list[str], str, int, str]:
        """テスト用のイラスト情報を作成する

        Args:
            illust_id (int): イラストID (0 < illust_id < 99999999)

        Returns:
            イラストIDで示される以下のイラスト情報
            urls (list[str]): 画像直リンクURLのリスト
            author_name (str): 作者名
            author_id (int): 作者ID
            illust_name (str): イラスト名
        """
        urls = {
            "251267": ["http://pic.nijie.net/02/nijie/18/30/21030/illust/0_0_aadcf2ddf1b24ec1_27436f.jpg"],
            "251197": ["http://pic.nijie.net/04/nijie/18/30/21030/illust/0_0_f3a05ba40da77873_1e5108.jpg",
                       "http://pic.nijie.net/02/nijie/18/30/21030/illust/251197_0_61e4cc9ff488f539_ff500b.jpg",
                       "http://pic.nijie.net/02/nijie/18/30/21030/illust/251197_1_d15b069661da1e90_99b04d.jpg",
                       "http://pic.nijie.net/02/nijie/18/30/21030/illust/251197_2_922a9f211aeda3ad_c6dd7d.jpg",
                       "http://pic.nijie.net/05/nijie/18/30/21030/illust/251197_3_a415cdb83be3cbb2_b95ac5.jpg",
                       "http://pic.nijie.net/02/nijie/18/30/21030/illust/251197_4_b67e46da22829b5f_8cd1a6.jpg",
                       "http://pic.nijie.net/02/nijie/18/30/21030/illust/251197_5_604330bb9efe6c4a_5b5153.jpg",
                       "http://pic.nijie.net/01/nijie/18/30/21030/illust/251197_6_c08214f63c465e95_3770c9.jpg",
                       "http://pic.nijie.net/04/nijie/18/30/21030/illust/251197_7_12c18a1ab3035fdf_8fdf81.jpg",
                       "http://pic.nijie.net/06/nijie/18/30/21030/illust/251197_8_4e959a4eaf40e12f_36a31b.jpg"],
            "414793": ["http://pic.nijie.net/02/nijie/21/12/4112/illust/0_0_7b961718be635818_8749ce.mp4"],
            "409587": ["http://pic.nijie.net/03/nijie/21/90/317190/illust/0_0_41ceff3011c776b5_110325.gif",
                       "http://pic.nijie.net/03/nijie/21/90/317190/illust/409587_1_216c24162ce6f7ba_618464.gif",
                       "http://pic.nijie.net/08/nijie/21/90/317190/illust/409587_2_b069a13911b8e8e6_e02a06.gif",
                       "http://pic.nijie.net/04/nijie/21/90/317190/illust/409587_0_cc566cefc4610854_95eb20.mp4",
                       "http://pic.nijie.net/05/nijie/21/90/317190/illust/409587_3_bf531ab4782e9563_6d8309.gif",
                       "http://pic.nijie.net/03/nijie/21/90/317190/illust/409587_4_4ada8109042eb838_7a3e61.gif",
                       "http://pic.nijie.net/06/nijie/21/90/317190/illust/409587_5_dc7f138c8c76338b_9f97cf.gif"]
        }
        cols = ["illust_id", "urls", "author_name", "author_id", "illust_name"]
        data = {
            "251267": [urls["251267"], "author_name_1", 21030, "一枚絵"],
            "251197": [urls["251197"], "author_name_1", 21030, "漫画"],
            "414793": [urls["414793"], "author_name_2", 4112, "うごイラ一枚"],
            "409587": [urls["409587"], "author_name_3", 317190, "うごイラ複数"]
        }
        res = data.get(str(illust_id), [[], "", -1, ""])
        return res

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        """nijieページへのログイン機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.LSNijie.LSNijie.Login" にpatchする

        Returns:
            MagicMock: ログイン機能のside_effectを持つモック
        """
        def LoginSideeffect(email, password):
            if self.email == email and self.password == password:
                cookies = "valid cookies"
                return (cookies, True)
            else:
                return (None, False)

        mock.side_effect = LoginSideeffect
        return mock

    def test_LSNijie(self):
        """nijieページ取得初期状態チェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)

            # 正常系
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)
            expect_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

            self.assertEqual(expect_headers, lsn_cont.headers)
            self.assertIsNotNone(lsn_cont.cookies)
            self.assertTrue(lsn_cont.auth_success)

            # 異常系
            with self.assertRaises(SystemExit):
                lsn_cont = LSNijie.LSNijie("invalid email", "invalid password", self.TEST_BASE_PATH)

    def test_Login(self):
        """nijieページスクレイピングのインスタンス生成とログインをチェック
        """

        with ExitStack() as stack:
            r = "{:0>8}".format(random.randint(0, 99999999))
            c = 'name="name", value="{}:{}", expires="expires", path={}, domain="domain"\n'.format(self.email, self.password, r)

            # open()をモックに置き換える
            mockfout = mock_open(read_data=c)
            mockfp = stack.enter_context(patch("pathlib.Path.open", mockfout))

            # モック置き換え
            mocknsreqget = stack.enter_context(patch("PictureGathering.LSNijie.requests.get"))
            mocknsreqpost = stack.enter_context(patch("PictureGathering.LSNijie.requests.post"))
            mocknsreqcj = stack.enter_context(patch("PictureGathering.LSNijie.requests.cookies.RequestsCookieJar"))
            mocknsisvalidcookies = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.IsValidCookies"))

            # requests.getで取得する内容のモックを返す
            def ReturnGet(url, headers):
                response = MagicMock()
                type(response).url = "test_url.html?url={}".format(r)

                def IsValid(s):
                    # 年齢確認で「はい」を選択したあとのURLか
                    return (url == "https://nijie.info/age_jump.php?url=")

                type(response).raise_for_status = IsValid

                return response

            # requests.postで取得する内容のモックを返す
            def ReturnPost(url, data):
                response = MagicMock()

                dict_cookies = MagicMock()
                type(dict_cookies).name = "name"
                type(dict_cookies).value = data["email"] + ":" + data["password"]
                type(dict_cookies).expires = "expires"
                type(dict_cookies).path = data["url"]
                type(dict_cookies).domain = "domain"

                type(response).cookies = [dict_cookies]

                def IsValid(s):
                    # ログインページのURLか
                    f_url = (url == "https://nijie.info/login_int.php")
                    # ログイン情報は正しいか
                    f_outh = (data["email"] == self.email) and (data["password"] == self.password)
                    return f_url and f_outh

                type(response).raise_for_status = IsValid

                return response

            actual_read_cookies = {}

            # requests.cookies.RequestsCookieJar()で取得する内容のモックを返す
            def ReturnCookieJar():
                response = MagicMock()

                def ReturnSet(s, name, value, expires="", path="", domain=""):
                    actual_read_cookies["name"] = name
                    actual_read_cookies["value"] = value
                    actual_read_cookies["expires"] = expires
                    actual_read_cookies["path"] = path
                    actual_read_cookies["domain"] = domain
                    return actual_read_cookies

                type(response).set = ReturnSet

                return response

            mocknsreqget.side_effect = ReturnGet
            mocknsreqpost.side_effect = ReturnPost
            mocknsreqcj.side_effect = ReturnCookieJar
            mocknsisvalidcookies.return_value = True

            # クッキーファイルが存在する場合、一時的にリネームする
            NIJIE_COOKIE_PATH = "./config/nijie_cookie.ini"
            nc_path = Path(NIJIE_COOKIE_PATH)
            tmp_path = nc_path.parent / "tmp.ini"
            if nc_path.is_file():
                nc_path.rename(tmp_path)

            # クッキーファイルが存在しない場合のテスト
            expect_cookies = {
                "name": "name",
                "value": self.email + ":" + self.password,
                "expires": "expires",
                "path": r,
                "domain": "domain",
            }
            # インスタンス生成時にLoginが呼ばれる
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)
            self.assertEqual(1, len(lsn_cont.cookies))
            res_cookies = lsn_cont.cookies[0]
            actual_cookies = {
                "name": res_cookies.name,
                "value": res_cookies.value,
                "expires": res_cookies.expires,
                "path": res_cookies.path,
                "domain": res_cookies.domain,
            }
            self.assertEqual(expect_cookies, actual_cookies)
            self.assertTrue(lsn_cont.auth_success)
            self.assertEqual(1, mocknsreqget.call_count)
            self.assertEqual(1, mocknsreqpost.call_count)
            self.assertEqual(1, mocknsreqcj.call_count)
            self.assertEqual(1, mocknsisvalidcookies.call_count)
            mocknsreqget.reset_mock()
            mocknsreqpost.reset_mock()
            mocknsreqcj.reset_mock()
            mocknsisvalidcookies.reset_mock()

            # 一時的にリネームしていた場合は復元する
            # そうでない場合はダミーのファイルを作っておく
            if tmp_path.is_file():
                tmp_path.rename(nc_path)
            else:
                nc_path.touch()

            # クッキーファイルが存在する場合のテスト
            # インスタンス生成時にLoginが呼ばれる
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)
            self.assertEqual(expect_cookies, actual_read_cookies)
            self.assertTrue(lsn_cont.auth_success)
            self.assertEqual(0, mocknsreqget.call_count)
            self.assertEqual(0, mocknsreqpost.call_count)
            self.assertEqual(1, mocknsreqcj.call_count)
            self.assertEqual(1, mocknsisvalidcookies.call_count)
            mocknsreqget.reset_mock()
            mocknsreqpost.reset_mock()
            mocknsreqcj.reset_mock()
            mocknsisvalidcookies.reset_mock()

            # ダミーファイルがある場合は削除しておく
            if not tmp_path.is_file() and nc_path.stat().st_size == 0:
                nc_path.unlink()

    def test_IsValidCookies(self):
        """クッキーが正しいかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)

            mocknsreqget = stack.enter_context(patch("PictureGathering.LSNijie.requests.get"))

            # requests.getで取得する内容のモックを返す
            def ReturnGet(url, headers, cookies):
                top_url = "http://nijie.info/index.php"
                response = MagicMock()

                if url == top_url and headers == self.headers and cookies == "valid cookies":
                    type(response).status_code = 200
                    type(response).url = url
                    type(response).text = "ニジエ - nijie"
                else:
                    type(response).status_code = 401
                    type(response).url = "invalid_url.php"
                    type(response).text = "invalid text"

                type(response).raise_for_status = lambda s: True

                return response

            mocknsreqget.side_effect = ReturnGet

            # 正常系
            res = lsn_cont.IsValidCookies(lsn_cont.headers, lsn_cont.cookies)
            self.assertTrue(res)

            # 異常系
            res = lsn_cont.IsValidCookies(None, None)
            self.assertFalse(res)
            res = lsn_cont.IsValidCookies(lsn_cont.headers, "invalid cookies")
            self.assertFalse(res)

    def test_IsTargetUrl(self):
        """URLがnijieのURLかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            # 作品ページURL
            url_s = "https://nijie.info/view.php?id=251267"
            self.assertEqual(True, lsn_cont.IsTargetUrl(url_s))

            # 作品詳細ページURL
            url_s = "https://nijie.info/view_popup.php?id=251267"
            self.assertEqual(True, lsn_cont.IsTargetUrl(url_s))

            # 異常系
            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            self.assertEqual(False, lsn_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(pixiv)
            url_s = "https://www.pixiv.net/artworks/24010650"
            self.assertEqual(False, lsn_cont.IsTargetUrl(url_s))

            # httpsでなくhttp
            url_s = "http://nijie.info/view_popup.php?id=251267"
            self.assertEqual(False, lsn_cont.IsTargetUrl(url_s))

            # nijieの別ページ
            url_s = "https://nijie.info/user_like_illust_view.php?id=21030"
            self.assertEqual(False, lsn_cont.IsTargetUrl(url_s))

            # プリフィックスエラー
            url_s = "ftp://nijie.info/view.php?id=251267"
            self.assertEqual(False, lsn_cont.IsTargetUrl(url_s))

            # サフィックスエラー
            url_s = "http://nijie.info/view.php?id=251267&rank=1"
            self.assertEqual(False, lsn_cont.IsTargetUrl(url_s))

    def test_GetIllustId(self):
        """nijie作品ページURLからイラストIDを取得する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            r = "{:0>6}".format(random.randint(0, 999999))
            # 作品ページURL
            url_s = "https://nijie.info/view.php?id={}".format(r)
            expect = int(r)
            actual = lsn_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

            # 作品詳細ページURL
            url_s = "https://nijie.info/view_popup.php?id={}".format(r)
            expect = int(r)
            actual = lsn_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "https://nijie.info/view.php?id={}&rank=1".format(r)
            expect = -1
            actual = lsn_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
        """
        with ExitStack() as stack:
            # モック置き換え
            mocknsreqget = stack.enter_context(patch("PictureGathering.LSNijie.requests.get"))
            mocknsbs = stack.enter_context(patch("PictureGathering.LSNijie.BeautifulSoup"))
            mocknsdpa = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.DetailPageAnalysis"))
            mocknsmsdp = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.MakeSaveDirectoryPath"))

            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)

            # requests.getで取得する内容のモックを返す
            def ReturnGet(url, headers, cookies):
                response = MagicMock()

                # メディアDL時
                pattern = r"^http://pic.nijie.net/[^$]*$"
                regex = re.compile(pattern)
                f1 = not (regex.findall(url) == [])

                # 作品詳細ページをGET時
                pattern = r"^http://nijie.info/view_popup.php\?id=[0-9]*$"
                regex = re.compile(pattern)
                f2 = not (regex.findall(url) == [])

                if f1 and headers == self.headers and cookies == "valid cookies":
                    # メディアDLを模倣
                    # contentにバイナリデータを設定
                    type(response).content = str(url).encode("utf-8")
                    type(response).status_code = 200
                    type(response).url = url
                    type(response).text = url
                elif f2 and headers == self.headers and cookies == "valid cookies":
                    # 作品詳細ページをGET時
                    type(response).status_code = 200
                    type(response).url = url
                    type(response).text = "ニジエ - nijie ," + url  # イラストID伝達用
                else:
                    # エラー
                    type(response).status_code = 401
                    type(response).url = "invalid_url.php"
                    type(response).text = "invalid text"

                type(response).raise_for_status = lambda s: True

                return response

            # BeautifulSoupのモック
            def ReturnBeautifulSoup(markup, features):
                # ここでは実際に解析はしない（test_DetailPageAnalysisが担当する）
                # 識別に必要なイラストIDのみ伝達する
                url = str(markup).split(",")[1]
                qs = urllib.parse.urlparse(url).query
                qd = urllib.parse.parse_qs(qs)
                illust_id = int(qd["id"][0])

                return illust_id

            # DetailPageAnalysisのモック
            def ReturnDetailPageAnalysis(soup):
                # ここでは実際に解析はしない（test_DetailPageAnalysisが担当する）
                # 伝達されたイラストIDを識別子として情報を返す
                illust_id = str(soup)
                return self.__GetIllustData(int(illust_id))

            # MakeSaveDirectoryPathのモック
            def ReturnMakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path):
                # 既存のディレクトリの存在は調べずに単純に結合して返す
                sd_path = "./{}({})/{}({})/".format(author_name, author_id, illust_name, illust_id)
                save_directory_path = Path(base_path) / sd_path
                return str(save_directory_path)

            mocknsreqget.side_effect = ReturnGet
            mocknsbs.side_effect = ReturnBeautifulSoup
            mocknsdpa.side_effect = ReturnDetailPageAnalysis
            mocknsmsdp.side_effect = ReturnMakeSaveDirectoryPath

            # テスト用ディレクトリが存在しているならば削除する
            # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
            if self.TBP.is_dir():
                shutil.rmtree(self.TBP)

            # 一枚絵, 漫画, うごイラ一枚, うごイラ複数 をそれぞれチェック
            illust_ids = [251267, 251197, 414793, 409587]
            for illust_id in illust_ids:
                illust_url = "https://nijie.info/view.php?id={}".format(illust_id)
                res = lsn_cont.DownloadIllusts(illust_url, str(self.TBP))
                self.assertEqual(0, res)  # どれも初めてDLしたはずなので返り値は0

                urls, author_name, author_id, illust_name = self.__GetIllustData(illust_id)
                save_directory_path = ReturnMakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, str(self.TBP))
                sd_path = Path(save_directory_path)
                
                # DL後のディレクトリ構成とファイルの存在チェック
                pages = len(urls)
                if pages > 1:  # 漫画形式、うごイラ複数
                    self.assertTrue(self.TBP.is_dir())
                    self.assertTrue(sd_path.is_dir())
                    for i, url in enumerate(urls):
                        ext = Path(url).suffix
                        file_name = "{}_{:03}{}".format(sd_path.name, i, ext)
                        self.assertTrue((sd_path / file_name).is_file())
                elif pages == 1:  # 一枚絵、うごイラ一枚
                    url = urls[0]
                    ext = Path(url).suffix
                    name = "{}{}".format(sd_path.name, ext)
                    self.assertTrue(self.TBP.is_dir())
                    self.assertTrue(sd_path.parent.is_dir())
                    self.assertTrue((sd_path.parent / name).is_file())
                else:  # エラーならばテスト結果を失敗とする
                    self.assertTrue(False)
            
            # 2回目のDLをシミュレート
            for illust_id in illust_ids:
                illust_url = "https://nijie.info/view.php?id={}".format(illust_id)
                res = lsn_cont.DownloadIllusts(illust_url, str(self.TBP))
                self.assertEqual(1, res)  # 2回目のDLなので返り値は1

    def test_DetailPageAnalysis(self):
        """html構造解析機能をチェック
        """
        with ExitStack() as stack:
            # モック置き換え
            mocklogger = stack.enter_context(patch.object(logger, "error"))
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)

            # BeautifulSoupのモック
            def ReturnBeautifulSoup(illust_id, url_s=""):
                data = self.__GetIllustData(int(illust_id))
                response = MagicMock()
            
                def ReturnFindAll(s, name=None, attrs={}, recursive=True, text=None, limit=None, **kwargs):
                    res = []
                    url = url_s
                    if name == "div" and kwargs.get("id") == "img_filter":
                        for urls_element in data[0]:
                            res.append(ReturnBeautifulSoup(illust_id, urls_element))
                    elif name == "video":
                        if ".mp4" in url or ".gif" in url:
                            url = url.split(":")[1]
                            res.append({"src": url})
                    elif name == "a":
                        aimg_mock = MagicMock()
                        url = url.split(":")[1]
                        type(aimg_mock).img = {"src": url}
                        type(aimg_mock).get = lambda s, name: {"href": url}
                        res.append(aimg_mock)
                    return res

                type(response).find_all = ReturnFindAll
                
                def ReturnFind(s, name=None, attrs={}, recursive=True, text=None, **kwargs):
                    res = None
                    if name == "title":
                        title_mock = MagicMock()
                        title_text = data[3] + " | " + data[1]
                        type(title_mock).text = str(title_text)
                        res = title_mock
                    return res

                type(response).find = ReturnFind
                return response
            
            # 一枚絵, 漫画, うごイラ一枚, うごイラ複数, エラー値 をチェック
            illust_ids = [251267, 251197, 414793, 409587, -1]
            for illust_id in illust_ids:
                soup_mock = ReturnBeautifulSoup(illust_id)
                urls, author_name, author_id, illust_name = lsn_cont.DetailPageAnalysis(soup_mock)
                expect_data = self.__GetIllustData(illust_id)
                actual_data = [urls, author_name, author_id, illust_name]
                self.assertEqual(expect_data, actual_data)

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNijie.LSNijie.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsn_cont = LSNijie.LSNijie(self.email, self.password, self.TEST_BASE_PATH)

            # 一枚絵, 漫画, うごイラ一枚, うごイラ複数 をチェック
            illust_ids = [251267, 251197, 414793, 409587]
            for illust_id in illust_ids:
                data = self.__GetIllustData(int(illust_id))

                author_name = data[1]
                author_id = data[2]
                illust_name = data[3]
                base_path = str(self.TBP)
                expect = self.TBP / "./{}({})/{}({})/".format(author_name, author_id, illust_name, illust_id)

                # 想定保存先ディレクトリが存在する場合は削除する
                if expect.is_dir():
                    shutil.rmtree(expect)

                # 保存先ディレクトリが存在しない場合の実行
                actual = Path(lsn_cont.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path))
                self.assertEqual(expect, actual)

                # 保存先ディレクトリを作成する
                actual.mkdir(parents=True, exist_ok=True)

                # 保存先ディレクトリが存在する場合の実行
                actual = Path(lsn_cont.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path))
                self.assertEqual(expect, actual)

            # エラー値をチェック
            illust_id = -1
            data = self.__GetIllustData(int(illust_id))

            author_name = data[1]
            author_id = data[2]
            illust_name = data[3]
            base_path = str(self.TBP)
            expect = ""
            actual = lsn_cont.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path)
            self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
