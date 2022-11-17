# coding: utf-8
from pathlib import Path

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *
from sqlalchemy.exc import NoResultFound

from PictureGathering.DBControllerBase import DBControllerBase
from PictureGathering.Model import *


DEBUG = False


class RetweetDBController(DBControllerBase):
    def __init__(self, db_fullpath="PG_DB.db",):
        super().__init__(db_fullpath)

    def upsert(self, params: dict) -> None:
        """RetweetにUPSERTする

        Notes:
            一致しているかの判定は
            img_filename, url, url_thumbnailのどれか一つでも完全一致している場合、とする

        Args:
            params (dict): 以下のキーを持つ辞書
                params = {
                    "is_exist_saved_file": (bool),
                    "img_filename": (str),
                    "url": (str),
                    "url_thumbnail": (str),
                    "tweet_id": (str),
                    "tweet_url": (str),
                    "created_at": (str: "%Y-%m-%d %H:%M:%S"),
                    "user_id": (str),
                    "user_name": (str),
                    "screan_name": (str),
                    "tweet_text": (str),
                    "tweet_via": (str),
                    "saved_localpath": (str),
                    "saved_created_at": (str: "%Y-%m-%d %H:%M:%S"),
                }
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        records = [Retweet.create(params)]
        for r in records:
            try:
                q = session.query(Retweet).filter(
                    or_(Retweet.img_filename == r.img_filename,
                        Retweet.url == r.url,
                        Retweet.url_thumbnail == r.url_thumbnail))
                ex = q.one()
            except NoResultFound:
                # INSERT
                session.add(r)
            else:
                # UPDATE
                ex.is_exist_saved_file = r.is_exist_saved_file
                ex.img_filename = r.img_filename
                ex.url = r.url
                ex.url_thumbnail = r.url_thumbnail
                ex.tweet_id = r.tweet_id
                ex.tweet_url = r.tweet_url
                ex.created_at = r.created_at
                ex.user_id = r.user_id
                ex.user_name = r.user_name
                ex.screan_name = r.screan_name
                ex.tweet_text = r.tweet_text
                ex.tweet_via = r.tweet_via
                ex.saved_localpath = r.saved_localpath
                ex.saved_created_at = r.saved_created_at
                ex.media_size = r.media_size
                ex.media_blob = r.media_blob

        # TODO::操作履歴保存未対応
        session.commit()
        session.close()

    def select(self, limit=300) -> list[dict]:
        """RetweetからSELECTする

        Note:
            f"select * from Retweet order by id desc limit {limit}"

        Args:
            limit (int): 取得レコード数上限

        Returns:
            list[dict]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(Retweet).order_by(desc(Retweet.id)).limit(limit).all()
        res_dict = [r.toDict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict

    def select_from_media_url(self, filename) -> list[dict]:
        """Retweetからfilenameを条件としてSELECTする

        Note:
            f"select * from Retweet where img_filename = {filename}"

        Args:
            filename (str): 取得対象のファイル名

        Returns:
            list[dict]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(Retweet).filter_by(img_filename=filename).all()
        res_dict = [r.toDict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict

    def update_flag(self, filename_list=[], set_flag=0) -> list[dict]:
        """Retweet中の filename_list に含まれるファイル名を持つレコードについて
        　 is_exist_saved_fileフラグを更新する

        Note:
            "update Retweet set is_exist_saved_file = {} where img_filename in ({})".format(set_flag, filename)

        Args:
            filename_list (list[str]): 取得対象のファイル名リスト
            set_flag (int): セットするフラグ

        Returns:
            dict[]: フラグが更新された結果レコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        flag = False if set_flag == 0 else True
        records = session.query(Retweet).filter(Retweet.img_filename.in_(filename_list)).all()
        for record in records:
            record.is_exist_saved_file = flag

        res_dict = [r.toDict() for r in records]  # 辞書リストに変換

        session.commit()
        session.close()
        return res_dict

    def clear_flag(self) -> None:
        """Retweet中のis_exist_saved_fileフラグをすべて0に更新する

        Note:
            "update Retweet set is_exist_saved_file = 0"
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        records = session.query(Retweet).filter(Retweet.is_exist_saved_file).all()
        for record in records:
            record.is_exist_saved_file = False

        session.commit()
        session.close()
        return 0


if __name__ == "__main__":
    DEBUG = True
    db_fullpath = Path("J:\\twitter") / "PG_DB.db"
    db_cont = RetweetDBController(db_fullpath=str(db_fullpath), save_operation=True)
    # db_cont.DBReflectFromFile("./archive/operatefile.txt")
