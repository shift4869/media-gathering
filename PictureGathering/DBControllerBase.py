# coding: utf-8
import re
from abc import ABCMeta, abstractmethod
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import *
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from PictureGathering.Model import *

DEBUG = False


class DBControllerBase(metaclass=ABCMeta):
    def __init__(self, db_fullpath="PG_DB.db"):
        self.dbname = db_fullpath
        self.engine = create_engine(f"sqlite:///{self.dbname}", echo=False)
        Base.metadata.create_all(self.engine)

    @abstractmethod
    def upsert(self, params: dict) -> None:
        """DBにUPSERTする

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
        pass

    @abstractmethod
    def select(self, limit=300) -> list[dict]:
        """DBからSELECTする

        Note:
            f"select * from Favorite order by created_at desc limit {limit}"

        Args:
            limit (int): 取得レコード数上限

        Returns:
            list[dict]: SELECTしたレコードの辞書リスト
        """
        return []

    @abstractmethod
    def select_from_media_url(self, filename) -> list[dict]:
        """filename を条件としてSELECTする

        Note:
            f"select * from Favorite where img_filename = {filename}"

        Args:
            filename (str): 取得対象のファイル名

        Returns:
            list[dict]: SELECTしたレコードの辞書リスト
        """
        return []

    @abstractmethod
    def update_flag(self, filename_list=[], set_flag=0) -> list[dict]:
        """filename_list に含まれるファイル名を持つレコードについて
        　 is_exist_saved_file フラグを更新する

        Note:
            f"update Favorite set is_exist_saved_file = {set_flag} where img_filename in ({filename_list})"

        Args:
            filename_list (list): 取得対象のファイル名リスト
            set_flag (int): セットするフラグ

        Returns:
            list[dict]: フラグが更新された結果レコードの辞書リスト
        """
        return []

    @abstractmethod
    def clear_flag(self) -> None:
        """is_exist_saved_file フラグをすべて0に更新する

        Note:
            "update Favorite set is_exist_saved_file = 0"
        """
        pass

    def upsert_del(self, tweet) -> None:
        """DeleteTargetにUPSERTする

        Note:
            insert into DeleteTarget (tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num) values (*)

        Args:
            tweet (dict): Insert対象ツイートオブジェクト
                tweet = {
                    "data": {
                        "id": tweet_id (str),
                        "text": (str),
                    }
                }
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        # text から add_num と del_num を抽出する
        pattern = " +[0-9]* "
        text = tweet.get("data", {}).get("text", "")
        add_num = int(re.findall(pattern, text)[0])
        del_num = int(re.findall(pattern, text)[1])
        dts_format = "%Y-%m-%d %H:%M:%S"

        params = {
            "tweet_id": tweet.get("data", {}).get("id", ""),
            "delete_done": False,
            "created_at": datetime.now().strftime(dts_format),
            "deleted_at": None,
            "tweet_text": text,
            "add_num": add_num,
            "del_num": del_num
        }
        r = DeleteTarget(params["tweet_id"], params["delete_done"], params["created_at"],
                         params["deleted_at"], params["tweet_text"], params["add_num"], params["del_num"])

        try:
            q = session.query(DeleteTarget).filter(
                or_(DeleteTarget.tweet_id == r.tweet_id))
            ex = q.one()
        except NoResultFound:
            # INSERT
            session.add(r)
        else:
            # UPDATE
            ex.tweet_id = r.tweet_id
            ex.delete_done = r.delete_done
            ex.created_at = r.created_at
            ex.deleted_at = r.deleted_at
            ex.tweet_text = r.tweet_text
            ex.add_num = r.add_num
            ex.del_num = r.del_num

        session.commit()
        session.close()

    def update_del(self) -> list[dict]:
        """DeleteTargetからSELECTしてフラグをUPDATEする

        Note:
            2日前の通知ツイートを削除対象とする

        Returns:
            list[dict]: 削除対象となる通知ツイートの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        # 2日前の通知ツイートを削除する(1日前の日付より前)
        t = date.today() - timedelta(1)
        # 今日未満 = 昨日以前の通知ツイートをDBから取得
        records = session.query(DeleteTarget).filter(~DeleteTarget.delete_done).\
            filter(DeleteTarget.created_at < t.strftime("%Y-%m-%d %H:%M:%S")).all()

        # 消去フラグを立てる
        for record in records:
            record.delete_done = True
            record.deleted_at = t.strftime("%Y-%m-%d %H:%M:%S")

        res_dict = [r.to_dict() for r in records]  # 辞書リストに変換

        session.commit()
        session.close()
        return res_dict

    def upsert_external_link(self, external_link_list: list[ExternalLink]) -> None:
        """ExternalLinkにUPSERTする

        Args:
            external_link_list (list[ExternalLink]): 外部リンクリスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        for r in external_link_list:
            try:
                q = session.query(ExternalLink).filter(and_(ExternalLink.external_link_url == r.external_link_url, ExternalLink.tweet_url == r.tweet_url))
                p = q.one()
            except NoResultFound:
                # INSERT
                session.add(r)
            else:
                # UPDATE
                p.external_link_url = r.external_link_url
                p.tweet_id = r.tweet_id
                p.tweet_url = r.tweet_url
                p.created_at = r.created_at
                p.user_id = r.user_id
                p.user_name = r.user_name
                p.screan_name = r.screan_name
                p.tweet_text = r.tweet_text
                p.tweet_via = r.tweet_via
                if p.saved_created_at == "":
                    p.saved_created_at = r.saved_created_at
                p.link_type = r.link_type

        session.commit()
        session.close()

    def select_external_link(self, target_external_link: str) -> list[dict]:
        """ExternalLinkからSELECTする

        Args:
            target_external_link (str): 対象外部リンク

        Returns:
            list[dict]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(ExternalLink).filter_by(external_link_url=target_external_link).all()
        res_dict = [r.to_dict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict


if __name__ == "__main__":
    import PictureGathering.FavDBController
    DEBUG = True
    db_fullpath = Path("J:\\twitter") / "PG_DB.db"
    db_cont = PictureGathering.FavDBController(db_fullpath=str(db_fullpath), save_operation=True)
    # db_cont.DBReflectFromFile("./archive/operatefile.txt")
