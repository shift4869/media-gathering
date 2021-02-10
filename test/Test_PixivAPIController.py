# coding: utf-8
import configparser
import random
import re
import shutil
import sys
import unittest
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, PropertyMock, mock_open, patch
from pathlib import Path

from PictureGathering import PixivAPIController


logger = getLogger("root")
logger.setLevel(WARNING)


class TestPixivAPIController(unittest.TestCase):

    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)

        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.username = config["pixiv"]["username"]
        self.password = config["pixiv"]["password"]

        self.TEST_BASE_PATH = "./test/PG_Pixiv"
        self.TBP = Path(self.TEST_BASE_PATH)

    def tearDown(self):
        # 後始末：テスト用ディレクトリを削除する
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if self.TBP.is_dir():
            shutil.rmtree(self.TBP)

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        def LoginSideeffect(username, password):
            if self.username == username and self.password == password:
                def ReturnWorks(illust_id):
                    r_works = MagicMock()
                    p_status = PropertyMock()
                    if 0 < illust_id and illust_id < 99999999:
                        p_status.return_value = "success"
                    else:
                        p_status.return_value = "failed"
                    type(r_works).status = p_status

                    def ReturnResponse():
                        r_response = MagicMock()
                        p_is_manga = PropertyMock()

                        # マンガ形式かどうかの判定
                        is_manga = False
                        if str(illust_id) == "59580629":
                            is_manga = False
                        elif str(illust_id) == "24010650":
                            is_manga = True

                        p_is_manga.return_value = is_manga
                        type(r_response).is_manga = p_is_manga

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
                            res = []
                            if str(illust_id) == "24010650":
                                url_base = "https://i.pximg.net/img-original/img/2011/12/30/23/52/44/{}_p{}.png"
                                urls = [url_base.format(illust_id, i) for i in range(5)]
                                res = [ReturnImageurls(url) for url in urls]

                            p_pages.return_value = res
                            type(r_pages).pages = p_pages
                            return r_pages

                        p_metadata = PropertyMock()
                        p_metadata.return_value = ReturnPages()
                        type(r_response).metadata = p_metadata

                        # 一枚絵のreturn_value設定
                        url = ""
                        if str(illust_id) == "59580629":
                            url = "https://i.pximg.net/img-original/img/2016/10/22/10/11/37/{}_p0.jpg".format(illust_id)

                        p_image_urls = PropertyMock()
                        p_image_urls.return_value = ReturnLarge(url)
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

                aapi_response = MagicMock()
                p_access_token = PropertyMock()
                p_access_token.return_value = "ok"
                type(aapi_response).access_token = p_access_token

                return (api_response, aapi_response, True)
            else:
                return (None, None, False)

        mock.side_effect = LoginSideeffect
        return mock

    def test_PixivAPIController(self):
        """非公式pixivAPI利用クラス初期状態チェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)

            self.assertIsNotNone(pa_cont.api)
            self.assertIsNotNone(pa_cont.aapi)
            self.assertTrue(pa_cont.auth_success)
            self.assertIsNotNone(pa_cont.api.access_token)
            self.assertIsNotNone(pa_cont.aapi.access_token)

    def test_Login(self):
        """非公式pixivAPIインスタンス生成とログインをチェック
        """
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
            return response_factory("ok_access_token", "ok_refresh_token")

        with ExitStack() as stack:
            # open()をモックに置き換える
            mockfout = mock_open()
            mockfp = stack.enter_context(patch("PictureGathering.PixivAPIController.open", mockfout))

            # mockpalogin = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.Login"))
            mockpapub = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPI"))
            mockpaapp = stack.enter_context(patch("PictureGathering.PixivAPIController.AppPixivAPI"))

            mockpapub.side_effect = api_side_effect
            mockpaapp.side_effect = api_side_effect

            expect = (mockpapub.side_effect(), mockpaapp.side_effect(), True)
            # インスタンス生成時にLoginが呼ばれる
            pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
            actual = (pa_cont.api, pa_cont.aapi, pa_cont.auth_success)

            self.assertEqual(mockpapub.call_count, 1)
            self.assertEqual(mockpaapp.call_count, 1)
            self.assertEqual(expect[2], actual[2])

            # TODO::refresh_tokenの有無によって分岐

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
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
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
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
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
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)

            url_s = "https://www.pixiv.net/artworks/24010650"
            expect = Path(self.TEST_BASE_PATH) / "./shift(149176)/フランの羽[アイコン用](24010650)/"

            # 想定保存先ディレクトリが存在する場合は削除する
            if expect.is_dir():
                shutil.rmtree(expect)

            # 保存先ディレクトリが存在しない場合の実行
            actual = Path(pa_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))
            self.assertEqual(expect, actual)

            # 保存先ディレクトリを作成する
            actual.mkdir(parents=True, exist_ok=True)

            # 保存先ディレクトリが存在する場合の実行
            actual = Path(pa_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
            expect = ""
            actual = pa_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH)
            self.assertEqual(expect, actual)

            # 不正なイラストID
            url_s = "https://www.pixiv.net/artworks/00000000"
            expect = ""
            actual = pa_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH)
            self.assertEqual(expect, actual)

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLする
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)
        work_url_s = "https://www.pixiv.net/artworks/24010650"
        urls_s = pa_cont.GetIllustURLs(work_url_s)
        save_directory_path_s = Path(pa_cont.MakeSaveDirectoryPath(work_url_s, self.TEST_BASE_PATH))

        # 一枚絵
        # 予想される保存先ディレクトリとファイル名を取得
        save_directory_path_cache = save_directory_path_s.parent
        url_s = urls_s[0]
        name_s = "{}{}".format(save_directory_path_s.name, Path(url_s).suffix)

        with ExitStack() as stack:
            mockgu = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.DownloadUgoira"))

            # 1回目の実行
            res = pa_cont.DownloadIllusts([url_s], str(save_directory_path_s))
            self.assertEqual(0, res)  # 新規DL成功想定（実際にDLする）
            mockgu.assert_called_once()
            mockgu.reset_mock()

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(self.TBP.is_dir())
            self.assertTrue(save_directory_path_cache.is_dir())
            self.assertTrue((save_directory_path_cache / name_s).is_file())

            # 2回目の実行
            res = pa_cont.DownloadIllusts([url_s], str(save_directory_path_s))
            self.assertEqual(1, res)  # 2回目は既にDL済なのでスキップされる想定
            mockgu.assert_not_called()
            mockgu.reset_mock()

        # 漫画形式
        # 予想される保存先ディレクトリとファイル名を取得
        save_directory_path_cache = save_directory_path_s.parent
        dirname_s = save_directory_path_s.name
        self.assertEqual((save_directory_path_cache / dirname_s), save_directory_path_s)

        expect_names = []
        for i, url_s in enumerate(urls_s):
            name_s = "{:03}{}".format(i + 1, Path(url_s).suffix)
            expect_names.append(name_s)

        with ExitStack() as stack:
            mockgu = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.DownloadUgoira"))

            # 1回目の実行
            res = pa_cont.DownloadIllusts(urls_s, str(save_directory_path_s))
            self.assertEqual(0, res)  # 新規DL成功想定（実際にDLする）
            mockgu.assert_not_called()
            mockgu.reset_mock()

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(self.TBP.is_dir())
            self.assertTrue(save_directory_path_cache.is_dir())
            self.assertTrue((save_directory_path_cache / dirname_s).is_dir())
            self.assertTrue(save_directory_path_s.is_dir())
            for name_s in expect_names:
                self.assertTrue((save_directory_path_s / name_s).is_file())

            # 2回目の実行
            res = pa_cont.DownloadIllusts(urls_s, str(save_directory_path_s))
            self.assertEqual(1, res)  # 2回目は既にDL済なのでスキップされる想定
            mockgu.assert_not_called()
            mockgu.reset_mock()

        # urls指定エラー（空リスト）
        res = pa_cont.DownloadIllusts([], str(save_directory_path_s))
        self.assertEqual(-1, res)

    def test_DownloadUgoira(self):
        """うごイラをダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLする
        """
        pa_cont = PixivAPIController.PixivAPIController(self.username, self.password)

        # サンプル画像：おみくじ(86704541)
        work_url_s = "https://www.pixiv.net/artworks/86704541"
        illust_id_s = pa_cont.GetIllustId(work_url_s)
        expect_path = self.TBP / "おみくじ(86704541)"
        expect_gif_path = expect_path.parent / "{}{}".format(expect_path.name, ".gif")
        EXPECT_FRAME_NUM = 14
        expect_frames = [str(expect_path / "{}_ugoira{}.jpg".format(illust_id_s, i)) for i in range(0, EXPECT_FRAME_NUM)]

        # うごイラDL
        res = pa_cont.DownloadUgoira(illust_id_s, self.TEST_BASE_PATH)

        # DL後のディレクトリ構成とファイルの存在チェック
        self.assertTrue(self.TBP.is_dir())
        self.assertTrue(expect_path.is_dir())
        self.assertTrue(expect_gif_path.is_file())

        # frameのDLをチェック
        actual_frames = []
        af = [(sp.stat().st_mtime, str(sp)) for sp in expect_path.glob("**/*") if sp.is_file()]
        for mtime, path in sorted(af, reverse=False):
            actual_frames.append(path)
        self.assertEqual(len(expect_frames), len(actual_frames))
        self.assertEqual(expect_frames, actual_frames)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
