# coding: utf-8
import configparser
import random
import shutil
import sys
import unittest
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
        """非公式nijieAPIの全体操作機能のモックを作成する

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

    def __MakeAppApiMock(self) -> MagicMock:
        """非公式nijieAPIの詳細操作機能のモックを作成する

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
        p_access_token = PropertyMock()
        p_access_token.return_value = "ok"
        type(aapi_response).access_token = p_access_token

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
            p_original_image_url = PropertyMock()
            p_original_image_url.return_value = s["image_url"]
            type(r_original_image_url).original_image_url = p_original_image_url

            r_meta_single_page = MagicMock()
            p_meta_single_page = PropertyMock()
            p_meta_single_page.return_value = r_original_image_url
            type(r_meta_single_page).meta_single_page = p_meta_single_page

            r_illust = MagicMock()
            p_illust = PropertyMock()
            p_illust.return_value = r_meta_single_page
            type(r_illust).illust = p_illust

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
            p_frames = PropertyMock()
            p_frames.return_value = frames
            type(r_frames).frames = p_frames

            r_ugoira_metadata2 = MagicMock()
            p_ugoira_metadata2 = PropertyMock()
            p_ugoira_metadata2.return_value = r_frames
            type(r_ugoira_metadata2).ugoira_metadata = p_ugoira_metadata2

            return r_ugoira_metadata2

        p_ugoira_metadata = PropertyMock()
        p_ugoira_metadata.return_value = ReturnUgoiraMetadata
        type(aapi_response).ugoira_metadata = p_ugoira_metadata

        return aapi_response

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        """非公式nijieAPIのログイン機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.NijieController.NijieController.Login" にpatchする

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

    
    def test_NijieController(self):
        """nijieページ取得初期状態チェック
        """
        pass

    def test_Login(self):
        """非公式nijieAPIインスタンス生成とログインをチェック
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
        return

        with ExitStack() as stack:
            # open()をモックに置き換える
            mockfout = mock_open()
            mockfp = stack.enter_context(patch("pathlib.Path.open", mockfout))

            # mockpalogin = stack.enter_context(patch("PictureGathering.NijieController.NijieController.Login"))
            mockpapub = stack.enter_context(patch("PictureGathering.NijieController.NijieAPI"))
            mockpaapp = stack.enter_context(patch("PictureGathering.NijieController.AppNijieAPI"))

            mockpapub.side_effect = lambda: response_factory("ok_access_token", "ok_refresh_token")
            mockpaapp.side_effect = lambda: response_factory("ok_access_token", "ok_refresh_token")

            # refresh_tokenファイルが存在する場合、一時的にリネームする
            REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
            rt_path = Path(REFRESH_TOKEN_PATH)
            tmp_path = rt_path.parent / "tmp.ini"
            if rt_path.is_file():
                rt_path.rename(tmp_path)

            # refresh_tokenファイルが存在しない場合のテスト
            expect = (mockpapub.side_effect(), mockpaapp.side_effect(), True)
            # インスタンス生成時にLoginが呼ばれる
            pa_cont = NijieController.NijieController(self.username, self.password)
            actual = (pa_cont.api, pa_cont.aapi, pa_cont.auth_success)

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
            pa_cont = NijieController.NijieController(self.username, self.password)
            actual = (pa_cont.api, pa_cont.aapi, pa_cont.auth_success)

            self.assertEqual(mockpapub.call_count, 1)
            self.assertEqual(mockpaapp.call_count, 1)
            self.assertEqual(expect[2], actual[2])
            mockpapub.reset_mock()
            mockpaapp.reset_mock()

            # ダミーファイルがある場合は削除しておく
            if not tmp_path.is_file() and rt_path.stat().st_size == 0:
                rt_path.unlink()

    def test_IsNijieURL(self):
        """nijieのURLかどうか判定する機能をチェック
        """
        # クラスメソッドなのでインスタンス無しで呼べる
        IsNijieURL = NijieScraping.NijieController.IsNijieURL
        
        # 正常系
        # url_s = "https://www.nijie.net/artworks/24010650"
        # self.assertEqual(True, IsNijieURL(url_s))

    def test_GetIllustId(self):
        """nijie作品ページURLからイラストIDを取得する機能をチェック
        """
        pass

    def test_GetIllustURLs(self):
        """nijie作品ページURLからイラストへの直リンクを取得する機能をチェック
        """
        pass

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        pass

    def test_DownloadIllusts(self):
        """イラストをダウンロードする機能をチェック
        """
        pass

    def test_DownloadUgoira(self):
        """うごイラをダウンロードする機能をチェック
        """
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
