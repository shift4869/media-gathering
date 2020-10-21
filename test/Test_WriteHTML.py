# coding: utf-8
import sys
import unittest
from logging import WARNING, getLogger

from mock import MagicMock, PropertyMock, patch

from PictureGathering import WriteHTML

logger = getLogger("root")
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
        self.POINTER_PATH = './pointer.png'
        self.FAV_HTML_PATH = './html/FavPictureGathering.html'
        self.RETWEET_HTML_PATH = './html/RetweetPictureGathering.html'
        self.COLUMN_NUM = 6

    def tearDown(self):
        pass

    def FavoriteSampleFactory(self, img_url):
        pass

    def test_MakeTHTag(self):
        """thタグ作成チェック
        """
        pass

    def test_WriteResultHTML(self):
        """html書き出しチェック
        """
        pass

if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
