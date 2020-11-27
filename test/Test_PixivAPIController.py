# coding: utf-8
import configparser
import os
import re
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
        def responce_factory(access_token, refresh_token):
            responce = MagicMock()
            p_access_token = PropertyMock()
            p_access_token.return_value = access_token
            type(responce).access_token = p_access_token

            p_refresh_token = PropertyMock()
            p_refresh_token.return_value = refresh_token
            type(responce).refresh_token = p_access_token

            p_auth = MagicMock()
            p_auth.side_effect = auth_side_effect
            type(responce).auth = p_auth

            p_login = MagicMock()
            p_login.side_effect = login_side_effect
            type(responce).login = p_login
            return responce

        # インスタンス生成時のsideeffect(PixivAPI(), AppPixivAPI())
        def api_side_effect():
            return responce_factory(pa_cont.api.access_token, pa_cont.api.refresh_token)

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

        # refresh_tokenが既に存在しているなら削除
        REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
        if os.path.exists(REFRESH_TOKEN_PATH):
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
        expect = ""
        actual = ""
        self.assertEqual(expect, actual)

    def test_GetIllustId(self):
        """pixiv作品ページURLからイラストIDを取得する機能をチェック
        """
        expect = ""
        actual = ""
        self.assertEqual(expect, actual)

    def test_GetIllustURLs(self):
        """pixiv作品ページURLからイラストへの直リンクを取得する機能をチェック
        """
        expect = ""
        actual = ""
        self.assertEqual(expect, actual)

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        expect = ""
        actual = ""
        self.assertEqual(expect, actual)

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
        """
        expect = ""
        actual = ""
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
