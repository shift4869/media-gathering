# coding: utf-8
import configparser
import random
import re
import shutil
import sys
import unittest
import urllib.parse
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, PropertyMock, mock_open, patch
from pathlib import Path
from time import sleep
from typing import List

from PictureGathering import NijieScraping


logger = getLogger("root")
logger.setLevel(WARNING)


class TestNijieController(unittest.TestCase):

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

    def __GetIllustData(self, illust_id: int) -> dict:
        """テスト用のイラスト情報を作成する

        Args:
            illust_id (int): イラストID (0 < illust_id < 99999999)

        Returns:
            dict: イラストIDで示されるイラスト情報を表す辞書（キーはcolsを参照）
        """
        pass

    def __MakeSoupMock(self) -> MagicMock:
        """html構造解析時のbs4モックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            find_all("div", id="img_filter")[]
                find_all("video")[]
                    {"src": "video_url"}
                find_all("a")[]
                    img["src"]

        Returns:
            MagicMock: api_response
        """
        def ReturnWorks(illust_id):
            r_works = MagicMock()
            p_status = PropertyMock()
            s = {}
            if 0 < illust_id and illust_id < 99999999:
                p_status.return_value = "success"
                s = self.__GetIllustData(illust_id)
            else:
                p_status.return_value = "failed"
            type(r_works).status = p_status

            def ReturnResponse():
                r_response = MagicMock()
                p_type = PropertyMock()
                p_type.return_value = s["type"]
                type(r_response).type = p_type

                p_is_manga = PropertyMock()
                p_is_manga.return_value = s["is_manga"]
                type(r_response).is_manga = p_is_manga

                r_name_id = MagicMock()
                p_name = PropertyMock()
                p_name.return_value = s["author_name"]
                type(r_name_id).name = p_name
                p_id = PropertyMock()
                p_id.return_value = s["author_id"]
                type(r_name_id).id = p_id
                p_user = PropertyMock()
                p_user.return_value = r_name_id
                type(r_response).user = p_user

                p_title = PropertyMock()
                p_title.return_value = s["title"]
                type(r_response).title = p_title

                def ReturnLarge(url):
                    r_large = MagicMock()
                    p_large = PropertyMock()

                    p_large.return_value = url
                    type(r_large).large = p_large
                    return r_large

                def ReturnImageurls(url):
                    r_imageurls = MagicMock()
                    p_imageurls = PropertyMock()
                    p_imageurls.return_value = ReturnLarge(url)
                    type(r_imageurls).image_urls = p_imageurls
                    return r_imageurls

                def ReturnPages():
                    r_pages = MagicMock()
                    p_pages = PropertyMock()

                    # 漫画形式のreturn_value設定
                    p_pages.return_value = [ReturnImageurls(url) for url in s["image_urls"]]
                    type(r_pages).pages = p_pages
                    return r_pages

                p_metadata = PropertyMock()
                p_metadata.return_value = ReturnPages()
                type(r_response).metadata = p_metadata

                # 一枚絵のreturn_value設定
                p_image_urls = PropertyMock()
                p_image_urls.return_value = ReturnLarge(s["image_url"])
                type(r_response).image_urls = p_image_urls

                return r_response

            p_response = PropertyMock()
            p_response.side_effect = lambda: [ReturnResponse()]
            type(r_works).response = p_response

            return r_works

        api_response = MagicMock()
        p_works = PropertyMock()
        p_works.return_value = ReturnWorks
        type(api_response).works = p_works

        p_access_token = PropertyMock()
        p_access_token.return_value = "ok"
        type(api_response).access_token = p_access_token

        return api_response

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        """nijieページへのログイン機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.NijieScraping.NijieController.Login" にpatchする

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

    def test_NijieController(self):
        """nijieページ取得初期状態チェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)

            # 正常系
            ns_cont = NijieScraping.NijieController(self.email, self.password)
            expect_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

            self.assertEqual(expect_headers, ns_cont.headers)
            self.assertIsNotNone(ns_cont.cookies)
            self.assertTrue(ns_cont.auth_success)

            # 異常系
            with self.assertRaises(SystemExit):
                ns_cont = NijieScraping.NijieController("invalid email", "invalid password")

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
            mocknsreqget = stack.enter_context(patch("PictureGathering.NijieScraping.requests.get"))
            mocknsreqpost = stack.enter_context(patch("PictureGathering.NijieScraping.requests.post"))
            mocknsreqcj = stack.enter_context(patch("PictureGathering.NijieScraping.requests.cookies.RequestsCookieJar"))
            mocknsisvalidcookies = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.IsValidCookies"))

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
            ns_cont = NijieScraping.NijieController(self.email, self.password)
            self.assertEqual(1, len(ns_cont.cookies))
            res_cookies = ns_cont.cookies[0]
            actual_cookies = {
                "name": res_cookies.name,
                "value": res_cookies.value,
                "expires": res_cookies.expires,
                "path": res_cookies.path,
                "domain": res_cookies.domain,
            }
            self.assertEqual(expect_cookies, actual_cookies)
            self.assertTrue(ns_cont.auth_success)
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
            ns_cont = NijieScraping.NijieController(self.email, self.password)
            self.assertEqual(expect_cookies, actual_read_cookies)
            self.assertTrue(ns_cont.auth_success)
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
            pass

    def test_IsValidCookies(self):
        """クッキーが正しいかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            ns_cont = NijieScraping.NijieController(self.email, self.password)

            mocknsreqget = stack.enter_context(patch("PictureGathering.NijieScraping.requests.get"))

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
            res = ns_cont.IsValidCookies(ns_cont.headers, ns_cont.cookies)
            self.assertTrue(res)

            # 異常系
            res = ns_cont.IsValidCookies(None, None)
            self.assertFalse(res)
            res = ns_cont.IsValidCookies(ns_cont.headers, "invalid cookies")
            self.assertFalse(res)

    def test_IsNijieURL(self):
        """nijieのURLかどうか判定する機能をチェック
        """
        # クラスメソッドなのでインスタンス無しで呼べる
        IsNijieURL = NijieScraping.NijieController.IsNijieURL

        # 正常系
        # 作品ページURL
        url_s = "http://nijie.info/view.php?id=251267"
        self.assertEqual(True, IsNijieURL(url_s))

        # 作品詳細ページURL
        url_s = "http://nijie.info/view_popup.php?id=251267"
        self.assertEqual(True, IsNijieURL(url_s))

        # 異常系
        # 全く関係ないアドレス(Google)
        url_s = "https://www.google.co.jp/"
        self.assertEqual(False, IsNijieURL(url_s))

        # 全く関係ないアドレス(pixiv)
        url_s = "https://www.pixiv.net/artworks/24010650"
        self.assertEqual(False, IsNijieURL(url_s))

        # httpでなくhttps
        url_s = "https://nijie.info/view_popup.php?id=251267"
        self.assertEqual(False, IsNijieURL(url_s))

        # nijieの別ページ
        url_s = "http://nijie.info/user_like_illust_view.php?id=21030"
        self.assertEqual(False, IsNijieURL(url_s))

        # プリフィックスエラー
        url_s = "ftp://nijie.info/view.php?id=251267"
        self.assertEqual(False, IsNijieURL(url_s))

        # サフィックスエラー
        url_s = "http://nijie.info/view.php?id=251267&rank=1"
        self.assertEqual(False, IsNijieURL(url_s))

    def test_GetIllustId(self):
        """nijie作品ページURLからイラストIDを取得する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            ns_cont = NijieScraping.NijieController(self.email, self.password)

            # 正常系
            r = "{:0>6}".format(random.randint(0, 999999))
            # 作品ページURL
            url_s = "http://nijie.info/view.php?id={}".format(r)
            expect = int(r)
            actual = ns_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

            # 作品詳細ページURL
            url_s = "http://nijie.info/view_popup.php?id={}".format(r)
            expect = int(r)
            actual = ns_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "http://nijie.info/view.php?id={}&rank=1".format(r)
            expect = -1
            actual = ns_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
        """
        with ExitStack() as stack:
            # モック置き換え
            mocknsreqget = stack.enter_context(patch("PictureGathering.NijieScraping.requests.get"))
            mocknsbs = stack.enter_context(patch("PictureGathering.NijieScraping.BeautifulSoup"))
            mocknsdpa = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.DetailPageAnalysis"))
            mocknsmsdp = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.MakeSaveDirectoryPath"))

            mocknslogin = stack.enter_context(patch("PictureGathering.NijieScraping.NijieController.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            ns_cont = NijieScraping.NijieController(self.email, self.password)

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
                urls = {
                    "251267": ["http://pic.nijie.net/05/nijie_picture/21030_20180226022216_0.jpg"],
                    "251197": ["http://pic.nijie.net/05/nijie_picture/21030_20180225212822_0.jpg",
                               "http://pic.nijie.net/02/nijie_picture/diff/main/21030_20180225212823_0.jpg",
                               "http://pic.nijie.net/05/nijie_picture/diff/main/21030_20180225212824_1.jpg",
                               "http://pic.nijie.net/05/nijie_picture/diff/main/21030_20180225212824_2.jpg",
                               "http://pic.nijie.net/02/nijie_picture/diff/main/21030_20180225212824_3.jpg",
                               "http://pic.nijie.net/04/nijie_picture/diff/main/21030_20180225212825_4.jpg",
                               "http://pic.nijie.net/01/nijie_picture/diff/main/21030_20180225212827_5.jpg",
                               "http://pic.nijie.net/01/nijie_picture/diff/main/21030_20180225212828_6.jpg",
                               "http://pic.nijie.net/05/nijie_picture/diff/main/21030_20180225212828_7.jpg",
                               "http://pic.nijie.net/04/nijie_picture/diff/main/21030_20180225212828_8.jpg"],
                    "414793": ["http://pic.nijie.net/06/nijie_picture/4112_20210207002919_0.mp4"],
                    "409587": ["http://pic.nijie.net/06/nijie_picture/317190_20210107221003_0.gif",
                               "http://pic.nijie.net/01/nijie_picture/diff/main/409587_317190_20210107221005_0.mp4",
                               "http://pic.nijie.net/06/nijie_picture/diff/main/409587_317190_20210107221006_1.gif",
                               "http://pic.nijie.net/06/nijie_picture/diff/main/409587_317190_20210107221006_2.gif",
                               "http://pic.nijie.net/06/nijie_picture/diff/main/409587_317190_20210107221007_3.gif",
                               "http://pic.nijie.net/06/nijie_picture/diff/main/409587_317190_20210107221007_4.gif",
                               "http://pic.nijie.net/06/nijie_picture/diff/main/409587_5_317190_20210108181522.gif"]
                }
                cols = ["illust_id", "urls", "author_name", "author_id", "illust_name"]
                data = {
                    "251267": [urls["251267"], "黒雲鵺", 21030, "一枚絵"],
                    "251197": [urls["251197"], "黒雲鵺", 21030, "漫画"],
                    "414793": [urls["414793"], "むむ", 4112, "うごイラ一枚"],
                    "409587": [urls["409587"], "mfp", 317190, "うごイラ複数"]
                }
                return data[illust_id]

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

            # illust_id = 251267  # 一枚絵
            # illust_id = 251197  # 漫画
            # illust_id = 414793  # うごイラ一枚
            # illust_id = 409587  # うごイラ複数
            url_s = "http://nijie.info/view.php?id=251267"
            ns_cont.DownloadIllusts(url_s, str(self.TBP))

        pass

    def test_DetailPageAnalysis(self):
        """html構造解析機能をチェック
        """
        pass

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
