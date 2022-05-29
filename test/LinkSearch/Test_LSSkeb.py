# coding: utf-8
import asyncio
import configparser
import random
import shutil
import sys
import unittest
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, AsyncMock, mock_open, patch
from pathlib import Path

from PictureGathering import LSSkeb


logger = getLogger("root")
logger.setLevel(WARNING)


class TestLSSkeb(unittest.TestCase):

    def setUp(self):
        """コンフィグファイルからパスワードを取得する
        """
        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.twitter_id = config["skeb"]["twitter_id"]
        self.twitter_password = config["skeb"]["twitter_password"]

        self.TEST_BASE_PATH = "./test/PG_Skeb"
        self.TBP = Path(self.TEST_BASE_PATH)

        warnings.simplefilter("ignore", ResourceWarning)

    def tearDown(self):
        """後始末：テスト用ディレクトリを削除する
        """
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if self.TBP.is_dir():
            shutil.rmtree(self.TBP)

    def __GetSkebData(self, work_id: int) -> dict:
        """テスト用の情報を作成する

        Args:
            work_id (int): 作品ID (0 < work_id < 999)

        Returns:
            dict: 作品IDで示される作品情報を表す辞書（キーはcolsを参照）
        """
        idstr = str(work_id)
        type_dict = {
            "1": "illust",
            "2": "gif",
            "3": "video",
        }
        type = type_dict.get(idstr, "")

        url_dict = {
            "illust": "https://skeb.imgix.net/uploads/origins/xxx?yyy",
            "gif": "https://skeb.imgix.net/uploads/origins/xxx?yyy",
            "video": "https://skeb-production.xx.xxxxx.xxxxxxxxx/uploads/outputs/xxx?yyy",
        }
        url = url_dict.get(type, "")

        cols = ["id", "url", "author_name", "type"]
        data = [idstr, url, "author_1", type]
        res = {}
        for c, d in zip(cols, data):
            res[c] = d
        return res

    def __MakePyppeteerMock(self, mock: MagicMock, callback_url, selector_response):
        """Pyppeteerの機能を模倣するモックを作成する
        """
        r_launch = AsyncMock()
        r_np = AsyncMock()

        async def ReturnLaunch(headless):
            async def ReturnNewPage(s):
                def ReturnOn(s, event, f=None):
                    r_on = MagicMock()
                    type(r_on).url = callback_url
                    return f(r_on)

                type(r_np).on = ReturnOn

                async def ReturnQuerySelectorAll(s, selector):
                    return selector_response

                type(r_np).querySelectorAll = ReturnQuerySelectorAll
                return r_np

            type(r_launch).newPage = ReturnNewPage
            return r_launch

        mock.side_effect = ReturnLaunch
        return mock, r_launch, r_np

    def __MakeGetTokenMock(self, mock: MagicMock) -> MagicMock:
        """トークン取得機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.LSSkeb.LSSkeb.GetToken" にpatchする

        Returns:
            MagicMock: トークン取得機能のside_effectを持つモック
        """
        def GetTokenSideeffect(twitter_id, twitter_password):
            if self.twitter_id == twitter_id and self.twitter_password == twitter_password:
                token = "ok_token"
                return (token, True)
            else:
                return (None, False)

        mock.side_effect = GetTokenSideeffect
        return mock

    def test_LSSkeb(self):
        """Skebページ処理クラス初期状態チェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)

            # 正常系
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            expect_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
            }
            self.assertEqual(expect_headers, lssk_cont.headers)
            self.assertEqual("https://skeb.jp/", lssk_cont.top_url)
            self.assertEqual("ok_token", lssk_cont.token)
            self.assertTrue(lssk_cont.auth_success)
            self.assertTrue(self.TEST_BASE_PATH, lssk_cont.base_path)

            # 異常系
            with self.assertRaises(SystemExit):
                lssk_cont = LSSkeb.LSSkeb("invalid twitter_id", "invalid twitter_password", self.TEST_BASE_PATH)

    def test_GetTokenFromOAuth(self):
        """ツイッターログインを行いSkebページで使うtokenを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockle = stack.enter_context(patch.object(logger, "error"))
            mockli = stack.enter_context(patch.object(logger, "info"))
            mockpl = stack.enter_context(patch("pyppeteer.launch"))
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            expect = "ok_token"
            callback_url = f"https://skeb.jp/callback?path=/&token={expect}"
            selector_mock = AsyncMock()
            mockpl, r_launch, r_np = self.__MakePyppeteerMock(mockpl, callback_url, [None, selector_mock])
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(lssk_cont.GetTokenFromOAuth(self.twitter_id, self.twitter_password))
            self.assertEqual(expect, actual)

            # 正常系の呼び出し確認
            expect_newPage_call = [
                "goto",
                "waitForNavigation",
                "content",
                "cookies",
                "waitForNavigation",
                "content",
                "cookies",
                "waitFor",
                "type",
                "waitFor",
                "type",
                "waitFor",
                "click",
                "waitForNavigation",
                "waitForNavigation",
                "content",
                "cookies",
            ]
            self.assertEqual(len(expect_newPage_call), len(r_np.mock_calls))
            for enc, npc in zip(expect_newPage_call, r_np.mock_calls):
                self.assertEqual(enc, npc[0])

            # 異常系
            # コールバックURLがキャッチできなかった
            # ツイッターログインに失敗した場合もこちら
            callback_url = f"https://skeb.jp/invalid_url"
            selector_mock = AsyncMock()
            mockpl, r_launch, r_np = self.__MakePyppeteerMock(mockpl, callback_url, [None, selector_mock])
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(lssk_cont.GetTokenFromOAuth(self.twitter_id, self.twitter_password))
            self.assertEqual("", actual)

            # ログインボタンセレクト失敗
            expect = "ok_token"
            callback_url = f"https://skeb.jp/callback?path=/&token={expect}"
            mockpl, r_launch, r_np = self.__MakePyppeteerMock(mockpl, callback_url, [None, None])
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(lssk_cont.GetTokenFromOAuth(self.twitter_id, self.twitter_password))
            self.assertEqual("", actual)
            pass

    def test_GetToken(self):
        """トークン取得機能をチェック
        """
        with ExitStack() as stack:
            # open()をモックに置き換える
            mockfin = mock_open(read_data="ok_token")
            mockfp = stack.enter_context(patch("pathlib.Path.open", mockfin))

            # トークンファイルが存在する場合、一時的にリネームする
            SKEB_TOKEN_PATH = "./config/skeb_token.ini"
            stp_path = Path(SKEB_TOKEN_PATH)
            tmp_path = stp_path.parent / "tmp.ini"
            if stp_path.is_file():
                stp_path.rename(tmp_path)

            # トークンファイルが存在しない場合のテスト
            async def GetTokenFromOAuthMock(twitter_id, twitter_password):
                token = ""
                if self.twitter_id == twitter_id and self.twitter_password == twitter_password:
                    token = "ok_token_from_oauth"
                return token

            mockgtfo = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetTokenFromOAuth"))
            mockgtfo.side_effect = GetTokenFromOAuthMock
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            expect_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
            }
            self.assertEqual(expect_headers, lssk_cont.headers)
            self.assertEqual("https://skeb.jp/", lssk_cont.top_url)
            self.assertEqual("ok_token_from_oauth", lssk_cont.token)
            self.assertTrue(lssk_cont.auth_success)
            self.assertTrue(self.TEST_BASE_PATH, lssk_cont.base_path)

            # 一時的にリネームしていた場合は復元する
            # そうでない場合はダミーのファイルを作っておく
            if tmp_path.is_file():
                tmp_path.rename(stp_path)
            else:
                stp_path.touch()

            # トークンファイルが存在する場合のテスト
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            expect_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
            }
            self.assertEqual(expect_headers, lssk_cont.headers)
            self.assertEqual("https://skeb.jp/", lssk_cont.top_url)
            self.assertEqual("ok_token", lssk_cont.token)
            self.assertTrue(lssk_cont.auth_success)
            self.assertTrue(self.TEST_BASE_PATH, lssk_cont.base_path)

            # ダミーファイルがある場合は削除しておく
            if not tmp_path.is_file() and stp_path.stat().st_size == 0:
                stp_path.unlink()

    def test_MakeCallbackURL(self):
        """コールバックURLを生成する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            # 通常
            e_top_url = "https://skeb.jp/"
            e_path = "ok_path"
            e_token = "ok_token"
            expect = f"{e_top_url}callback?path=/{e_path}&token={e_token}"
            actual = lssk_cont.MakeCallbackURL(e_path, e_token)
            self.assertEqual(expect, actual)

            # pathの先頭と末尾に"/"が含まれていても処理可能かどうか
            expect = f"{e_top_url}callback?path=/{e_path}&token={e_token}"
            actual = lssk_cont.MakeCallbackURL("/" + e_path, e_token)
            self.assertEqual(expect, actual)
            actual = lssk_cont.MakeCallbackURL("/" + e_path + "/", e_token)
            self.assertEqual(expect, actual)
            actual = lssk_cont.MakeCallbackURL(e_path + "/", e_token)
            self.assertEqual(expect, actual)

            # pathが"/"のみの場合
            expect = f"{e_top_url}callback?path=/&token={e_token}"
            actual = lssk_cont.MakeCallbackURL("/", e_token)
            self.assertEqual(expect, actual)

            # 異常系
            # top_urlが壊れている
            del lssk_cont.top_url
            actual = lssk_cont.MakeCallbackURL(e_path, e_token)
            self.assertEqual("", actual)

    def test_IsValidToken(self):
        """トークンが有効かどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mocksession = stack.enter_context(patch("PictureGathering.LSSkeb.HTMLSession"))
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)

            def ReturnSession():
                response = MagicMock()

                def ReturnGet(s, url, headers):
                    r_get = MagicMock()

                    def ReturnFind(key):
                        r_find = MagicMock()
                        if "ok_token" in url:
                            r_find.attrs = {"href": "/account"}
                            r_find.full_text = "アカウント"
                        else:
                            r_find.attrs = {}
                            r_find.full_text = "無効なページ"

                        return [r_find]

                    r_get.html.find = ReturnFind
                    return r_get

                type(response).get = ReturnGet
                return response

            # 正常系
            # トークン指定あり
            mocksession.side_effect = ReturnSession
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            actual = lssk_cont.IsValidToken("ok_token")
            expect = True
            self.assertEqual(expect, actual)

            # トークン指定なし（lssk_cont.tokenが使用される）
            actual = lssk_cont.IsValidToken()
            expect = True
            self.assertEqual(expect, actual)

            # 異常系
            # 不正なトークン
            actual = lssk_cont.IsValidToken("invalid token")
            expect = False
            self.assertEqual(expect, actual)

            # lssk_cont.tokenが存在しない
            del lssk_cont.token
            actual = lssk_cont.IsValidToken()
            expect = False
            self.assertEqual(expect, actual)
            pass

    def test_IsTargetUrl(self):
        """URLがSkebのURLかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            url_s = "https://skeb.jp/@author_name/works/111"
            self.assertEqual(True, lssk_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(pixiv)
            url_s = "https://www.pixiv.net/artworks/11111111"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # httpsでなくhttp
            url_s = "http://skeb.jp/@author_name/works/111"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # プリフィックスエラー
            url_s = "ftp:https://skeb.jp/@author_name/works/111"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # サフィックスエラー
            url_s = "https://skeb.jp/@author_name/works/111?rank=1"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

    def test_GetUserWorkID(self):
        """Skeb作品ページURLから作者アカウント名と作品idを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            author_name_s = "author_name"
            work_id_s = random.randint(1, 100)
            url_s = f"https://skeb.jp/@{author_name_s}/works/{work_id_s}"
            actual = lssk_cont.GetUserWorkID(url_s)
            self.assertEqual((author_name_s, work_id_s), actual)

            # 異常系
            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            actual = lssk_cont.GetUserWorkID(url_s)
            self.assertEqual(("", -1), actual)

    def test_ConvertWebp(self):
        """webp形式の画像ファイルをpngに変換する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            def ReturnImage(target_path):
                r = MagicMock()
                type(r).convert = lambda s, m: r
                type(r).save = lambda s, fp: fp.touch()
                return r if target_path.is_file() else None
            mockimg = stack.enter_context(patch("PictureGathering.LSSkeb.Image.open"))
            mockimg.side_effect = ReturnImage

            # 正常系
            EXT = ".png"
            self.TBP.mkdir(exist_ok=True, parents=True)
            e_target_path = self.TBP / "illust.webp"
            e_target_path.touch()
            expect = str(e_target_path.with_suffix(EXT))
            actual = lssk_cont.ConvertWebp(e_target_path)
            self.assertIsNotNone(actual)
            self.assertTrue(actual.is_file())
            self.assertFalse(e_target_path.is_file())
            self.assertEqual(expect, str(actual))

            # 異常系
            # 存在しないファイルを指定
            self.TBP.mkdir(exist_ok=True, parents=True)
            e_target_path = self.TBP / "illust.webp"
            e_target_path.unlink(missing_ok=True)
            actual = lssk_cont.ConvertWebp(e_target_path)
            self.assertIsNone(actual)

    def test_GetWorkURLs(self):
        """Skeb作品ページURLから作品URLを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockle = stack.enter_context(patch.object(logger, "error"))
            mocksession = stack.enter_context(patch("PictureGathering.LSSkeb.HTMLSession"))
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            work_id_s = 1

            def ReturnSession():
                response = MagicMock()

                def ReturnGet(s, url, headers):
                    r_get = MagicMock()

                    def ReturnFind(key):
                        r_find = MagicMock()
                        sd = self.__GetSkebData(work_id_s)

                        if work_id_s == 1 and key == "img":
                            # イラスト
                            r_find.attrs = {"src": sd.get("url", "")}
                        elif work_id_s == 2 and key == "video":
                            # gif
                            r_find.attrs = {
                                "preload": "auto",
                                "autoplay": "autoplay",
                                "muted": "muted",
                                "loop": "loop",
                                "src": sd.get("url", "")
                            }
                        elif work_id_s == 3 and key == "source":
                            # 動画
                            r_find.attrs = {
                                "type": "video/mp4",
                                "src": sd.get("url", "")
                            }
                        else:
                            return []

                        return [r_find]

                    r_get.html.find = ReturnFind
                    return r_get

                type(response).get = ReturnGet
                return response

            # 正常系
            # イラスト
            mocksession.side_effect = ReturnSession
            author_name_s = "author_1"
            work_id_s = 1
            url_s = f"https://skeb.jp/@{author_name_s}/works/{work_id_s}"
            sd = self.__GetSkebData(work_id_s)
            expect = [(sd.get("url", ""), "illust")]
            actual = lssk_cont.GetWorkURLs(url_s)
            self.assertEqual(expect, actual)

            # gif
            work_id_s = 2
            url_s = f"https://skeb.jp/@{author_name_s}/works/{work_id_s}"
            sd = self.__GetSkebData(work_id_s)
            expect = [(sd.get("url", ""), "video")]
            actual = lssk_cont.GetWorkURLs(url_s)
            self.assertEqual(expect, actual)

            # 動画
            work_id_s = 3
            url_s = f"https://skeb.jp/@{author_name_s}/works/{work_id_s}"
            sd = self.__GetSkebData(work_id_s)
            expect = [(sd.get("url", ""), "video")]
            actual = lssk_cont.GetWorkURLs(url_s)
            self.assertEqual(expect, actual)

            # どのリソースも取得できなかった
            work_id_s = 4
            url_s = f"https://skeb.jp/@{author_name_s}/works/{work_id_s}"
            expect = []
            actual = lssk_cont.GetWorkURLs(url_s)
            self.assertEqual(expect, actual)

            # 異常系
            # URLが不正
            work_id_s = 1
            url_s = f"https://skeb.jp/invalid_url/{work_id_s}"
            expect = []
            actual = lssk_cont.GetWorkURLs(url_s)
            self.assertEqual(expect, actual)

            pass

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            author_name_s = "author_1"
            work_id_s = 1
            url_s = f"https://skeb.jp/@{author_name_s}/works/{work_id_s}"
            expect = self.TBP / author_name_s / f"{work_id_s:03}"
            actual = lssk_cont.MakeSaveDirectoryPath(url_s, self.TBP)
            self.assertEqual(str(expect), actual)

            # 異常系
            # 不正なURL
            url_s = f"https://skeb.jp/invalid_url"
            actual = lssk_cont.MakeSaveDirectoryPath(url_s, self.TBP)
            self.assertEqual("", actual)

    def test_DownloadWorks(self):
        """作品をダウンロードする機能をチェック
           実際にアクセスしてDLはしない
        """
        with ExitStack() as stack:
            # open()をモックに置き換える
            # mockfout = mock_open()
            # mockfp = stack.enter_context(patch("pathlib.Path.open", mockfout))
            mockle = stack.enter_context(patch.object(logger, "error"))
            mockli = stack.enter_context(patch.object(logger, "info"))
            mockrequest = stack.enter_context(patch("PictureGathering.LSSkeb.requests.get"))
            mockcw = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.ConvertWebp"))
            mockgt = stack.enter_context(patch("PictureGathering.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            # サイドエフェクト設定
            def ReturnConvertWebp(target_path: Path, ext: str = ".png"):
                dst_path = target_path.with_suffix(ext)
                shutil.copy(target_path, dst_path)
                target_path.unlink(missing_ok=True)
                return dst_path

            def ReturnGet(url, headers):
                response = MagicMock()
                type(response).content = str(url).encode()
                return response

            mockcw.side_effect = ReturnConvertWebp
            mockrequest.side_effect = ReturnGet

            # 検証用作者アカウント名等設定
            NUM = 3  # 検証用作者アカウント数
            work_id = 0  # 作品id（インクリメントされる）
            # 変換処理用辞書
            p_dict = {
                "illust": (True, ".webp", ".png"),
                "video": (False, ".mp4", ".mp4"),
            }
            # 検証用作者名リスト
            author_name_list = [f"author_{i}" for i in range(1, NUM + 1)]
            # タイプリスト
            type_list = ["illust", "video"]
            # すべての検証用作者アカウント,タイプについて検証する
            for author_name in author_name_list:
                for type_s in type_list:
                    # 単一作品と複数作品について検証する
                    urls_list = [
                        ["https://skeb.resource.test/001_xxx?yyy"],  # 単一
                        [f"https://skeb.resource.test/{i:03}_xxx?yyy" for i in range(1, random.randint(3, NUM + 3))],  # 複数
                    ]
                    for urls in urls_list:
                        # source_list設定
                        # work_id = random.randint(1, NUM * 2)
                        work_id = work_id + 1
                        dst_ext = p_dict.get(type_s, (False, "", ""))[2]
                        source_list_s = [(url, type_s) for url in urls]

                        # save_directory_path設定
                        url_s = f"https://skeb.jp/@{author_name}/works/{work_id}"
                        save_directory_path = lssk_cont.MakeSaveDirectoryPath(url_s, self.TBP)
                        sd_path = Path(save_directory_path)

                        # 1回目の実行
                        actual = lssk_cont.DownloadWorks(source_list_s, save_directory_path)
                        self.assertEqual(0, actual)

                        # DL後のディレクトリ構成とファイルの存在チェック
                        sd_path = Path(save_directory_path)
                        if len(source_list_s) > 1:
                            # 複数作品
                            expect_names = []
                            for i, src in enumerate(source_list_s):
                                file_name = f"{author_name}_{work_id:03}_{i:03}{dst_ext}"
                                expect_names.append(file_name)

                            self.assertTrue(self.TBP.is_dir())
                            self.assertTrue(sd_path.is_dir())
                            for name_s in expect_names:
                                self.assertTrue((sd_path / name_s).is_file())
                        else:
                            # 単一作品
                            file_name = f"{author_name}_{work_id:03}{dst_ext}"
                            self.assertTrue(self.TBP.is_dir())
                            self.assertTrue(sd_path.parent.is_dir())
                            self.assertTrue((sd_path.parent / file_name).is_file())

                        # requests.getが呼ばれたかどうか確認
                        mockrequest.assert_called()
                        mockrequest.reset_mock()

                        # 変換処理をする設定なら変換処理が呼ばれたかどうか確認
                        if p_dict.get(type_s, (False, "", ""))[0]:
                            mockcw.assert_called()
                            mockcw.reset_mock()
                        else:
                            mockcw.assert_not_called()

                        # 2回目の実行
                        actual = lssk_cont.DownloadWorks(source_list_s, save_directory_path)
                        self.assertEqual(1, actual)
                        pass

            # 異常系
            # requests.getに失敗
            def ReturnGetFailed(url, headers):
                response = MagicMock()
                response.raise_for_status.side_effect = Exception("Mock Exception")
                return response

            mockrequest.side_effect = ReturnGetFailed
            urls_list = [
                ["https://skeb.resource.test/001_xxx?yyy"],  # 単一
                [f"https://skeb.resource.test/{i:03}_xxx?yyy" for i in range(1, random.randint(3, NUM + 3))],  # 複数
            ]
            for urls in urls_list:
                source_list_s = [(url, "illust") for url in urls]
                url_s = f"https://skeb.jp/@author_1/works/99"
                save_directory_path = lssk_cont.MakeSaveDirectoryPath(url_s, self.TBP)
                with self.assertRaises(Exception):
                    actual = lssk_cont.DownloadWorks(source_list_s, save_directory_path)

            # タイプが不正
            mockrequest.side_effect = ReturnGet
            for urls in urls_list:
                source_list_s = [(url, "invlid_type") for url in urls]
                url_s = f"https://skeb.jp/@author_2/works/99"
                save_directory_path = lssk_cont.MakeSaveDirectoryPath(url_s, self.TBP)

                actual = lssk_cont.DownloadWorks(source_list_s, save_directory_path)
                self.assertEqual(-1, actual)
            pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
