import configparser
import re
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from mock import MagicMock, PropertyMock, mock_open, patch

from PictureGathering import FavDBController, RetweetDBController, WriteHTML

logger = getLogger(__name__)
logger.setLevel(WARNING)


class TestWriteHTML(unittest.TestCase):

    def setUp(self):
        self.template = '''<!DOCTYPE html>
        <html>
        <head>
        <title>PictureGathering</title>
        </head>
        <body>
        <table>
        {table_content}
        </table>
        </body>
        </html>
        '''
        self.th_template = '''<th>
            <div style="position: relative; width: {pic_width}px;" >
            <a href="{url}" target="_blank">
            <img border="0" src="{url_thumbnail}" alt="{url}" width="{pic_width}px">
            </a>
            <a href="{tweet_url}" target="_blank">
            <img src="{pointer_path}" alt="pointer"
            style="opacity: 0.5; position: absolute; right: 10px; bottom: 10px;"  />
            </a>
            </div>
            </th>
        '''
        self.POINTER_PATH = "./pointer.png"
        self.FAV_HTML_PATH = "./test/FavPictureGathering.html"
        self.RETWEET_HTML_PATH = "./test/RetweetPictureGathering.html"
        self.COLUMN_NUM = 6

    def tearDown(self):
        pass

    def test_MakeTHTag(self):
        """thタグ作成チェック
        """
        s_url = "http://sample.com"
        s_url_thumbnail = "http://sample.com/sample_thumbnail.png"
        s_tweet_url = "http://sample.com/tweet_url"

        pic_width = 256
        expect = self.th_template.format(pic_width=pic_width,
                                         url=s_url,
                                         url_thumbnail=s_url_thumbnail,
                                         tweet_url=s_tweet_url,
                                         pointer_path=self.POINTER_PATH)
        expect = re.sub("\n *", "\n", expect)  # インデントによるスペースの差異は吸収する

        actual = WriteHTML.MakeTHTag(s_url, s_url_thumbnail, s_tweet_url)
        actual = re.sub("\n *", "\n", actual)  # インデントによるスペースの差異は吸収する

        self.assertEqual(expect, actual)

    def test_WriteResultHTML(self):
        """html書き出しチェック
        """
        with ExitStack() as stack:
            # open()をモックに置き換える
            mockfout = mock_open()
            mockfp = stack.enter_context(patch("PictureGathering.WriteHTML.open", mockfout))
            # ファイルパスをテスト用に置き換える
            WriteHTML.FAV_HTML_PATH = self.FAV_HTML_PATH
            WriteHTML.RETWEET_HTML_PATH = self.RETWEET_HTML_PATH

            # DBコントローラー（SELECTだけなので本番のDBを使う）
            CONFIG_FILE_NAME = "./config/config.ini"
            config_path = Path(CONFIG_FILE_NAME)
            config = configparser.ConfigParser()
            self.assertTrue(config_path.is_file())
            config.read(config_path, encoding="utf8")
            db_path = Path(config["db"]["save_path"]) / config["db"]["save_file_name"]

            # select時にデフォルトではキリが良い数しか取得しない
            # 全分岐を通るために中途半端な数を要求する
            limit_s = 299  # 299レコード取得する

            # テスト用html生成関数
            def MakeResultHTML(db):
                res = ""
                cnt = 0
                for row in db:
                    if cnt == 0:
                        res += "<tr>\n"
                    res += WriteHTML.MakeTHTag(url=row["url"], url_thumbnail=row["url_thumbnail"], tweet_url=row["tweet_url"])
                    if cnt == self.COLUMN_NUM - 1:
                        res += "</tr>\n"
                    cnt = (cnt + 1) % self.COLUMN_NUM
                if cnt != 0:
                    for k in range((self.COLUMN_NUM) - (cnt)):
                        res += "<th></th>\n"
                    res += "</tr>\n"
                return res

            # Fav
            db_cont = FavDBController.FavDBController(str(db_path))
            s_db = db_cont.select(limit_s)
            s_save_path = self.FAV_HTML_PATH
            res = MakeResultHTML(s_db)
            expect = self.template.format(table_content=res)
            expect = re.sub("\n *", "\n", expect)

            res = WriteHTML.WriteResultHTML("Fav", db_cont, limit_s)

            actual = mockfout().write.call_args[0][0]
            actual = re.sub("\n *", "\n", actual)
            self.assertEqual(0, res)
            self.assertEqual(expect, actual)

            # Retweet
            db_cont = RetweetDBController.RetweetDBController(str(db_path))
            s_db = db_cont.select(limit_s)
            s_save_path = self.RETWEET_HTML_PATH
            res = MakeResultHTML(s_db)
            expect = self.template.format(table_content=res)
            expect = re.sub("\n *", "\n", expect)

            res = WriteHTML.WriteResultHTML("RT", db_cont, limit_s)

            actual = mockfout().write.call_args[0][0]
            actual = re.sub("\n *", "\n", actual)
            self.assertEqual(0, res)
            self.assertEqual(expect, actual)

            # エラー処理チェック
            res = WriteHTML.WriteResultHTML("error", db_cont, limit_s)
            self.assertEqual(-1, res)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
