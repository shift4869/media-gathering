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

from requests import adapters
from requests.models import HTTPError

from PictureGathering import LSNicoSeiga


logger = getLogger("root")
logger.setLevel(WARNING)


class TestLSNicoSeiga(unittest.TestCase):

    def setUp(self):
        """コンフィグファイルからパスワードを取得する
        """
        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.email = config["nico_seiga"]["email"]
        self.password = config["nico_seiga"]["password"]
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

        self.TEST_BASE_PATH = "./test/PG_Seiga"
        self.TBP = Path(self.TEST_BASE_PATH)

    def tearDown(self):
        """後始末：テスト用ディレクトリを削除する
        """
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if self.TBP.is_dir():
            shutil.rmtree(self.TBP)

    def __GetIllustData(self, illust_id: int) -> tuple[list[str], str, int, str]:
        """テスト用の静画情報を作成する

        Args:
            illust_id (int): イラストID (0 < illust_id < 99999999)

        Returns:
            イラストIDで示される以下のイラスト情報を表す辞書（キーはcolsを参照）
                url (str): 画像直リンクURL
                author_name (str): 作者名
                author_id (int): 作者ID
                illust_name (str): イラスト名
                ext (str): 拡張子（'.xxx'）
            illust_idが不正値の場合は空辞書を返す
        """
        idstr = str(illust_id)
        cols = ["illust_id", "url", "author_name", "author_id", "illust_name", "ext"]
        
        urls = {
            "5360137": "https://lohas.nicoseiga.jp/priv/718eac68eb1946a1eec1c887fbaa555bba98f160/1621735446/5360137",
        }
        data = {
            "5360137": [5360137, urls["5360137"], "author_name", 22907347, "title", ".jpg"],
        }
        res = {}

        # 不正値の場合は空辞書を返す
        if not data.get(idstr):
            return {}

        for c, d in zip(cols, data[idstr]):
            res[c] = d
        return res

    def __GetAuthorName(self, author_id: int) -> tuple[list[str], str, int, str]:
        """テスト用の作者名を取得する

        Args:
            author_id (int): 作者ID

        Returns:
            author_name (str): 作者名、author_idが不正値の場合は空文字列を返す
        """
        data = {
            "22907347": "author_name"
        }
        return data.get(str(author_id), "")

    def __MakeSessionMock(self) -> MagicMock:
        """セッションのモックを作成する
        """
        session = MagicMock()
        type(session).mount = lambda s, prefix, adapter: str(prefix) + str(adapter)

        # session.postで取得する内容のモックを返す
        def ReturnPost(s, url, data={}, headers={}):
            response = MagicMock()

            def IsValid(s):
                # ログイン時に使用するエンドポイント
                NS_LOGIN_ENDPOINT = "https://account.nicovideo.jp/api/v1/login?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url=&mail_or_tel=1"
                # ログインページのURLか
                f_url = (url == NS_LOGIN_ENDPOINT)
                # ログイン情報は正しいか
                f_outh = (data.get("mail_tel") == self.email) and (data.get("password") == self.password)
                # ヘッダーは正しいか
                f_headers = (headers == self.headers)

                is_valid = (f_url and f_outh and f_headers)
                if not is_valid:
                    raise HTTPError
                return is_valid

            type(response).raise_for_status = IsValid

            return response

        type(session).post = ReturnPost

        # session.getで取得する内容のモックを返す
        def ReturnGet(s, url, headers={}):
            response = MagicMock()

            # 静画情報取得APIエンドポイント
            NS_IMAGE_INFO_API_ENDPOINT = "http://seiga.nicovideo.jp/api/illust/info?id="
            if NS_IMAGE_INFO_API_ENDPOINT in url:
                # クエリを取得する
                qs = urllib.parse.urlparse(url).query
                qd = urllib.parse.parse_qs(qs)
                illust_id = int(qd["id"][0])

                # 静画情報
                info = self.__GetIllustData(illust_id)
                info_url = NS_IMAGE_INFO_API_ENDPOINT + str(illust_id)
                if url == info_url and info:
                    author_id = info["author_id"]
                    illust_name = info["illust_name"]
                    type(response).text = f"<image><user_id>{author_id}</user_id><title>{illust_name}</title></image>"

            # 作者情報取得APIエンドポイント
            NS_USERNAME_API_ENDPOINT = "https://seiga.nicovideo.jp/api/user/info?id="
            if NS_USERNAME_API_ENDPOINT in url:
                # クエリを取得する
                qs = urllib.parse.urlparse(url).query
                qd = urllib.parse.parse_qs(qs)
                author_id = int(qd["id"][0])

                # 作者情報
                author_name = self.__GetAuthorName(author_id)
                username_info_url = NS_USERNAME_API_ENDPOINT + str(author_id)
                if url == username_info_url and author_name:
                    type(response).text = f"<user><user_id>{author_id}</user_id><nickname>{author_name}</nickname></user>"

            # ニコニコ静画ページ取得APIエンドポイント
            NS_IMAGE_SOUECE_API_ENDPOINT = "http://seiga.nicovideo.jp/image/source?id="
            if NS_IMAGE_SOUECE_API_ENDPOINT in url:
                # クエリを取得する
                qs = urllib.parse.urlparse(url).query
                qd = urllib.parse.parse_qs(qs)
                illust_id = int(qd["id"][0])

                # 画像直リンク
                info = self.__GetIllustData(illust_id)
                source_page_url = NS_IMAGE_SOUECE_API_ENDPOINT + str(illust_id)
                if url == source_page_url and info:
                    source_url = info["url"]
                    type(response).text = f'''
                        <div id="content" class="illust_big">
                            <div class="controll">
                                <ul><li class="close"><img src="/img/btn_close.png" alt="閉じる"></li></ul>
                            </div>
                            <div class="illust_view_big"
                                 data-src="{source_url}"
                                 data-watch_url="https://seiga.nicovideo.jp/seiga/im{illust_id}">
                            </div>
                        </div>
                    '''

            def IsValid(s):
                # ヘッダーは正しいか
                f_headers = (headers == self.headers)
                if not f_headers:
                    raise HTTPError
                return f_headers

            type(response).raise_for_status = IsValid
            return response

        type(session).get = ReturnGet
        return session

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        """セッション開始とログイン機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.LSNicoSeiga.LSNicoSeiga.Login" にpatchする

        Returns:
            MagicMock: セッション開始とログイン機能のside_effectを持つモック
        """
        def LoginSideeffect(email, password):
            if self.email == email and self.password == password:
                session = self.__MakeSessionMock()
                return (session, True)
            else:
                return (None, False)

        mock.side_effect = LoginSideeffect
        return mock

    def test_LSNicoSeiga(self):
        """静画ページ取得クラス初期状態チェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)

            # 正常系
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            self.assertEqual(self.headers, lsns_cont.headers)
            self.assertIsNotNone(lsns_cont.session)
            self.assertTrue(lsns_cont.auth_success)
            self.assertEqual(self.TEST_BASE_PATH, lsns_cont.base_path)

            # 異常系
            with self.assertRaises(SystemExit):
                lsns_cont = LSNicoSeiga.LSNicoSeiga("invalid email", "invalid password", self.TEST_BASE_PATH)

    def test_Login(self):
        """セッション開始とログイン機能をチェック
        """
        with ExitStack() as stack:
            # モック置き換え
            mocksession = stack.enter_context(patch("PictureGathering.LSNicoSeiga.requests.session"))
            mocksession.side_effect = self.__MakeSessionMock

            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)
            self.assertEqual(self.headers, lsns_cont.headers)
            self.assertIsNotNone(lsns_cont.session)
            self.assertTrue(lsns_cont.auth_success)
            self.assertEqual(self.TEST_BASE_PATH, lsns_cont.base_path)

    def test_IsTargetUrl(self):
        """URLがニコニコ静画のURLかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            # 作品ページURL
            url_s = "https://seiga.nicovideo.jp/seiga/im5360137"
            self.assertEqual(True, lsns_cont.IsTargetUrl(url_s))

            # 作品ページURL（クエリつき）
            url_s = "https://seiga.nicovideo.jp/seiga/im5360137?track=ranking"
            self.assertEqual(True, lsns_cont.IsTargetUrl(url_s))

            # 異常系
            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            self.assertEqual(False, lsns_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(pixiv)
            url_s = "https://www.pixiv.net/artworks/24010650"
            self.assertEqual(False, lsns_cont.IsTargetUrl(url_s))

            # 漫画ページ
            url_s = "https://seiga.nicovideo.jp/watch/mg558273"
            self.assertEqual(False, lsns_cont.IsTargetUrl(url_s))

            # httpsでなくhttp
            url_s = "http://seiga.nicovideo.jp/seiga/im5360137"
            self.assertEqual(False, lsns_cont.IsTargetUrl(url_s))

            # 静画の別ページ
            url_s = "https://seiga.nicovideo.jp/illust/ranking/point/hourly?save=1"
            self.assertEqual(False, lsns_cont.IsTargetUrl(url_s))

            # プリフィックスエラー
            url_s = "ftp://seiga.nicovideo.jp/seiga/im5360137"
            self.assertEqual(False, lsns_cont.IsTargetUrl(url_s))

    def test_GetIllustId(self):
        """ニコニコ静画作品ページURLからイラストIDを取得する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            r = "{:0>7}".format(random.randint(0, 9999999))
            # 作品ページURL
            url_s = "https://seiga.nicovideo.jp/seiga/im{}".format(r)
            expect = int(r)
            actual = lsns_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

            # 異常系
            # 漫画ページ
            url_s = "https://seiga.nicovideo.jp/watch/mg{}".format(r)
            expect = -1
            actual = lsns_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

    def test_GetIllustInfo(self):
        """ニコニコ静画情報を取得する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            illust_id = 5360137
            expect_info = self.__GetIllustData(illust_id)
            expect = (int(expect_info["author_id"]), expect_info["illust_name"])
            actual = lsns_cont.GetIllustInfo(illust_id)
            self.assertEqual(expect, actual)

            # 異常系
            illust_id = -1
            expect = (-1, "")
            actual = lsns_cont.GetIllustInfo(illust_id)
            self.assertEqual(expect, actual)

    def test_GetAuthorName(self):
        """ニコニコ静画の作者名を取得する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            illust_id = 5360137
            author_id = 22907347
            expect_info = self.__GetIllustData(illust_id)
            expect = expect_info["author_name"]
            actual = lsns_cont.GetAuthorName(author_id)
            self.assertEqual(expect, actual)

            # 異常系
            author_id = -1
            expect = ""
            actual = lsns_cont.GetAuthorName(author_id)
            self.assertEqual(expect, actual)

    def test_GetSourceURL(self):
        """ニコニコ静画の画像直リンクを取得する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            illust_id = 5360137
            expect_info = self.__GetIllustData(illust_id)
            expect = expect_info["url"]
            actual = lsns_cont.GetSourceURL(illust_id)
            self.assertEqual(expect, actual)

            # 異常系
            illust_id = -1
            expect = ""
            actual = lsns_cont.GetSourceURL(illust_id)
            self.assertEqual(expect, actual)

    def test_GetExtFromBytes(self):
        """バイナリデータ配列から拡張子を判別する機能をチェック
        """
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # 正常系
            # .jpg
            data = b"\xff\xd8\xff\xff\xff\xff\xff\xff"
            self.assertEqual(".jpg", lsns_cont.GetExtFromBytes(data))

            # .png
            data = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
            self.assertEqual(".png", lsns_cont.GetExtFromBytes(data))

            # .gif
            data = b"\x47\x49\x46\x38\xff\xff\xff\xff"
            self.assertEqual(".gif", lsns_cont.GetExtFromBytes(data))

            # 異常系
            # 全く関係ないバイナリ
            data = b"\xff\xff\xff\xff\xff\xff\xff\xff"
            self.assertEqual(".invalid", lsns_cont.GetExtFromBytes(data))

            # 短いバイナリ
            data = b"\xff\xff\xff\xff"
            self.assertEqual(".invalid", lsns_cont.GetExtFromBytes(data))

    def test_DownloadIllusts(self):
        """ニコニコ静画作品ページURLからダウンロードする機能をチェック
        """
        return
        with ExitStack() as stack:
            # モック置き換え
            mocknsreqget = stack.enter_context(patch("PictureGathering.LSNicoSeiga.requests.get"))
            mocknsbs = stack.enter_context(patch("PictureGathering.LSNicoSeiga.BeautifulSoup"))
            mocknsdpa = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.DetailPageAnalysis"))
            mocknsmsdp = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.MakeSaveDirectoryPath"))

            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

            # requests.getで取得する内容のモックを返す
            def ReturnGet(url, headers, cookies):
                response = MagicMock()

                # メディアDL時
                pattern = r"^http://pic.seiga.net/[^$]*$"
                regex = re.compile(pattern)
                f1 = not (regex.findall(url) == [])

                # 作品詳細ページをGET時
                pattern = r"^http://seiga.info/view_popup.php\?id=[0-9]*$"
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
                    type(response).text = "ニジエ - seiga ," + url  # イラストID伝達用
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
                illust_url = "http://seiga.info/view.php?id={}".format(illust_id)
                res = lsns_cont.DownloadIllusts(illust_url, str(self.TBP))
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
                        file_name = "{:03}{}".format(i, ext)
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
                illust_url = "http://seiga.info/view.php?id={}".format(illust_id)
                res = lsns_cont.DownloadIllusts(illust_url, str(self.TBP))
                self.assertEqual(1, res)  # 2回目のDLなので返り値は1

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        return
        with ExitStack() as stack:
            mocknslogin = stack.enter_context(patch("PictureGathering.LSNicoSeiga.LSNicoSeiga.Login"))
            mocknslogin = self.__MakeLoginMock(mocknslogin)
            lsns_cont = LSNicoSeiga.LSNicoSeiga(self.email, self.password, self.TEST_BASE_PATH)

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
                actual = Path(lsns_cont.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path))
                self.assertEqual(expect, actual)

                # 保存先ディレクトリを作成する
                actual.mkdir(parents=True, exist_ok=True)

                # 保存先ディレクトリが存在する場合の実行
                actual = Path(lsns_cont.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path))
                self.assertEqual(expect, actual)

            # エラー値をチェック
            illust_id = -1
            data = self.__GetIllustData(int(illust_id))

            author_name = data[1]
            author_id = data[2]
            illust_name = data[3]
            base_path = str(self.TBP)
            expect = ""
            actual = lsns_cont.MakeSaveDirectoryPath(author_name, author_id, illust_name, illust_id, base_path)
            self.assertEqual(expect, actual)

    def test_Process(self):
        pass

if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
