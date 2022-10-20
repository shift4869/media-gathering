# coding: utf-8
import json
import re
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timedelta
from logging import WARNING, getLogger
from mock import MagicMock, PropertyMock, patch
from pathlib import Path

import freezegun
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from PictureGathering import DBControllerBase, Model
from PictureGathering.Model import *

logger = getLogger(__name__)
logger.setLevel(WARNING)
TEST_DB_FULLPATH = "./test/test.db"


class ConcreteDBControllerBase(DBControllerBase.DBControllerBase):
    """テスト用の具体化コントローラー

    DBControllerBase.DBControllerBase()の抽象クラスメソッドを最低限実装したテスト用の派生クラス
    """

    def __init__(self, db_fullpath=TEST_DB_FULLPATH, save_operation=True):
        super().__init__(db_fullpath, save_operation)

    def Upsert(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath, include_blob):
        return 0

    def Select(self, limit=300):
        return ["Select Called"]

    def SelectFromMediaURL(self, filename):
        return ["SelectFromMediaURL Called"]

    def FlagUpdate(self, file_list=[], set_flag=0):
        return ["FlagUpdate Called"]

    def FlagClear(self):
        return 0


class TestDBController(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        self.session.commit()
        self.session.close()
        if self.engine.url.database == ":memory:":
            Base.metadata.drop_all(self.engine)

        if Path(TEST_DB_FULLPATH).is_file():
            Path(TEST_DB_FULLPATH).unlink()

        # 操作履歴削除
        sd_archive = Path("./archive")
        op_files = [s for s in sd_archive.glob("**/*") if ".gitkeep" not in str(s)]
        for op_file in op_files:
            op_file.unlink()

    def GetTweetSample(self, img_url_s: str) -> dict:
        """ツイートオブジェクトのサンプルを生成する

        Notes:
            メディアを含むツイートのサンプル
            辞書構造やキーについては下記tweet_json参照

        Args:
            img_url_s (str): サンプルメディアURL

        Returns:
            dict: ツイートオブジェクト（辞書）
        """
        # ネストした引用符つきの文字列はjsonで処理できないのであくまで仮の文字列
        tweet_url_s = "http://www.tweet.sample.com"
        tag_p_s = "<a href=https://mobile.twitter.com rel=nofollow>Twitter Web App</a>"
        tweet_json = f'''{{
            "entities": {{
                "media": [{{
                    "expanded_url": "{tweet_url_s}"
                }}]
            }},
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id_str": "12345_id_str_sample",
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "text": "tweet_text_sample",
            "source": "{tag_p_s}"
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def GetDelTweetSample(self) -> dict:
        """ツイートオブジェクトのサンプルを生成する

        Notes:
            DeleteTargetに挿入するツイートのサンプル
            辞書構造やキーについては下記tweet_json参照

        Returns:
            dict: ツイートオブジェクト（辞書）
        """
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id_str": "12345_id_str_sample",
            "text": "@s_shift4869 PictureGathering run.\\n2018/03/09 11:59:38 Process Done !!\\nadd 1 new images. delete 0 old images."
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def test_SQLParam(self):
        """パラメータ生成関数をチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = ConcreteDBControllerBase()
        controlar.engine = self.engine

        with freezegun.freeze_time("2018-11-18 17:12:58"):
            img_url_s = "http://www.img.filename.sample.com/media/sample.png"
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = Path(img_url_s).name

            td_format_s = "%a %b %d %H:%M:%S +0000 %Y"
            dts_format_s = "%Y-%m-%d %H:%M:%S"

            tweet_s = self.GetTweetSample(img_url_s)
            save_file_fullpath_s = Path(file_name_s)

            with save_file_fullpath_s.open(mode="wb") as fout:
                fout.write(b"abcde")

            tca = tweet_s["created_at"]
            dst = datetime.strptime(tca, td_format_s) + timedelta(hours=9)
            regex = re.compile(r"<[^>]*?>")
            via = regex.sub("", tweet_s["source"])
            expect = {
                "img_filename": file_name_s,
                "url": url_orig_s,
                "url_thumbnail": url_thumbnail_s,
                "tweet_id": tweet_s["id_str"],
                "tweet_url": tweet_s["entities"]["media"][0]["expanded_url"],
                "created_at": dst.strftime(dts_format_s),
                "user_id": tweet_s["user"]["id_str"],
                "user_name": tweet_s["user"]["name"],
                "screan_name": tweet_s["user"]["screen_name"],
                "tweet_text": tweet_s["text"],
                "tweet_via": via,
                "saved_localpath": str(save_file_fullpath_s),
                "saved_created_at": datetime.now().strftime(dts_format_s),
                "media_size": 5,
                "media_blob": b"abcde"
            }
            actual = controlar._GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, str(save_file_fullpath_s), True)
            self.assertEqual(expect, actual)

            del_tweet_s = self.GetDelTweetSample()
            pattern = " +[0-9]* "
            text = del_tweet_s["text"]
            add_num = int(re.findall(pattern, text)[0])
            del_num = int(re.findall(pattern, text)[1])

            tca = del_tweet_s["created_at"]
            dst = datetime.strptime(tca, td_format_s) + timedelta(hours=9)
            expect = {
                "tweet_id": del_tweet_s["id_str"],
                "delete_done": False,
                "created_at": dst.strftime(dts_format_s),
                "deleted_at": None,
                "tweet_text": del_tweet_s["text"],
                "add_num": add_num,
                "del_num": del_num
            }
            actual = controlar._GetDelUpdateParam(del_tweet_s)
            self.assertEqual(expect, actual)

    def test_DBDelUpsert(self):
        """DeleteTargetへのUPSERTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = ConcreteDBControllerBase()
        controlar.engine = self.engine

        del_tweet_s = self.GetDelTweetSample()
        res = controlar.DelUpsert(del_tweet_s)
        self.assertEqual(res, 0)

        param = controlar._GetDelUpdateParam(del_tweet_s)
        expect = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                              param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])
        actual = self.session.query(DeleteTarget).all()
        self.assertEqual([expect], actual)

    def test_DBDelSelect(self):
        """DeleteTargetからのSELECTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = ConcreteDBControllerBase()
        controlar.engine = self.engine

        # テーブルの用意
        records = []
        td_format = "%a %b %d %H:%M:%S +0000 %Y"
        t = []
        s = []
        t.append(date.today())
        for i in range(1, 3):
            t.append(t[i - 1] - timedelta(1))
        for tn in t:
            s.append(tn.strftime(td_format))
        for i, sn in enumerate(s):
            del_tweet_s = {
                "created_at": sn,
                "id_str": f"12345_id_str_sample_{i + 1}",
                "text": "@s_shift4869 PictureGathering run.\\n2018/03/09 11:59:38 Process Done !!\\nadd 1 new images. delete 0 old images."
            }
            param = controlar._GetDelUpdateParam(del_tweet_s)
            r = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                             param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])
            records.append(r)
            self.session.add(r)
        self.session.commit()

        actual = controlar.DelSelect()[0]

        expect = records[2].toDict()
        self.assertEqual(expect["tweet_id"], actual["tweet_id"])

    def test_DBReflectFromFile(self):
        """操作履歴ファイルから操作を反映する機能をチェックする
        """
        return  # 一旦スキップ

        # engineをテスト用インメモリテーブルに置き換える
        controlar = ConcreteDBControllerBase()
        controlar.engine = self.engine

        # テスト用操作履歴ファイルを反映する
        operate_file = "./test/operate_file_example/operatefile.txt"
        operate_file_path = Path(operate_file)

        res = controlar.DBReflectFromFile(str(operate_file_path))
        self.assertEqual(res, 0)

        # テスト用操作履歴ファイル反映後の想定状況と比較する
        # DBFavUpsert
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.FavoriteSampleFactory(img_url_s)
        img_url_s = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.FavoriteSampleFactory(img_url_s)
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        file_name_s = "sample_3.png"
        r3 = self.FavoriteSampleFactory(img_url_s)
        r3.img_filename = file_name_s
        expect = [self.f, r2, r3]
        actual = self.session.query(Favorite).all()
        self.assertEqual(expect, actual)

        # DBRetweetUpsert
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.RetweetSampleFactory(img_url_s)
        img_url_s = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.RetweetSampleFactory(img_url_s)
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        file_name_s = "sample_3.png"
        r3 = self.RetweetSampleFactory(img_url_s)
        r3.img_filename = file_name_s
        expect = [self.rt, r2, r3]
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)

        # DBDelUpsert
        del_tweet_s = self.GetDelTweetSample()
        param = controlar._DBController__GetDelUpdateParam(del_tweet_s)
        expect = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                              param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])
        actual = self.session.query(DeleteTarget).all()
        self.assertEqual([expect], actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
