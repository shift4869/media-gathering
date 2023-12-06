import sys
import unittest
from datetime import datetime
from pathlib import Path

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from media_gathering import RetweetDBController
from media_gathering.Model import *
from media_gathering.tac.TweetInfo import TweetInfo

TEST_DB_FULLPATH = "./tests/tests.db"


class TestDBController(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # サンプル生成
        img_url_s = "http://www.img.filename.sample.com/media/sample.png"
        self.rt = self._Retweet_sample_factory(img_url_s)
        self.session.add(self.rt)

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

    @classmethod
    def tearDownClass(cls):
        if Path(TEST_DB_FULLPATH).is_file():
            Path(TEST_DB_FULLPATH).unlink(missing_ok=True)

    def _Retweet_sample_factory(self, img_url: str) -> Retweet:
        """Retweetオブジェクトを生成する

        Args:
            img_url (str): サンプルメディアURL

        Returns:
            Retweet: Retweetオブジェクト
        """
        url_orig = img_url + ":orig"
        url_thumbnail = img_url + ":large"
        file_name = Path(img_url).name
        tweet_info = self._make_tweet_info_sample(img_url)
        save_file_fullpath = Path(file_name)

        with save_file_fullpath.open(mode="wb") as fout:
            fout.write(file_name.encode())  # ファイル名をテキトーに書き込んでおく

        # パラメータ設定
        dts_format = "%Y-%m-%d %H:%M:%S"
        params = {
            "is_exist_saved_file": True,
            "img_filename": file_name,
            "url": url_orig,
            "url_thumbnail": url_thumbnail,
            "tweet_id": tweet_info.tweet_id,
            "tweet_url": tweet_info.tweet_url,
            "created_at": tweet_info.created_at,
            "user_id": tweet_info.user_id,
            "user_name": tweet_info.user_name,
            "screan_name": tweet_info.screan_name,
            "tweet_text": tweet_info.tweet_text,
            "tweet_via": tweet_info.tweet_via,
            "saved_localpath": str(save_file_fullpath),
            "saved_created_at": datetime.now().strftime(dts_format),
        }
        params["media_blob"] = None
        params["media_size"] = Path(save_file_fullpath).stat().st_size
        rt = Retweet.create(params)
        return rt

    def _make_tweet_info_sample(self, img_url_s: str) -> TweetInfo:
        """ツイートオブジェクトのサンプルを生成する

        Notes:
            メディアを含むツイートのサンプル
            辞書構造やキーについては下記tweet_json参照

        Args:
            img_url_s (str): サンプルメディアURL

        Returns:
            TweetInfo: ツイート情報オブジェクト
        """
        dts_format = "%Y-%m-%d %H:%M:%S"
        file_name = Path(img_url_s).name
        tweet_url_s = "http://www.tweet.sample.com"
        arg_dict = {
            "media_filename": file_name,
            "media_url": img_url_s,
            "media_thumbnail_url": img_url_s,
            "tweet_id": "tweet_id",
            "tweet_url": tweet_url_s,
            "created_at": datetime.now().strftime(dts_format),
            "user_id": "user_id",
            "user_name": "user_name",
            "screan_name": "screan_name",
            "tweet_text": "tweet_text",
            "tweet_via": "tweet_via",
        }
        tweet_s = TweetInfo.create(arg_dict)
        return tweet_s

    def test_QuerySample(self):
        """クエリテストサンプル
        """
        expect = [self.rt]
        actual = self.session.query(Retweet).all()
        self.assertEqual(actual, expect)

    def test_upsert(self):
        """RetweetへのUPSERTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = RetweetDBController.RetweetDBController(TEST_DB_FULLPATH)
        controlar.engine = self.engine

        # 1回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self._Retweet_sample_factory(img_url_s)
        controlar.upsert(r1.to_dict())

        # 2回目（INSERT）
        img_url_s = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self._Retweet_sample_factory(img_url_s)
        controlar.upsert(r2.to_dict())

        # 3回目（UPDATE）
        img_url_s = "http://www.img.filename.sample.com/media/sample_1.png"
        file_name_s = "sample_3.png"
        r3 = self._Retweet_sample_factory(img_url_s)
        r3.img_filename = file_name_s
        controlar.upsert(r3.to_dict())

        r2.id = "2"
        r3.id = "3"
        expect = [self.rt, r3, r2]
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)

    def test_select(self):
        """RetweetからのSELECTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = RetweetDBController.RetweetDBController(TEST_DB_FULLPATH)
        controlar.engine = self.engine

        # SELECT
        limit_s = 300
        actual = controlar.select(limit_s)

        expect = [self.rt.to_dict()]
        self.assertEqual(expect, actual)

    def test_select_from_media_url(self):
        """Retweetからfilenameを条件としてのSELECTをチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = RetweetDBController.RetweetDBController(TEST_DB_FULLPATH)
        controlar.engine = self.engine

        # サンプル生成
        video_url_s = "https://video.twimg.com/ext_tw_video/1152052808385875970/pu/vid/998x714/sample.mp4"
        file_name_s = Path(video_url_s).name
        record = self._Retweet_sample_factory(video_url_s)
        record.img_filename = file_name_s
        self.session.add(record)
        self.session.commit()

        expect = [record.to_dict()]
        actual = controlar.select_from_media_url(file_name_s)
        self.assertEqual(expect, actual)

    def test_update_flag(self):
        """Retweetのis_exist_saved_fileフラグ更新をチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = RetweetDBController.RetweetDBController(TEST_DB_FULLPATH)
        controlar.engine = self.engine

        # 1回目（r1,r2を追加して両方ともTrueに更新）
        img_url_1 = "http://www.img.filename.sample.com/media/sample_1.png"
        r1 = self._Retweet_sample_factory(img_url_1)
        img_url_2 = "http://www.img.filename.sample.com/media/sample_2.png"
        r2 = self._Retweet_sample_factory(img_url_2)
        self.session.add(r1)
        self.session.add(r2)

        r1.is_exist_saved_file = True
        r2.is_exist_saved_file = True
        self.session.commit()
        expect = [r1.to_dict(), r2.to_dict()]
        actual = controlar.update_flag([r1.img_filename, r2.img_filename], 1)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

        # 2回目（r3を追加してr1とr3のみFalseに更新）
        img_url_3 = "http://www.img.filename.sample.com/media/sample_3.png"
        r3 = self._Retweet_sample_factory(img_url_3)
        r3.is_exist_saved_file = True
        self.session.add(r3)

        r1.is_exist_saved_file = False
        r3.is_exist_saved_file = False
        self.session.commit()
        expect = [r1.to_dict(), r3.to_dict()]
        actual = controlar.update_flag([r1.img_filename, r3.img_filename], 0)
        self.assertEqual(expect[0]["is_exist_saved_file"], actual[0]["is_exist_saved_file"])
        self.assertEqual(expect, actual)

    def test_clear_flag(self):
        """Retweetのis_exist_saved_fileフラグクリア機能をチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = RetweetDBController.RetweetDBController(TEST_DB_FULLPATH)
        controlar.engine = self.engine

        # サンプル生成
        r = []
        for i, f in enumerate([True, False, True]):
            img_url = f"http://www.img.filename.sample.com/media/sample_{i}.png"
            t = self._Retweet_sample_factory(img_url)
            t.is_exist_saved_file = f
            r.append(t)
            self.session.add(t)
        self.session.commit()

        # フラグクリア前チェック
        expect = [self.rt] + r
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)

        # フラグクリア
        controlar.clear_flag()

        # フラグクリア後チェック
        self.rt.is_exist_saved_file = False
        for t in r:
            t.is_exist_saved_file = False
        expect = [self.rt] + r
        actual = self.session.query(Retweet).all()
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
