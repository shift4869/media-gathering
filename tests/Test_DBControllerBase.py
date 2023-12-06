import re
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from freezegun import freeze_time
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from media_gathering import DBControllerBase
from media_gathering.Model import *


class ConcreteDBControllerBase(DBControllerBase.DBControllerBase):
    """テスト用の具体化コントローラー

    DBControllerBase.DBControllerBase()の抽象クラスメソッドを最低限実装したテスト用の派生クラス
    """

    def __init__(self, db_fullpath=":memory:"):
        super().__init__(db_fullpath)

    def upsert(self, params: dict) -> None:
        return 0

    def select(self, limit=300) -> list[dict]:
        return ["select called"]

    def select_from_media_url(self, filename) -> list[dict]:
        return ["select_from_media_url called"]

    def update_flag(self, file_list=[], set_flag=0) -> list[dict]:
        return ["update_flag called"]

    def clear_flag(self) -> None:
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

    def _make_post_tweet_response_sample(self, created_at, add_num, del_num) -> dict:
        """ツイートオブジェクトのサンプルを生成する

        Notes:
            DeleteTargetに挿入するツイートのサンプル

        Returns:
            dict: ツイートオブジェクト（post後の返り値）
        """
        tweet_texts = [
            "@s_shift4869 PictureGathering run.",
            f"{created_at} Process Done !!",
            f"add {add_num} new images. delete {del_num} old images."
        ]
        tweet_s = {
            "data": {
                "id": "12345_id_str_sample",
                "text": "\n".join(tweet_texts)
            }
        }
        return tweet_s

    def _make_external_link_sample(self, i: int) -> ExternalLink:
        """外部リンクオブジェクトのサンプルを生成する

        Notes:
            ExternalLinkに挿入する外部リンクオブジェクトのサンプル

        Returns:
            ExternalLink: 外部リンクオブジェクト
        """
        expanded_url = f"expanded_url_{i:02}"
        tweet_id = f"{i:05}"
        tweet_url = f"tweet_url_{i:02}"
        dts_format = "%Y-%m-%d %H:%M:%S"
        created_at = datetime.now().strftime(dts_format)
        user_id = f"{i:03}"
        user_name = f"user_name_{i:02}"
        screan_name = f"screan_name_{i:02}"
        tweet_text = f"tweet_text_{i:02}"
        tweet_via = "tweet_via"
        saved_created_at = datetime.now().strftime(dts_format)
        link_type = ""
        r = {
            "external_link_url": expanded_url,
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "created_at": created_at,
            "user_id": user_id,
            "user_name": user_name,
            "screan_name": screan_name,
            "tweet_text": tweet_text,
            "tweet_via": tweet_via,
            "saved_created_at": saved_created_at,
            "link_type": link_type,
        }
        return ExternalLink.create(r)

    def test_upsert_del(self):
        """DeleteTargetへのUPSERTをチェックする
        """
        freezed_time = "2022-10-24 10:30:00"
        with freeze_time(freezed_time):
            # engineをテスト用インメモリテーブルに置き換える
            controlar = ConcreteDBControllerBase()
            controlar.engine = self.engine

            # 厳密な一致判定
            def is_equal_DeleteTarget(p_list, q_list):
                if len(p_list) != len(q_list):
                    return False
                for p, q in zip(p_list, q_list):
                    member = [
                        p.tweet_id == q.tweet_id,
                        p.delete_done == q.delete_done,
                        p.created_at == q.created_at,
                        p.deleted_at == q.deleted_at,
                        p.tweet_text == q.tweet_text,
                        p.add_num == q.add_num,
                        p.del_num == q.del_num
                    ]
                    if not all(member):
                        return False
                return True

            # insert
            tweet_del = self._make_post_tweet_response_sample(freezed_time, 1, 0)

            pattern = " +[0-9]* "
            text = tweet_del.get("data", {}).get("text", "")
            add_num = int(re.findall(pattern, text)[0])
            del_num = int(re.findall(pattern, text)[1])
            dts_format = "%Y-%m-%d %H:%M:%S"

            params = {
                "tweet_id": tweet_del.get("data", {}).get("id", ""),
                "delete_done": False,
                "created_at": datetime.now().strftime(dts_format),
                "deleted_at": None,
                "tweet_text": text,
                "add_num": add_num,
                "del_num": del_num
            }
            expect = DeleteTarget(params["tweet_id"], params["delete_done"], params["created_at"],
                                  params["deleted_at"], params["tweet_text"], params["add_num"], params["del_num"])

            actual = controlar.upsert_del(tweet_del)
            self.assertIsNone(actual)
            actual = self.session.query(DeleteTarget).all()
            self.assertTrue(is_equal_DeleteTarget([expect], actual))

            # update
            tweet_del = self._make_post_tweet_response_sample(freezed_time, 5, 3)

            pattern = " +[0-9]* "
            text = tweet_del.get("data", {}).get("text", "")
            add_num = int(re.findall(pattern, text)[0])
            del_num = int(re.findall(pattern, text)[1])
            dts_format = "%Y-%m-%d %H:%M:%S"

            params = {
                "tweet_id": tweet_del.get("data", {}).get("id", ""),
                "delete_done": False,
                "created_at": datetime.now().strftime(dts_format),
                "deleted_at": None,
                "tweet_text": text,
                "add_num": add_num,
                "del_num": del_num
            }
            expect = DeleteTarget(params["tweet_id"], params["delete_done"], params["created_at"],
                                  params["deleted_at"], params["tweet_text"], params["add_num"], params["del_num"])

            actual = controlar.upsert_del(tweet_del)
            self.assertIsNone(actual)
            actual = self.session.query(DeleteTarget).all()
            self.assertTrue(is_equal_DeleteTarget([expect], actual))

    def test_update_del(self):
        """DeleteTargetからのSELECTしてフラグをUPDATEする機能をチェックする
        """
        # engineをテスト用インメモリテーブルに置き換える
        controlar = ConcreteDBControllerBase()
        controlar.engine = self.engine

        # テーブルの用意
        for i in range(1, 5):
            freezed_time = f"2022-10-{i:02} 10:30:00"
            with freeze_time(freezed_time):
                # insert
                tweet_del = self._make_post_tweet_response_sample(freezed_time, i + 2, i + 1)
                tweet_del["data"]["id"] = f"{i:02}_" + tweet_del["data"]["id"]
                controlar.upsert_del(tweet_del)

        freezed_time = f"2022-10-05 10:30:00"
        with freeze_time(freezed_time):
            t = date.today() - timedelta(1)
            expect_element_list = list(self.session.query(DeleteTarget).all()[:3])

            expect = []
            for record in expect_element_list:
                record.delete_done = True
                record.deleted_at = t.strftime("%Y-%m-%d %H:%M:%S")
                expect.append(record.to_dict())
            actual = controlar.update_del()
            self.assertEqual(expect, actual)

    def test_upsert_external_link(self):
        """ExternalLinkへのUPSERTをチェックする
        """
        freezed_time = "2022-10-24 10:30:00"
        with freeze_time(freezed_time):
            # engineをテスト用インメモリテーブルに置き換える
            controlar = ConcreteDBControllerBase()
            controlar.engine = self.engine

            # 厳密な一致判定
            def is_equal_ExternalLink(p_list, q_list):
                if len(p_list) != len(q_list):
                    return False
                for p, q in zip(p_list, q_list):
                    member = [
                        p.external_link_url == q.external_link_url,
                        p.tweet_id == q.tweet_id,
                        p.tweet_url == q.tweet_url,
                        p.created_at == q.created_at,
                        p.user_id == q.user_id,
                        p.user_name == q.user_name,
                        p.screan_name == q.screan_name,
                        p.tweet_text == q.tweet_text,
                        p.tweet_via == q.tweet_via,
                        p.saved_created_at == q.saved_created_at,
                        p.link_type == q.link_type
                    ]
                    if not all(member):
                        return False
                return True

            # insert
            external_link_list = [self._make_external_link_sample(i) for i in range(5)]
            expect = [self._make_external_link_sample(i) for i in range(5)]

            controlar.upsert_external_link(external_link_list)

            actual = self.session.query(ExternalLink).all()
            self.assertTrue(is_equal_ExternalLink(expect, actual))

            # update
            external_link_list = [self._make_external_link_sample(i) for i in range(5)]
            expect = [self._make_external_link_sample(i) for i in range(5)]
            for e_args, e in zip(external_link_list, expect):
                e_args.tweet_text = "updated_" + e_args.tweet_text
                e.tweet_text = "updated_" + e.tweet_text

            controlar.upsert_external_link(external_link_list)

            actual = []
            for record in expect:
                external_link = controlar.select_external_link(record.external_link_url)
                actual.append(external_link[0])
            expect = [e.to_dict() for e in expect]
            for e, a in zip(expect, actual):
                del e["id"]
                del a["id"]
            self.assertEqual(expect, actual)

    def test_select_external_link(self):
        """ExternalLinkへのSELECTをチェックする
        """
        freezed_time = "2022-10-24 10:30:00"
        with freeze_time(freezed_time):
            # engineをテスト用インメモリテーブルに置き換える
            controlar = ConcreteDBControllerBase()
            controlar.engine = self.engine

            # insert
            external_link_list = [self._make_external_link_sample(i) for i in range(5)]
            controlar.upsert_external_link(external_link_list)

            expect = self.session.query(ExternalLink).all()

            actual = []
            for record in expect:
                external_link = controlar.select_external_link(record.external_link_url)
                actual.append(external_link[0])
            expect = [e.to_dict() for e in expect]
            self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
