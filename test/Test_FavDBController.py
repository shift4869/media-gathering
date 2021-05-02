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

from PictureGathering import FavDBController, Model
from PictureGathering.Model import *

logger = getLogger("root")
logger.setLevel(WARNING)


class TestDBController(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # サンプル生成
        img_url_s = "http://www.img.filename.sample.com/media/sample.png"
        self.f = self.FavoriteSampleFactory(img_url_s)
        self.session.add(self.f)

        self.session.commit()

    def tearDown(self):
        self.session.commit()
    
        records = self.session.query(Favorite).all()
        for r in records:
            lp = Path(r.saved_localpath)
            if lp.is_file():
                lp.unlink()

        records = self.session.query(Retweet).all()
        for r in records:
            lp = Path(r.saved_localpath)
            if lp.is_file():
                lp.unlink()

        self.session.close()
        if self.engine.url.database == ":memory:":
            Base.metadata.drop_all(self.engine)

    def FavoriteSampleFactory(self, img_url: str) -> Favorite:
        """Favoriteオブジェクトを生成する

        Args:
            img_url (str): サンプルメディアURL

        Returns:
            Favorite: Favoriteオブジェクト
        """
        url_orig = img_url + ":orig"
        url_thumbnail = img_url + ":large"
        file_name = Path(img_url).name
        tweet = self.GetTweetSample(img_url)
        save_file_fullpath = Path(file_name)

        with save_file_fullpath.open(mode="wb") as fout:
            fout.write(file_name.encode())  # ファイル名をテキトーに書き込んでおく

        # パラメータ設定
        td_format = "%a %b %d %H:%M:%S +0000 %Y"
        dts_format = "%Y-%m-%d %H:%M:%S"
        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format)
        text = tweet["text"] if "text" in tweet else tweet["full_text"]
        regex = re.compile(r"<[^>]*?>")
        via = regex.sub("", tweet["source"])
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
                 via,
                 str(save_file_fullpath),
                 datetime.now().strftime(dts_format),
                 len(file_name.encode()),
                 file_name.encode())

        # サンプル生成
        f = Favorite(False, param[0], param[1], param[2], param[3], param[4], param[5], param[6],
                     param[7], param[8], param[9], param[10], param[11], param[12], param[13], param[14])
        return f

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

    def test_QuerySample(self):
        """クエリテストサンプル
        """
        expect = [self.f]
        actual = self.session.query(Favorite).all()
        self.assertEqual(actual, expect)

    def test_Upsert(self):
        """FavoriteへのUPSERTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = FavDBController.FavDBController()
        controlar.engine = self.engine

        # 1回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.FavoriteSampleFactory(img_url_s)
        controlar.Upsert(r1.img_filename, r1.url, r1.url_thumbnail,
                         self.GetTweetSample(img_url_s), r1.saved_localpath, True)

        # 2回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.FavoriteSampleFactory(img_url_s)
        controlar.Upsert(r2.img_filename, r2.url, r2.url_thumbnail,
                         self.GetTweetSample(img_url_s), r2.saved_localpath, False)

        # 3回目（UPDATE）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        file_name_s = "sample_3.png"
        r3 = self.FavoriteSampleFactory(img_url_s)
        r3.img_filename = file_name_s
        controlar.Upsert(r3.img_filename, r3.url, r3.url_thumbnail,
                         self.GetTweetSample(img_url_s), r3.saved_localpath, True)

        expect = [self.f, r2, r3]
        actual = self.session.query(Favorite).all()
        self.assertEqual(expect, actual)

    def test_Select(self):
        """FavoriteからのSELECTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = FavDBController.FavDBController()
        controlar.engine = self.engine

        # SELECT
        limit_s = 300
        actual = controlar.Select(limit_s)

        expect = [self.f.toDict()]
        self.assertEqual(expect, actual)

    def test_SelectFromMediaURL(self):
        """Favoriteからfilenameを条件としてのSELECTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = FavDBController.FavDBController()
        controlar.engine = self.engine

        # サンプル生成
        video_url_s = "https://video.twimg.com/ext_tw_video/1152052808385875970/pu/vid/998x714/sample.mp4"
        file_name_s = Path(video_url_s).name
        record = self.FavoriteSampleFactory(video_url_s)
        record.img_filename = file_name_s
        self.session.add(record)
        self.session.commit()

        expect = [record.toDict()]
        actual = controlar.SelectFromMediaURL(file_name_s)
        self.assertEqual(expect, actual)

    def test_FlagUpdate(self):
        """Favoriteのis_exist_saved_fileフラグ更新をチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = FavDBController.FavDBController()
        controlar.engine = self.engine

        # 1回目（r1,r2を追加して両方ともTrueに更新）
        img_url_1 = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self.FavoriteSampleFactory(img_url_1)
        img_url_2 = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self.FavoriteSampleFactory(img_url_2)
        self.session.add(r1)
        self.session.add(r2)

        r1.is_exist_saved_file = True
        r2.is_exist_saved_file = True
        self.session.commit()
        expect = [r1.toDict(), r2.toDict()]
        actual = controlar.FlagUpdate([r1.img_filename, r2.img_filename], 1)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

        # 2回目（r3を追加してr1とr3のみFalseに更新）
        img_url_3 = "http://www.img.filename.sample.com/media/sample_3.png"
        r3 = self.FavoriteSampleFactory(img_url_3)
        r3.is_exist_saved_file = True
        self.session.add(r3)

        r1.is_exist_saved_file = False
        r3.is_exist_saved_file = False
        self.session.commit()
        expect = [r1.toDict(), r3.toDict()]
        actual = controlar.FlagUpdate([r1.img_filename, r3.img_filename], 0)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

    def test_FlagClear(self):
        """Favoriteのis_exist_saved_fileフラグクリア機能をチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = FavDBController.FavDBController()
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
        controlar.FlagClear()

        # フラグクリア後チェック
        self.f.is_exist_saved_file = False
        for t in r:
            t.is_exist_saved_file = False
        expect = [self.f] + r
        actual = self.session.query(Favorite).all()
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
