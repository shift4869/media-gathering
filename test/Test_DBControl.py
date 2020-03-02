# coding: utf-8
import json
import os
import re
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timedelta
from logging import WARNING, getLogger

import freezegun
from mock import MagicMock, PropertyMock, patch
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from PictureGathering import DBController, Model
from PictureGathering.Model import *

logger = getLogger("root")
logger.setLevel(WARNING)


class TestDBController(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # サンプル生成
        img_url_s = "http://www.img.filename.sample.com/media/sample.png"
        self.f = self.FavoriteSampleFactory(img_url_s)
        self.session.add(self.f)

        # サンプル生成
        img_url_s = "http://www.img.filename.sample.com/media/sample.png"
        self.rt = self.RetweetSampleFactory(img_url_s)
        self.session.add(self.rt)

        self.session.commit()

    def tearDown(self):
        self.session.commit()
        self.session.close()
        if self.engine.url.database == ":memory:":
            Base.metadata.drop_all(self.engine)

    def FavoriteSampleFactory(self, img_url):
        url_orig = img_url + ":orig"
        url_thumbnail = img_url + ":large"
        file_name = os.path.basename(url_orig)
        tweet = self.GetTweetSample(img_url)
        save_file_fullpath = os.getcwd()

        td_format = '%a %b %d %H:%M:%S +0000 %Y'
        dts_format = '%Y-%m-%d %H:%M:%S'
        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format)
        text = tweet["text"] if "text" in tweet else tweet["full_text"]
        param = (file_name,
                 url_orig,
                 url_thumbnail,
                 tweet["id_str"],
                 tweet["entities"]["media"][0]["expanded_url"],
                 dst.strftime(dts_format),
                 tweet["user"]["id_str"],
                 tweet["user"]["name"],
                 tweet["user"]["screen_name"],
                 text,
                 save_file_fullpath,
                 datetime.now().strftime(dts_format))

        # サンプル生成
        f = Favorite(False, param[0], param[1], param[2], param[3], param[4], param[5],
                     param[6], param[7], param[8], param[9], param[10], param[11])
        return f

    def RetweetSampleFactory(self, img_url):
        url_orig = img_url + ":orig"
        url_thumbnail = img_url + ":large"
        file_name = os.path.basename(url_orig)
        tweet = self.GetTweetSample(img_url)
        save_file_fullpath = os.getcwd()

        td_format = '%a %b %d %H:%M:%S +0000 %Y'
        dts_format = '%Y-%m-%d %H:%M:%S'
        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format)
        text = tweet["text"] if "text" in tweet else tweet["full_text"]
        param = (file_name,
                 url_orig,
                 url_thumbnail,
                 tweet["id_str"],
                 tweet["entities"]["media"][0]["expanded_url"],
                 dst.strftime(dts_format),
                 tweet["user"]["id_str"],
                 tweet["user"]["name"],
                 tweet["user"]["screen_name"],
                 text,
                 save_file_fullpath,
                 datetime.now().strftime(dts_format))

        # サンプル生成
        rt = Retweet(False, param[0], param[1], param[2], param[3], param[4], param[5],
                    param[6], param[7], param[8], param[9], param[10], param[11])
        return rt

    def GetTweetSample(self, img_url_s):
        # ツイートオブジェクトのサンプルを生成する
        tweet_url_s = 'http://www.tweet.sample.com'
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
            "text": "tweet_text_sample"
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def GetDelTweetSample(self):
        # ツイートオブジェクトのサンプルを生成する
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id_str": "12345_id_str_sample",
            "text": "@s_shift4869 PictureGathering run.\\n2018/03/09 11:59:38 Process Done !!\\nadd 1 new images. delete 0 old images."
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def test_QuerySample(self):
        # クエリテストサンプル
        expect = [self.f]
        actual = self.session.query(Favorite).all()
        self.assertEqual(actual, expect)

    def test_SQLParam(self):
        # パラメータ生成関数をチェックする
        controlar = DBController.DBController()

        with freezegun.freeze_time('2018-11-18 17:12:58'):
            img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = os.path.basename(url_orig_s)

            td_format_s = '%a %b %d %H:%M:%S +0000 %Y'
            dts_format_s = '%Y-%m-%d %H:%M:%S'

            tweet_s = self.GetTweetSample(img_url_s)
            save_file_fullpath_s = os.getcwd()

            tca = tweet_s["created_at"]
            dst = datetime.strptime(tca, td_format_s)
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
                "saved_localpath": save_file_fullpath_s,
                "saved_created_at": datetime.now().strftime(dts_format_s)
            }
            actual = controlar._DBController__GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)
            self.assertEqual(expect, actual)

            del_tweet_s = self.GetDelTweetSample()
            pattern = ' +[0-9]* '
            text = del_tweet_s["text"]
            add_num = int(re.findall(pattern, text)[0])
            del_num = int(re.findall(pattern, text)[1])

            tca = del_tweet_s["created_at"]
            dst = datetime.strptime(tca, td_format_s)
            expect = {
                "tweet_id": del_tweet_s["id_str"],
                "delete_done": False,
                "created_at": dst.strftime(dts_format_s),
                "deleted_at": None,
                "tweet_text": del_tweet_s["text"],
                "add_num": add_num,
                "del_num": del_num
            }
            actual = controlar._DBController__GetDelUpdateParam(del_tweet_s)
            self.assertEqual(expect, actual)

    def test_DBFavUpsert(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # 1回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.FavoriteSampleFactory(img_url_s)
        controlar.DBFavUpsert(r1.img_filename, r1.url, r1.url_thumbnail,
                              self.GetTweetSample(img_url_s), r1.saved_localpath)

        # 2回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.FavoriteSampleFactory(img_url_s)
        controlar.DBFavUpsert(r2.img_filename, r2.url, r2.url_thumbnail,
                              self.GetTweetSample(img_url_s), r2.saved_localpath)

        # 3回目（UPDATE）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        file_name_s = "sample_3.png"
        r3 = self.FavoriteSampleFactory(img_url_s)
        r3.img_filename = file_name_s
        controlar.DBFavUpsert(r3.img_filename, r3.url, r3.url_thumbnail,
                              self.GetTweetSample(img_url_s), r3.saved_localpath)

        expect = [self.f, r2, r3]
        actual = self.session.query(Favorite).all()
        self.assertEqual(expect, actual)

    def test_DBFavSelect(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # SELECT
        limit_s = 300
        actual = controlar.DBFavSelect(limit_s)

        expect = [self.f.toDict()]
        self.assertEqual(expect, actual)

    def test_DBFavVideoURLSelect(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # サンプル生成
        video_url_s = 'https://video.twimg.com/ext_tw_video/1152052808385875970/pu/vid/998x714/sample.mp4'
        file_name_s = os.path.basename(video_url_s)
        record = self.FavoriteSampleFactory(video_url_s)
        record.img_filename = file_name_s
        self.session.add(record)
        self.session.commit()

        expect = [record.toDict()]
        actual = controlar.DBFavVideoURLSelect(file_name_s)
        self.assertEqual(expect, actual)

    def test_DBFavFlagUpdate(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # 1回目（r1,r2を追加して両方ともTrueに更新）
        img_url_1 = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.FavoriteSampleFactory(img_url_1)
        img_url_2 = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.FavoriteSampleFactory(img_url_2)
        self.session.add(r1)
        self.session.add(r2)
        self.session.commit()

        r1.is_exist_saved_file = True
        r2.is_exist_saved_file = True
        expect = [r1.toDict(), r2.toDict()]
        actual = controlar.DBFavFlagUpdate([r1.img_filename, r2.img_filename], 1)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

        # 2回目（r3を追加してr1とr3のみFalseに更新）
        img_url_3 = "http://www.img.filename.sample.com/media/sample_3.png"
        r3 = self.FavoriteSampleFactory(img_url_3)
        r3.is_exist_saved_file = True
        self.session.add(r3)
        self.session.commit()

        r1.is_exist_saved_file = False
        r3.is_exist_saved_file = False
        expect = [r1.toDict(), r3.toDict()]
        actual = controlar.DBFavFlagUpdate([r1.img_filename, r3.img_filename], 0)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

    def test_DBFavFlagClear(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # サンプル生成
        r = []
        for i, f in enumerate([True, False, True]):
            img_url = f"http://www.img.filename.sample.com/media/sample_{i}.png"
            t = self.FavoriteSampleFactory(img_url)
            t.is_exist_saved_file = f
            r.append(t)
            self.session.add(t)
        self.session.commit()

        # フラグクリア前チェック
        expect = [self.f] + r
        actual = self.session.query(Favorite).all()
        self.assertEqual(expect, actual)

        # フラグクリア
        controlar.DBFavFlagClear()

        # フラグクリア後チェック
        self.f.is_exist_saved_file = False
        for t in r:
            t.is_exist_saved_file = False
        expect = [self.f] + r
        actual = self.session.query(Favorite).all()
        self.assertEqual(expect, actual)

    def test_DBRetweetUpsert(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # 1回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.RetweetSampleFactory(img_url_s)
        controlar.DBRetweetUpsert(r1.img_filename, r1.url, r1.url_thumbnail,
                                  self.GetTweetSample(img_url_s), r1.saved_localpath)

        # 2回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.RetweetSampleFactory(img_url_s)
        controlar.DBRetweetUpsert(r2.img_filename, r2.url, r2.url_thumbnail,
                                  self.GetTweetSample(img_url_s), r2.saved_localpath)

        # 3回目（UPDATE）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        file_name_s = "sample_3.png"
        r3 = self.RetweetSampleFactory(img_url_s)
        r3.img_filename = file_name_s
        controlar.DBRetweetUpsert(r3.img_filename, r3.url, r3.url_thumbnail,
                                  self.GetTweetSample(img_url_s), r3.saved_localpath)

        expect = [self.rt, r2, r3]
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)

    def test_DBRetweetSelect(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # SELECT
        limit_s = 300
        actual = controlar.DBRetweetSelect(limit_s)

        expect = [self.rt.toDict()]
        self.assertEqual(expect, actual)

    def test_DBRetweetVideoURLSelect(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # サンプル生成
        video_url_s = 'https://video.twimg.com/ext_tw_video/1152052808385875970/pu/vid/998x714/sample.mp4'
        file_name_s = os.path.basename(video_url_s)
        record = self.RetweetSampleFactory(video_url_s)
        record.img_filename = file_name_s
        self.session.add(record)
        self.session.commit()

        expect = [record.toDict()]
        actual = controlar.DBRetweetVideoURLSelect(file_name_s)
        self.assertEqual(expect, actual)

    def test_DBRetweetFlagUpdate(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # 1回目（r1,r2を追加して両方ともTrueに更新）
        img_url_1 = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.RetweetSampleFactory(img_url_1)
        img_url_2 = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.RetweetSampleFactory(img_url_2)
        self.session.add(r1)
        self.session.add(r2)
        self.session.commit()

        r1.is_exist_saved_file = True
        r2.is_exist_saved_file = True
        expect = [r1.toDict(), r2.toDict()]
        actual = controlar.DBRetweetFlagUpdate([r1.img_filename, r2.img_filename], 1)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

        # 2回目（r3を追加してr1とr3のみFalseに更新）
        img_url_3 = "http://www.img.filename.sample.com/media/sample_3.png"
        r3 = self.RetweetSampleFactory(img_url_3)
        r3.is_exist_saved_file = True
        self.session.add(r3)
        self.session.commit()

        r1.is_exist_saved_file = False
        r3.is_exist_saved_file = False
        expect = [r1.toDict(), r3.toDict()]
        actual = controlar.DBRetweetFlagUpdate([r1.img_filename, r3.img_filename], 0)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

    def test_DBRetweetFlagClear(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # サンプル生成
        r = []
        for i, f in enumerate([True, False, True]):
            img_url = f"http://www.img.filename.sample.com/media/sample_{i}.png"
            t = self.RetweetSampleFactory(img_url)
            t.is_exist_saved_file = f
            r.append(t)
            self.session.add(t)
        self.session.commit()

        # フラグクリア前チェック
        expect = [self.rt] + r
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)

        # フラグクリア
        controlar.DBRetweetFlagClear()

        # フラグクリア後チェック
        self.rt.is_exist_saved_file = False
        for t in r:
            t.is_exist_saved_file = False
        expect = [self.rt] + r
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)

    def test_DBDelInsert(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        del_tweet_s = self.GetDelTweetSample()
        res = controlar.DBDelInsert(del_tweet_s)
        self.assertEqual(res, 0)

        param = controlar._DBController__GetDelUpdateParam(del_tweet_s)
        expect = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                              param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])
        actual = self.session.query(DeleteTarget).all()
        self.assertEqual([expect], actual)

    def test_DBDelSelect(self):
        # engineをテスト用インメモリテーブルに置き換える
        controlar = DBController.DBController()
        controlar.engine = self.engine

        # テーブルの用意
        records = []
        td_format = '%a %b %d %H:%M:%S +0000 %Y'
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
            param = controlar._DBController__GetDelUpdateParam(del_tweet_s)
            r = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                             param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])
            records.append(r)
            self.session.add(r)
        self.session.commit()

        actual = controlar.DBDelSelect()[0]

        expect = records[2].toDict()
        self.assertEqual(expect["tweet_id"], actual["tweet_id"])


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
