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

from bs4 import BeautifulSoup

from PictureGathering import LSPixivNovel


logger = getLogger("root")
logger.setLevel(WARNING)


class TestLSPixivNovel(unittest.TestCase):

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

    def __GetNovelData(self, novel_id: int) -> dict:
        """テスト用のノベル情報を作成する

        Args:
            novel_id (int): ノベルID (0 < novel_id < 99999999)

        Returns:
            dict: ノベルIDで示されるノベル情報を表す辞書（キーはcolsを参照）
        """
        idstr = str(novel_id)
        url = f"https://www.pixiv.net/novel/show.php?id={idstr}"

        cols = ["id", "url", "author_name", "author_id", "title", "create_date", "page_count", "text_length", "caption", "text"]
        data = {
            "11111111": [11111111, url, "作者名1", 111111, "小説タイトル1", "2022-01-08T21:15:11+09:00",
                         1, 5, "caption1", "text1"]
        }
        res = {}
        for c, d in zip(cols, data[idstr]):
            res[c] = d
        return res

    def __ReturnNovelDetail(self, novel_id) -> MagicMock:
        """非公式pixivAPIの全体操作機能のモックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            novel
                id
                title
                create_date
                page_count
                text_length
                caption
                user
                    name
                    id
            error

        Returns:
            MagicMock: novel_response
        """
        novel_response = MagicMock()
        s = {}
        if 0 < novel_id and novel_id < 99999999:
            s = self.__GetNovelData(novel_id)
            type(novel_response).error = None
        else:
            type(novel_response).error = "error"
            type(novel_response).novel = None
            return novel_response

        def ReturnResponse():
            r_response = MagicMock()

            # ノベルデータ設定
            type(r_response).id = s["id"]
            type(r_response).title = s["title"]
            type(r_response).create_date = s["create_date"]
            type(r_response).page_count = int(s["page_count"])
            type(r_response).text_length = int(s["text_length"])
            type(r_response).caption = s["caption"]

            r_name_id = MagicMock()
            type(r_name_id).name = s["author_name"]
            type(r_name_id).id = s["author_id"]

            type(r_response).user = r_name_id

            return r_response

        p_response = PropertyMock()
        p_response.return_value = ReturnResponse()
        type(novel_response).novel = p_response

        return novel_response

    def __ReturnNovelText(self, novel_id) -> MagicMock:
        """非公式pixivAPIの全体操作機能のモックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            novel_text
                novel_text
            error

        Returns:
            MagicMock: novel_text_response
        """
        novel_text_response = MagicMock()
        s = {}
        if 0 < novel_id and novel_id < 99999999:
            s = self.__GetNovelData(novel_id)
            type(novel_text_response).error = None
        else:
            type(novel_text_response).error = "error"
            type(novel_text_response).novel = None
            return novel_text_response

        p_response = PropertyMock()
        p_response.return_value = s["text"]
        type(novel_text_response).novel_text = p_response

        return novel_text_response

    def __MakeAppApiMock(self) -> MagicMock:
        """非公式pixivAPIの詳細操作機能のモックを作成する

        Note:
            以下のプロパティ、メソッドを模倣する
            aapi_response
                access_token
                novel_detail(novel_id)
                    ※self.__ReturnNovelDetail参照
                novel_text(novel_id)
                    ※self.__ReturnNovelText参照

        Returns:
            MagicMock: aapi_response
        """
        aapi_response = MagicMock()
        type(aapi_response).access_token = "ok"

        p_novel_detail = PropertyMock()
        p_novel_detail.return_value = self.__ReturnNovelDetail
        type(aapi_response).novel_detail = p_novel_detail

        p_novel_text = PropertyMock()
        p_novel_text.return_value = self.__ReturnNovelText
        type(aapi_response).novel_text = p_novel_text

        return aapi_response

    def __MakeLoginMock(self, mock: MagicMock) -> MagicMock:
        """非公式pixivAPIのログイン機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "PictureGathering.LSPixivNovel.LSPixivNovel.Login" にpatchする

        Returns:
            MagicMock: ログイン機能のside_effectを持つモック
        """
        def LoginSideeffect(username, password):
            if self.username == username and self.password == password:
                aapi_response = self.__MakeAppApiMock()

                return (aapi_response, True)
            else:
                return (None, False)

        mock.side_effect = LoginSideeffect
        return mock

    def test_LSPixivNovel(self):
        """非公式pixivAPI利用クラス初期状態チェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixivNovel.LSPixivNovel.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)

            # 正常系
            lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)
            # self.assertIsNotNone(lspn_cont.api)
            self.assertIsNotNone(lspn_cont.aapi)
            self.assertTrue(lspn_cont.auth_success)
            # self.assertIsNotNone(lspn_cont.api.access_token)
            self.assertIsNotNone(lspn_cont.aapi.access_token)

            # 異常系
            with self.assertRaises(SystemExit):
                lspn_cont = LSPixivNovel.LSPixivNovel("invalid user", "invalid password", self.TEST_BASE_PATH)

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

            # mockpalogin = stack.enter_context(patch("PictureGathering.LSPixivNovel.LSPixivNovel.Login"))
            mockpaapp = stack.enter_context(patch("PictureGathering.LSPixivNovel.AppPixivAPI"))

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
                expect = (mockpaapp.side_effect(), True)
                # インスタンス生成時にLoginが呼ばれる
                lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)
                actual = (lspn_cont.aapi, lspn_cont.auth_success)

                self.assertEqual(mockpaapp.call_count, 1)
                self.assertEqual(expect[1], actual[1])
            mockpaapp.reset_mock()

            # 一時的にリネームしていた場合は復元する
            # そうでない場合はダミーのファイルを作っておく
            if tmp_path.is_file():
                tmp_path.rename(rt_path)
            else:
                rt_path.touch()

            # refresh_tokenファイルが存在する場合のテスト
            expect = (mockpaapp.side_effect(), True)
            # インスタンス生成時にLoginが呼ばれる
            lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)
            actual = (lspn_cont.aapi, lspn_cont.auth_success)

            self.assertEqual(mockpaapp.call_count, 1)
            self.assertEqual(expect[1], actual[1])
            mockpaapp.reset_mock()

            # ダミーファイルがある場合は削除しておく
            if not tmp_path.is_file() and rt_path.stat().st_size == 0:
                rt_path.unlink()

    def test_IsTargetUrl(self):
        """URLがpixivノベル作品のURLかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixivNovel.LSPixivNovel.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)

            # 正常系
            url_s = "https://www.pixiv.net/novel/show.php?id=3195243"
            self.assertEqual(True, lspn_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            self.assertEqual(False, lspn_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(nijie)
            url_s = "http://nijie.info/view.php?id=402197"
            self.assertEqual(False, lspn_cont.IsTargetUrl(url_s))

            # httpsでなくhttp
            url_s = "http://www.pixiv.net/novel/show.php?id=3195243"
            self.assertEqual(False, lspn_cont.IsTargetUrl(url_s))

            # pixivの別ページ
            url_s = "https://www.pixiv.net/bookmark_new_novel.php"
            self.assertEqual(False, lspn_cont.IsTargetUrl(url_s))

            # プリフィックスエラー
            url_s = "ftp:https://www.pixiv.net/novel/show.php?id=3195243"
            self.assertEqual(False, lspn_cont.IsTargetUrl(url_s))

            # サフィックスエラー
            url_s = "https://www.pixiv.net/novel/show.php?id=3195243&rank=1"
            self.assertEqual(False, lspn_cont.IsTargetUrl(url_s))

    def test_GetNovelId(self):
        """pixiv作品ページURLからノベルIDを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixivNovel.LSPixivNovel.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)

            # 正常系
            r = "{:0>8}".format(random.randint(0, 99999999))
            url_s = f"https://www.pixiv.net/novel/show.php?id={r}"
            expect = int(r)
            actual = lspn_cont.GetNovelId(url_s)
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = f"https://www.pixiv.net/novel/show.php?id={r}?rank=1"
            expect = -1
            actual = lspn_cont.GetNovelId(url_s)
            self.assertEqual(expect, actual)

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixivNovel.LSPixivNovel.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)

            url_s = "https://www.pixiv.net/novel/show.php?id=11111111"
            expect = Path(self.TEST_BASE_PATH) / "./作者名1(111111)/小説タイトル1(11111111)/"

            # 想定保存先ディレクトリが存在する場合は削除する
            if expect.is_dir():
                shutil.rmtree(expect)

            # 保存先ディレクトリが存在しない場合の実行
            actual = Path(lspn_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))
            self.assertEqual(expect, actual)

            # 保存先ディレクトリを作成する
            actual.mkdir(parents=True, exist_ok=True)

            # 保存先ディレクトリが存在する場合の実行
            actual = Path(lspn_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))
            self.assertEqual(expect, actual)

            # サフィックスエラー
            url_s = "https://www.pixiv.net/novel/show.php?id=11111111?rank=1"
            expect = ""
            actual = lspn_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH)
            self.assertEqual(expect, actual)

            # 不正なノベルID
            url_s = "https://www.pixiv.net/novel/show.php?id=00000000"
            expect = ""
            actual = lspn_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH)
            self.assertEqual(expect, actual)

    def test_DownloadNovel(self):
        """ノベル作品をダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLはしない
        """
        with ExitStack() as stack:
            mockpalogin = stack.enter_context(patch("PictureGathering.LSPixivNovel.LSPixivNovel.Login"))
            mockpalogin = self.__MakeLoginMock(mockpalogin)
            lspn_cont = LSPixivNovel.LSPixivNovel(self.username, self.password, self.TEST_BASE_PATH)

            novel_id_s = 11111111
            url_s = f"https://www.pixiv.net/novel/show.php?id={novel_id_s}"
            save_directory_path_s = Path(lspn_cont.MakeSaveDirectoryPath(url_s, self.TEST_BASE_PATH))

            # 正常系
            # ノベル作品
            # 予想される保存先ディレクトリとファイル名を取得
            save_directory_path_cache = save_directory_path_s.parent
            name_s = "{}{}".format(save_directory_path_s.name, ".txt")

            # 1回目の実行
            res = lspn_cont.DownloadNovel(url_s, str(save_directory_path_s))
            self.assertEqual(0, res)  # 新規DL成功想定（実際に保存する）

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(self.TBP.is_dir())
            self.assertTrue(save_directory_path_cache.is_dir())
            self.assertTrue((save_directory_path_cache / name_s).is_file())

            # ファイルの内容チェック
            def MakeExpectText(novel_id):
                work = self.__GetNovelData(novel_id)
                author_name = work.get("author_name")
                author_id = work.get("author_id")
                id = work.get("id")
                title = work.get("title")
                create_date = work.get("create_date")
                page_count = work.get("page_count")
                text_length = work.get("text_length")
                caption = work.get("caption")
                novel_text = work.get("text")
                info_tag = f"[info]\n" \
                           f"author:{author_name}({author_id})\n" \
                           f"id:{id}\n" \
                           f"title:{title}\n" \
                           f"create_date:{create_date}\n" \
                           f"page_count:{page_count}\n" \
                           f"text_length:{text_length}\n"
                soup = BeautifulSoup(caption, "html.parser")
                caption = f"[caption]\n" \
                          f"{soup.prettify()}\n"
                res = ""
                res = res + info_tag + "\n"
                res = res + caption + "\n"
                res = res + "[text]\n" + novel_text + "\n"
                return res

            expect = MakeExpectText(novel_id_s)
            actual = ""
            with (save_directory_path_cache / name_s).open("r", encoding="utf-8") as fin:
                actual = fin.read()
            self.assertEqual(expect, actual)

            # 2回目の実行
            res = lspn_cont.DownloadNovel(url_s, str(save_directory_path_s))
            self.assertEqual(1, res)  # 2回目は既にDL済なのでスキップされる想定

            # DL後のディレクトリ構成とファイルの存在チェック
            self.assertTrue(self.TBP.is_dir())
            self.assertTrue(save_directory_path_cache.is_dir())
            self.assertTrue((save_directory_path_cache / name_s).is_file())

            # 異常系
            # urls指定エラー（空リスト）
            res = lspn_cont.DownloadNovel("", str(save_directory_path_s))
            self.assertEqual(-1, res)

            # urls指定エラー（不正なノベルID）
            url_s = "https://www.pixiv.net/novel/show.php?id=00000000"
            res = lspn_cont.DownloadNovel(url_s, str(save_directory_path_s))
            self.assertEqual(-1, res)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
