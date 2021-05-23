# coding: utf-8
import configparser
import random
import shutil
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, PropertyMock, mock_open, patch
from pathlib import Path
from time import sleep

from PictureGathering import LSPixiv


logger = getLogger("root")
logger.setLevel(WARNING)


class TestLSPixiv(unittest.TestCase):

    def setUp(self):
        """コンフィグファイルからパスワードを取得する
        """
        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.username = config["pixiv"]["username"]
        self.password = config["pixiv"]["password"]

        self.TEST_BASE_PATH = "./test/PG_Pixiv"
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
        idstr = str(illust_id)
        url_base = {
            "59580629": "https://i.pximg.net/img-original/img/2016/10/22/10/11/37/{}_p0.jpg",
            "24010650": "https://i.pximg.net/img-original/img/2011/12/30/23/52/44/{}_p{}.png",
            "86704541": "https://.../{}_ugoira{}.jpg"
        }
        cols = ["id", "type", "is_manga", "author_name", "author_id", "title", "image_url", "image_urls"]
        data = {
            "59580629": [59580629, "illust", False, "author_name", 0, "title",
                         url_base["59580629"].format(illust_id), []],
            "24010650": [24010650, "illust", True, "shift", 149176, "フランの羽[アイコン用]",
                         "", [url_base["24010650"].format(illust_id, i) for i in range(5)]],
            "86704541": [86704541, "ugoira", False, "author_name", 0, "おみくじ",
                         url_base["86704541"].format(illust_id, 0), [url_base["86704541"].format(illust_id, i) for i in range(14)]]
        }
        res = {}
        for c, d in zip(cols, data[idstr]):
            res[c] = d
        return res

    def __MakePublicApiMock(self) -> MagicMock:
        """非公式pixivAPIの全体操作機能のモックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            api_response
                access_token
                works[0]
                    type
                    is_manga
                    user
                        name
                        is
                    metadata
                        pages[]
                            image_urls
                                large
                    image_urls
                        large

        Returns:
            MagicMock: api_response
        """
        def ReturnWorks(illust_id):
            r_works = MagicMock()
            s = {}
            if 0 < illust_id and illust_id < 99999999:
                type(r_works).status = "success"
                s = self.__GetIllustData(illust_id)
            else:
                type(r_works).status = "failed"

            def ReturnResponse():
                r_response = MagicMock()

                # イラストデータ設定
                type(r_response).type = s["type"]
                type(r_response).is_manga = s["is_manga"]
                type(r_response).title = s["title"]

                r_name_id = MagicMock()
                type(r_name_id).name = s["author_name"]
                type(r_name_id).id = s["author_id"]

                type(r_response).user = r_name_id

                def ReturnLarge(url):
                    r_large = MagicMock()
                    type(r_large).large = url
                    return r_large

                def ReturnImageurls(url):
                    r_imageurls = MagicMock()
                    type(r_imageurls).image_urls = ReturnLarge(url)
                    return r_imageurls

                def ReturnPages():
                    r_pages = MagicMock()
                    # 漫画形式のreturn_value設定
                    type(r_pages).pages = [ReturnImageurls(url) for url in s["image_urls"]]
                    return r_pages

                type(r_response).metadata = ReturnPages()

                # 一枚絵のreturn_value設定
                type(r_response).image_urls = ReturnLarge(s["image_url"])

                return r_response

            p_response = PropertyMock()
            p_response.side_effect = lambda: [ReturnResponse()]
            type(r_works).response = p_response

            return r_works

        api_response = MagicMock()
        p_works = PropertyMock()
        p_works.return_value = ReturnWorks
        type(api_response).works = p_works
        type(api_response).access_token = "ok"

        return api_response

    def __MakeAppApiMock(self) -> MagicMock:
        """非公式pixivAPIの詳細操作機能のモックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            aapi_response
                access_token
                download(url, path, name="")
                illust_detail(illust_id)
                    illust
                        meta_single_page
                            original_image_url
                ugoira_metadata(illust_id)
                    ugoira_metadata
                        frames[]

        Returns:
            MagicMock: aapi_response
        """
        aapi_response = MagicMock()
        type(aapi_response).access_token = "ok"

        def ReturnDownload(url, path, name=""):
            if name == "":
                name = Path(url).name
            # ダミーファイルをダウンロードしたことにしてpathに生成する
            with (Path(path) / name).open("wb") as fout:
                fout.write(url.encode())

            # DLには多少時間がかかる想定
            sleep(0.01)

        p_download = PropertyMock()
        p_download.return_value = ReturnDownload
        type(aapi_response).download = p_download

        def ReturnIllustDetail(illust_id):
            s = {}
            if 0 < illust_id and illust_id < 99999999:
                s = self.__GetIllustData(illust_id)

            r_original_image_url = MagicMock()
            type(r_original_image_url).original_image_url = s["image_url"]

            r_meta_single_page = MagicMock()
            type(r_meta_single_page).meta_single_page = r_original_image_url

            r_illust = MagicMock()
            type(r_illust).illust = r_meta_single_page

            return r_illust

        p_illust_detail = PropertyMock()
        p_illust_detail.return_value = ReturnIllustDetail
        type(aapi_response).illust_detail = p_illust_detail

        def ReturnUgoiraMetadata(illust_id):
            s = {}
            if 0 < illust_id and illust_id < 99999999:
                s = self.__GetIllustData(illust_id)

            frames_len = len(s["image_urls"])
            DEFAULT_DELAY = 30
            frames = [{"delay": DEFAULT_DELAY} for i in range(frames_len)]

            r_frames = MagicMock()
            type(r_frames).frames = frames

            r_ugoira_metadata2 = MagicMock()
            type(r_ugoira_metadata2).ugoira_metadata = r_frames

            return r_ugoira_metadata2

        p_ugoira_metadata = PropertyMock()
        p_ugoira_metadata.return_value = ReturnUgoiraMetadata
        type(aapi_response).ugoira_metadata = p_ugoira_metadata

        return aapi_response

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        """非公式pixivAPIのログイン機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.LSPixiv.LSPixiv.Login" にpatchする

        Returns:
            MagicMock: ログイン機能のside_effectを持つモック
        """
        def LoginSideeffect(username, password):
            if self.username == username and self.password == password:
                api_response = self.__MakePublicApiMock()
                aapi_response = self.__MakeAppApiMock()

                return (api_response, aapi_response, True)
            else:
                return (None, None, False)

        mock.side_effect = LoginSideeffect
        return mock

    def __MakeImageMock(self, mock: MagicMock) -> MagicMock:
        """PIL.Imageクラスのモックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            mock
                open(path)
                    copy()
                    save(fp, save_all, append_images, optimize, duration, loop)

        Returns:
            MagicMock: PIL.Imageクラスのモック
        """
        def ReturnOpen(path):
            r_open = MagicMock()
            p_copy = PropertyMock()
            p_copy.return_value = lambda: ReturnOpen(path)
            type(r_open).copy = p_copy

            def ReturnSave(fp, save_all, append_images, optimize, duration, loop):
                path_list = []
                for image in append_images:
                    path_list.append(image.return_value)
                
                # gifファイルを生成したことにしてダミーをfpに生成する
                with Path(fp).open("wb") as fout:
                    fout.write(fp.encode())
                    fout.write(", ".join(path_list).encode())
                    fout.write(", ".join(map(str, duration)).encode())

            p_save = PropertyMock()
            p_save.return_value = ReturnSave
            type(r_open).save = p_save

            r_open.return_value = path
            return r_open

        p_open = PropertyMock()
        p_open.return_value = ReturnOpen
        type(mock).open = p_open
        return mock
    
    def test_LSPixiv(self):
        """非公式pixivAPI利用クラス初期状態チェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)

            # 正常系
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)
            self.assertIsNotNone(lsp_cont.api)
            self.assertIsNotNone(lsp_cont.aapi)
            self.assertTrue(lsp_cont.auth_success)
            self.assertIsNotNone(lsp_cont.api.access_token)
            self.assertIsNotNone(lsp_cont.aapi.access_token)

            # 異常系
            with self.assertRaises(SystemExit):
                lsp_cont = LSPixiv.LSPixiv("invalid user", "invalid password", self.TEST_BASE_PATH)

    def test_Login(self):
        """非公式pixivAPIインスタンス生成とログインをチェック
        """
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
            p_auth.side_effect = lambda refresh_token: refresh_token
            type(response).auth = p_auth

            p_login = MagicMock()
            p_login.side_effect = lambda username, password: (username, password)
            type(response).login = p_login
            return response

        with ExitStack() as stack:
            # open()をモックに置き換える
            mockfout = mock_open()
            mockfp = stack.enter_context(patch("pathlib.Path.open", mockfout))

            # mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpapub = stack.enter_context(patch("PictureGathering.LSPixiv.PixivAPI"))
            mockpaapp = stack.enter_context(patch("PictureGathering.LSPixiv.AppPixivAPI"))

            mockpapub.side_effect = lambda: response_factory("ok_access_token", "ok_refresh_token")
            mockpaapp.side_effect = lambda: response_factory("ok_access_token", "ok_refresh_token")

            # refresh_tokenファイルが存在する場合、一時的にリネームする
            REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
            rt_path = Path(REFRESH_TOKEN_PATH)
            tmp_path = rt_path.parent / "tmp.ini"
            if rt_path.is_file():
                rt_path.rename(tmp_path)

            # refresh_tokenファイルが存在しない場合のテスト
            # 現在は新規ログインはできないため常に失敗する
            with self.assertRaises(SystemExit):
                expect = (mockpapub.side_effect(), mockpaapp.side_effect(), True)
                # インスタンス生成時にLoginが呼ばれる
                lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)
                actual = (lsp_cont.api, lsp_cont.aapi, lsp_cont.auth_success)

                self.assertEqual(mockpapub.call_count, 1)
                self.assertEqual(mockpaapp.call_count, 1)
                self.assertEqual(expect[2], actual[2])
            mockpapub.reset_mock()
            mockpaapp.reset_mock()

            # 一時的にリネームしていた場合は復元する
            # そうでない場合はダミーのファイルを作っておく
            if tmp_path.is_file():
                tmp_path.rename(rt_path)
            else:
                rt_path.touch()

            # refresh_tokenファイルが存在する場合のテスト
            expect = (mockpapub.side_effect(), mockpaapp.side_effect(), True)
            # インスタンス生成時にLoginが呼ばれる
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)
            actual = (lsp_cont.api, lsp_cont.aapi, lsp_cont.auth_success)

            self.assertEqual(mockpapub.call_count, 1)
            self.assertEqual(mockpaapp.call_count, 1)
            self.assertEqual(expect[2], actual[2])
            mockpapub.reset_mock()
            mockpaapp.reset_mock()

            # ダミーファイルがある場合は削除しておく
            if not tmp_path.is_file() and rt_path.stat().st_size == 0:
                rt_path.unlink()

    def test_IsTargetUrl(self):
        """URLがpixivのURLかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)

            # 正常系
            url_s = "https://www.pixiv.net/artworks/24010650"
            self.assertEqual(True, lsp_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            self.assertEqual(False, lsp_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(nijie)
            url_s = "http://nijie.info/view.php?id=402197"
            self.assertEqual(False, lsp_cont.IsTargetUrl(url_s))

            # httpsでなくhttp
            url_s = "http://www.pixiv.net/artworks/24010650"
            self.assertEqual(False, lsp_cont.IsTargetUrl(url_s))

            # pixivの別ページ
            url_s = "https://www.pixiv.net/bookmark_new_illust.php"
            self.assertEqual(False, lsp_cont.IsTargetUrl(url_s))

            # プリフィックスエラー
            url_s = "ftp:https://www.pixiv.net/artworks/24010650"
            self.assertEqual(False, lsp_cont.IsTargetUrl(url_s))

            # サフィックスエラー
            url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
            self.assertEqual(False, lsp_cont.IsTargetUrl(url_s))

    def test_GetIllustId(self):
        """pixiv作品ページURLからイラストIDを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)

            # 正常系
            r = "{:0>8}".format(random.randint(0, 99999999))
            url_s = "https://www.pixiv.net/artworks/" + r
            expect = int(r)
            actual = lsp_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "https://www.pixiv.net/artworks/{}?rank=1".format(r)
            expect = -1
            actual = lsp_cont.GetIllustId(url_s)
            self.assertEqual(expect, actual)

    def test_GetIllustURLs(self):
        """pixiv作品ページURLからイラストへの直リンクを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)

            # 一枚絵
            url_s = "https://www.pixiv.net/artworks/59580629"
            expect = ["https://i.pximg.net/img-original/img/2016/10/22/10/11/37/59580629_p0.jpg"]
            actual = lsp_cont.GetIllustURLs(url_s)
            self.assertEqual(expect, actual)

            # 漫画形式
            url_s = "https://www.pixiv.net/artworks/24010650"
            expect = ["https://i.pximg.net/img-original/img/2011/12/30/23/52/44/24010650_p{}.png".format(i) for i in range(5)]
            actual = lsp_cont.GetIllustURLs(url_s)
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
            expect = []
            actual = lsp_cont.GetIllustURLs(url_s)
            self.assertEqual(expect, actual)

            # 不正なイラストID
            url_s = "https://www.pixiv.net/artworks/00000000"
            expect = []
            actual = lsp_cont.GetIllustURLs(url_s)
            self.assertEqual(expect, actual)

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)

            url_s = "https://www.pixiv.net/artworks/24010650"
            expect = Path(self.TEST_BASE_PATH) / "./shift(149176)/フランの羽[アイコン用](24010650)/"

            # 想定保存先ディレクトリが存在する場合は削除する
            if expect.is_dir():
                shutil.rmtree(expect)

            # 保存先ディレクトリが存在しない場合の実行
            actual = Path(lsp_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))
            self.assertEqual(expect, actual)

            # 保存先ディレクトリを作成する
            actual.mkdir(parents=True, exist_ok=True)

            # 保存先ディレクトリが存在する場合の実行
            actual = Path(lsp_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "https://www.pixiv.net/artworks/24010650?rank=1"
            expect = ""
            actual = lsp_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH)
            self.assertEqual(expect, actual)

            # 不正なイラストID
            url_s = "https://www.pixiv.net/artworks/00000000"
            expect = ""
            actual = lsp_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH)
            self.assertEqual(expect, actual)

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLはしない
        """
        with ExitStack() as stack:
            mockgu = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.DownloadUgoira"))
            mocksleep = stack.enter_context(patch("PictureGathering.LSPixiv.sleep"))
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)

            work_url_s = "https://www.pixiv.net/artworks/24010650"
            urls_s = lsp_cont.GetIllustURLs(work_url_s)
            save_directory_path_s = Path(lsp_cont.MakeSaveDirectoryPath(work_url_s, self.TEST_BASE_PATH))

            # 一枚絵
            # 予想される保存先ディレクトリとファイル名を取得
            save_directory_path_cache = save_directory_path_s.parent
            url_s = urls_s[0]
            name_s = "{}{}".format(save_directory_path_s.name, Path(url_s).suffix)

            # 1回目の実行
            res = lsp_cont.DownloadIllusts([url_s], str(save_directory_path_s))
            self.assertEqual(0, res)  # 新規DL成功想定（実際にDLする）
            mockgu.assert_called_once()
            mockgu.reset_mock()

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(self.TBP.is_dir())
            self.assertTrue(save_directory_path_cache.is_dir())
            self.assertTrue((save_directory_path_cache / name_s).is_file())

            # 2回目の実行
            res = lsp_cont.DownloadIllusts([url_s], str(save_directory_path_s))
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

            # 1回目の実行
            res = lsp_cont.DownloadIllusts(urls_s, str(save_directory_path_s))
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
            res = lsp_cont.DownloadIllusts(urls_s, str(save_directory_path_s))
            self.assertEqual(1, res)  # 2回目は既にDL済なのでスキップされる想定
            mockgu.assert_not_called()
            mockgu.reset_mock()

            # urls指定エラー（空リスト）
            res = lsp_cont.DownloadIllusts([], str(save_directory_path_s))
            self.assertEqual(-1, res)

    def test_DownloadUgoira(self):
        """うごイラをダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLはしない
        """
        with ExitStack() as stack:
            mocksleep = stack.enter_context(patch("PictureGathering.LSPixiv.sleep"))
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixiv.LSPixiv.Login"))
            mockimage = stack.enter_context(patch("PictureGathering.LSPixiv.Image"))

            mockpalogin = self.__MakeLoginMock(mockpalogin)
            mockimage = self.__MakeImageMock(mockimage)

            lsp_cont = LSPixiv.LSPixiv(self.username, self.password, self.TEST_BASE_PATH)

            # サンプル画像：おみくじ(86704541)
            work_url_s = "https://www.pixiv.net/artworks/86704541"
            illust_id_s = lsp_cont.GetIllustId(work_url_s)
            expect_path = self.TBP / "おみくじ(86704541)"
            expect_gif_path = expect_path.parent / "{}{}".format(expect_path.name, ".gif")
            EXPECT_FRAME_NUM = 14
            expect_frames = [str(expect_path / "{}_ugoira{}.jpg".format(illust_id_s, i)) for i in range(0, EXPECT_FRAME_NUM)]

            # うごイラDL
            res = lsp_cont.DownloadUgoira(illust_id_s, self.TEST_BASE_PATH)

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

            # うごイラでないイラストIDを入力
            work_url_s = "https://www.pixiv.net/artworks/24010650"
            illust_id_s = lsp_cont.GetIllustId(work_url_s)
            res = lsp_cont.DownloadUgoira(illust_id_s, self.TEST_BASE_PATH)
            self.assertEqual(1, res)  # うごイラではなかった

            # 不正なイラストIDを入力
            work_url_s = "https://www.pixiv.net/artworks/00000000"
            illust_id_s = lsp_cont.GetIllustId(work_url_s)
            res = lsp_cont.DownloadUgoira(illust_id_s, self.TEST_BASE_PATH)
            self.assertEqual(-1, res)  # 不正なイラストID


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
