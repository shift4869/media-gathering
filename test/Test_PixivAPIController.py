# coding: utf-8
import configparser
import glob
import os
import random
import re
import shutil
import sys
import unittest
import warnings
from logging import WARNING, getLogger

from contextlib import ExitStack
from mock import MagicMock, PropertyMock, mock_open, patch
from pixivpy3 import *

from PictureGathering import PixivAPIController


logger = getLogger("root")
logger.setLevel(WARNING)


class TestPixivAPIController(unittest.TestCase):

    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)

        CONFIG_FILE_NAME = "./config/config.ini"
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.username = self.config["pixiv"]["username"]
        self.password = self.config["pixiv"]["password"]

    def tearDown(self):
        pass

    def test_PixivAPIController(self):
        """非公式pixivAPI利用クラス初期状態チェック
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        self.assertIsNotNone(pa_cont.api)
        self.assertIsNotNone(pa_cont.aapi)
        self.assertTrue(pa_cont.auth_success)
        self.assertIsNotNone(pa_cont.api.access_token)
        self.assertIsNotNone(pa_cont.aapi.access_token)

    def test_Login(self):
        """非公式pixivAPIインスタンス生成とログインをチェック
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        
        # auth関数のsideeffect
        def auth_side_effect(refresh_token):
            return refresh_token

        # login関数のsideeffect
        def login_side_effect(username, password):
            return (username, password)

        # インスタンス生成時のsideeffectを生成する
        # access_token, refresh_tokenを属性として持ち、
        # auth(), login()をメソッドとして持つオブジェクトを模倣する
        def response_factory(access_token, refresh_token):
            response = MagicMock()
            p_access_token = PropertyMock()
            p_access_token.return_value = access_token
            type(response).access_token = p_access_token

            p_refresh_token = PropertyMock()
            p_refresh_token.return_value = refresh_token
            type(response).refresh_token = p_access_token

            p_auth = MagicMock()
            p_auth.side_effect = auth_side_effect
            type(response).auth = p_auth

            p_login = MagicMock()
            p_login.side_effect = login_side_effect
            type(response).login = p_login
            return response

        # インスタンス生成時のsideeffect(PixivAPI(), AppPixivAPI())
        def api_side_effect():
            return response_factory(pa_cont.api.access_token, pa_cont.api.refresh_token)

        # モック生成と一連のテストをまとめた関数
        def LoginProcessTest():
            with ExitStack() as stack:
                # open()をモックに置き換える
                mockfout = mock_open()
                mockfp = stack.enter_context(patch("PictureGathering.PixivAPIController.open", mockfout))
                
                mockpapub = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPI"))
                mockpaapp = stack.enter_context(patch("PictureGathering.PixivAPIController.AppPixivAPI"))

                mockpapub.side_effect = api_side_effect
                mockpaapp.side_effect = api_side_effect

                expect = (mockpapub.side_effect, mockpaapp.side_effect, True)
                actual = pa_cont.Login(self.username, self.password)

                self.assertEqual(mockpapub.call_count, 1)
                self.assertEqual(mockpaapp.call_count, 1)
                self.assertIsNotNone(actual[0])
                self.assertIsNotNone(actual[1])
                self.assertEqual(expect[2], actual[2])

        # 新規ログインを伴うテストを抑制する場合はFalse
        # 新規ログインを伴うテストを行う場合はTrue
        # TODO::パラメータによる分岐
        IS_NEW_LOGIN_TEST = False

        # refresh_tokenが既に存在しているなら削除
        REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
        if os.path.exists(REFRESH_TOKEN_PATH) and IS_NEW_LOGIN_TEST:
            os.remove(REFRESH_TOKEN_PATH)

        # refresh_tokenが存在していない状況をエミュレート
        LoginProcessTest()

        # refresh_tokenを保存
        refresh_token = pa_cont.api.refresh_token
        with open(REFRESH_TOKEN_PATH, "w") as fout:
            fout.write(refresh_token)
        self.assertTrue(os.path.exists(REFRESH_TOKEN_PATH))

        # refresh_tokenが存在している状況をエミュレート
        LoginProcessTest()

        # refresh_tokenは保存したままにしておく
        self.assertTrue(os.path.exists(REFRESH_TOKEN_PATH))

    def test_IsPixivURL(self):
        """pixivのURLかどうか判定する機能をチェック
        """
        # pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        # クラスメソッドなのでインスタンス無しで呼べる
        IsPixivURL = PixivAPIController.PixivAPIController.IsPixivURL
        
        # 正常系
        url_s = "https://www.pixiv.net/artworks/24010650"
        self.assertEqual(True, IsPixivURL(url_s))

        # 全く関係ないアドレス(Google)
        url_s = "https://www.google.co.jp/"
        self.assertEqual(False, IsPixivURL(url_s))

        # 全く関係ないアドレス(nijie)
        url_s = "http://nijie.info/view.php?id=402197"
        self.assertEqual(False, IsPixivURL(url_s))

        # httpsでなくhttp
        url_s = "http://www.pixiv.net/artworks/24010650"
        self.assertEqual(False, IsPixivURL(url_s))

        # pixivの別ページ
        url_s = "https://www.pixiv.net/bookmark_new_illust.php"
        self.assertEqual(False, IsPixivURL(url_s))

        # プリフィックスエラー
        url_s = "ftp:https://www.pixiv.net/artworks/24010650"
        self.assertEqual(False, IsPixivURL(url_s))

        # サフィックスエラー
        url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
        self.assertEqual(False, IsPixivURL(url_s))

    def test_GetIllustId(self):
        """pixiv作品ページURLからイラストIDを取得する機能をチェック
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)

        # 正常系
        r = "{:0>8}".format(random.randint(0, 99999999))
        url_s = "https://www.pixiv.net/artworks/" + r
        expect = int(r)
        actual = pa_cont.GetIllustId(url_s)
        self.assertEqual(expect, actual)

        # サフィックスエラー
        url_s = "https://www.pixiv.net/artworks/{}?rank=1".format(r)
        expect = -1
        actual = pa_cont.GetIllustId(url_s)
        self.assertEqual(expect, actual)

    def test_GetIllustURLs(self):
        """pixiv作品ページURLからイラストへの直リンクを取得する機能をチェック
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        
        # 一枚絵
        url_s = "https://www.pixiv.net/artworks/59580629"
        expect = ["https://i.pximg.net/img-original/img/2016/10/22/10/11/37/59580629_p0.jpg"]
        actual = pa_cont.GetIllustURLs(url_s)
        self.assertEqual(expect, actual)

        # 漫画形式
        url_s = "https://www.pixiv.net/artworks/24010650"
        expect = ["https://i.pximg.net/img-original/img/2011/12/30/23/52/44/24010650_p0.png",
                  "https://i.pximg.net/img-original/img/2011/12/30/23/52/44/24010650_p1.png",
                  "https://i.pximg.net/img-original/img/2011/12/30/23/52/44/24010650_p2.png",
                  "https://i.pximg.net/img-original/img/2011/12/30/23/52/44/24010650_p3.png",
                  "https://i.pximg.net/img-original/img/2011/12/30/23/52/44/24010650_p4.png"]
        actual = pa_cont.GetIllustURLs(url_s)
        self.assertEqual(expect, actual)

        # サフィックスエラー
        url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
        expect = []
        actual = pa_cont.GetIllustURLs(url_s)
        self.assertEqual(expect, actual)

        # 不正なイラストID
        url_s = "https://www.pixiv.net/artworks/00000000"
        expect = []
        actual = pa_cont.GetIllustURLs(url_s)
        self.assertEqual(expect, actual)

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        TEST_BASE_PATH = "./test/PG_Pixiv"
        url_s = "https://www.pixiv.net/artworks/24010650"
        expect = os.path.join(TEST_BASE_PATH, "./shift(149176)/フランの羽[アイコン用](24010650)/")

        # （想定）保存先ディレクトリが存在する場合は削除する
        if os.path.exists(expect):
            shutil.rmtree(expect)

        # 保存先ディレクトリが存在しない場合の実行
        actual = pa_cont.MakeSaveDirectoryPath(url_s, TEST_BASE_PATH)
        self.assertEqual(expect, actual)

        # 保存先ディレクトリを作成する
        os.makedirs(actual, exist_ok=True)

        # 保存先ディレクトリが存在する場合の実行
        actual = pa_cont.MakeSaveDirectoryPath(url_s, TEST_BASE_PATH)
        self.assertEqual(expect, actual)

        # 保存先ディレクトリを削除する
        if os.path.exists(TEST_BASE_PATH):
            shutil.rmtree(TEST_BASE_PATH)

        # サフィックスエラー
        url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
        expect = ""
        actual = pa_cont.MakeSaveDirectoryPath(url_s, TEST_BASE_PATH)
        self.assertEqual(expect, actual)

        # 不正なイラストID
        url_s = "https://www.pixiv.net/artworks/00000000"
        expect = ""
        actual = pa_cont.MakeSaveDirectoryPath(url_s, TEST_BASE_PATH)
        self.assertEqual(expect, actual)

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLする
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        TEST_BASE_PATH = "./test/PG_Pixiv"

        work_url_s = "https://www.pixiv.net/artworks/24010650"
        urls_s = pa_cont.GetIllustURLs(work_url_s)
        save_directory_path_s = pa_cont.MakeSaveDirectoryPath(work_url_s, TEST_BASE_PATH)

        # テスト用ディレクトリが存在する場合は削除する
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if os.path.exists(TEST_BASE_PATH):
            shutil.rmtree(TEST_BASE_PATH)

        # 一枚絵
        # 予想される保存先ディレクトリとファイル名を取得
        save_directory_path_cache = save_directory_path_s
        head_s, tail_s = os.path.split(save_directory_path_cache[:-1])
        save_directory_path_cache = head_s + "/"

        url_s = urls_s[0]
        root_s, ext_s = os.path.splitext(url_s)
        name_s = "{}{}".format(tail_s, ext_s)

        with ExitStack() as stack:
            mockgu = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.DownloadUgoira"))

            # 1回目の実行
            res = pa_cont.DownloadIllusts([url_s], save_directory_path_s)
            self.assertEqual(0, res)  # 新規DL成功想定（実際にDLする）
            mockgu.assert_called_once()
            mockgu.reset_mock()

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(os.path.exists(TEST_BASE_PATH))
            self.assertTrue(os.path.exists(save_directory_path_cache))
            self.assertTrue(os.path.exists(os.path.join(save_directory_path_cache, name_s)))

            # 2回目の実行
            res = pa_cont.DownloadIllusts([url_s], save_directory_path_s)
            self.assertEqual(1, res)  # 2回目は既にDL済なのでスキップされる想定
            mockgu.assert_not_called()
            mockgu.reset_mock()

        # 漫画形式
        # 予想される保存先ディレクトリとファイル名を取得
        save_directory_path_cache = save_directory_path_s
        dirname_s = os.path.basename(os.path.dirname(save_directory_path_s))
        head_s, tail_s = os.path.split(save_directory_path_s[:-1])
        save_directory_path_cache = head_s + "/"
        self.assertEqual(os.path.join(save_directory_path_cache, dirname_s), save_directory_path_s[:-1])

        expect_names = []
        for i, url_s in enumerate(urls_s):
            root_s, ext_s = os.path.splitext(url_s)
            name_s = "{:03}{}".format(i + 1, ext_s)
            expect_names.append(name_s)

        with ExitStack() as stack:
            mockgu = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.DownloadUgoira"))

            # 1回目の実行
            res = pa_cont.DownloadIllusts(urls_s, save_directory_path_s)
            self.assertEqual(0, res)  # 新規DL成功想定（実際にDLする）
            mockgu.assert_not_called()
            mockgu.reset_mock()

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(os.path.exists(TEST_BASE_PATH))
            self.assertTrue(os.path.exists(save_directory_path_cache))
            self.assertTrue(os.path.exists(os.path.join(save_directory_path_cache, dirname_s)))
            self.assertTrue(os.path.exists(save_directory_path_s))
            for name_s in expect_names:
                expect_path = os.path.join(save_directory_path_s, name_s)
                self.assertTrue(os.path.exists(expect_path))

            # 2回目の実行
            res = pa_cont.DownloadIllusts(urls_s, save_directory_path_s)
            self.assertEqual(1, res)  # 2回目は既にDL済なのでスキップされる想定
            mockgu.assert_not_called()
            mockgu.reset_mock()

        # urls指定エラー（空リスト）
        res = pa_cont.DownloadIllusts([], save_directory_path_s)
        self.assertEqual(-1, res)

        # 後始末：テスト用ディレクトリを削除する
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if os.path.exists(TEST_BASE_PATH):
            shutil.rmtree(TEST_BASE_PATH)

    def test_DownloadUgoira(self):
        """うごイラをダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLする
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        TEST_BASE_PATH = "./test/PG_Pixiv"

        # テスト用ディレクトリが存在する場合は削除する
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if os.path.exists(TEST_BASE_PATH):
            shutil.rmtree(TEST_BASE_PATH)

        # サンプル画像：おみくじ(86704541)
        work_url_s = "https://www.pixiv.net/artworks/86704541"
        illust_id_s = pa_cont.GetIllustId(work_url_s)
        expect_path = os.path.join(TEST_BASE_PATH, "おみくじ(86704541)")
        expect_gif_path = expect_path + ".gif"
        EXPECT_FRAME_NUM = 14
        expect_frames = [os.path.join(expect_path, "{}_ugoira{}.jpg".format(illust_id_s, i)) for i in range(0, EXPECT_FRAME_NUM)]

        # うごイラDL
        res = pa_cont.DownloadUgoira(illust_id_s, TEST_BASE_PATH)

        # DL後のディレクトリ構成とファイルの存在チェック
        self.assertTrue(os.path.exists(TEST_BASE_PATH))
        self.assertTrue(os.path.exists(expect_path))
        self.assertTrue(os.path.exists(expect_gif_path))

        # frameのDLをチェック
        actual_frames = glob.glob(os.path.join(expect_path + "/*"))
        actual_frames.sort(key=os.path.getmtime, reverse=False)
        self.assertEqual(len(expect_frames), len(actual_frames))
        self.assertEqual(expect_frames, actual_frames)

        # 後始末：テスト用ディレクトリを削除する
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if os.path.exists(TEST_BASE_PATH):
            shutil.rmtree(TEST_BASE_PATH)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
