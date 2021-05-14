# coding: utf-8
import pickle
from pathlib import Path

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from PictureGathering.DBControllerBase import DBControllerBase
from PictureGathering.Model import *


DEBUG = False


class FavDBController(DBControllerBase):
    def __init__(self, db_fullpath="PG_DB.db", save_operation=True):
        super().__init__(db_fullpath, save_operation)

    def Upsert(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath, include_blob):
        """FavoriteにUPSERTする

        Notes:
            追加しようとしているレコードが既存テーブルに存在しなければINSERT
            存在しているならばUPDATE(DELETE->INSERT)
            一致しているかの判定は
            img_filename, url, url_thumbnailのどれか一つでも完全一致している場合、とする

        Args:
            file_name (str): ファイル名
            url_orig (str): メディアURL
            url_thumbnail (str): サムネイルメディアURL
            tweet(str): ツイート本文
            save_file_fullpath(str): メディア保存パス（ローカル）

        Returns:
            int: 0(成功,新規追加), 1(成功,更新), other(失敗)
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()
        res = -1

        param = self._GetUpdateParam(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath, include_blob)
        r = Favorite(False, param["img_filename"], param["url"], param["url_thumbnail"],
                     param["tweet_id"], param["tweet_url"], param["created_at"],
                     param["user_id"], param["user_name"], param["screan_name"],
                     param["tweet_text"], param["tweet_via"], param["saved_localpath"], param["saved_created_at"],
                     param["media_size"], param["media_blob"])

        try:
            q = session.query(Favorite).filter(
                or_(Favorite.img_filename == r.img_filename,
                    Favorite.url == r.url,
                    Favorite.url_thumbnail == r.url_thumbnail))
            ex = q.one()
        except NoResultFound:
            # INSERT
            session.add(r)
            res = 0
        else:
            # UPDATEは実質DELETE->INSERTと同じとする
            session.delete(ex)
            session.commit()
            session.add(r)
            res = 1

        session.commit()
        session.close()

        # 操作履歴保存
        if self.operatefile and self.operatefile.is_file():
            bname = "DBFavUpsert_" + file_name.split(".")[0] + ".bin"
            bin_file_path = self.operatefile.parent / bname
            with bin_file_path.open(mode="wb") as fout:
                pickle.dump(tweet, fout)
            with self.operatefile.open(mode="a", encoding="utf_8") as fout:
                fout.write("DBFavUpsert,{},{},{},{},{}\n".format(file_name, url_orig, url_thumbnail, save_file_fullpath, include_blob))

        return res

    def Select(self, limit=300):
        """FavoriteからSELECTする

        Note:
            "select * from Favorite order by created_at desc limit {}".format(limit)

        Args:
            limit (int): 取得レコード数上限

        Returns:
            dict[]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(Favorite).order_by(desc(Favorite.created_at)).limit(limit).all()
        res_dict = [r.toDict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict

    def SelectFromMediaURL(self, filename):
        """Favoriteからfilenameを条件としてSELECTする

        Note:
            "select * from Favorite where img_filename = {}".format(file_name_s)

        Args:
            filename (str): 取得対象のファイル名

        Returns:
            dict[]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(Favorite).filter_by(img_filename=filename).all()
        res_dict = [r.toDict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict

    def FlagUpdate(self, file_list=[], set_flag=0):
        """Favorite中のfile_listに含まれるファイル名を持つレコードについて
        　 is_exist_saved_fileフラグを更新する

        Note:
            "update Favorite set is_exist_saved_file = {} where img_filename in ({})".format(set_flag, filename)

        Args:
            file_list (list): 取得対象のファイル名リスト
            set_flag (int): セットするフラグ

        Returns:
            dict[]: フラグが更新された結果レコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        flag = False if set_flag == 0 else True
        records = session.query(Favorite).filter(Favorite.img_filename.in_(file_list)).all()
        for record in records:
            record.is_exist_saved_file = flag

        res_dict = [r.toDict() for r in records]  # 辞書リストに変換

        session.commit()
        session.close()

        return res_dict

    def FlagClear(self):
        """Favorite中のis_exist_saved_fileフラグをすべて0に更新する

        Note:
            "update Favorite set is_exist_saved_file = 0"

        Returns:
             int: 0(成功)
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        records = session.query(Favorite).filter(Favorite.is_exist_saved_file == "True").all()
        for record in records:
            record.is_exist_saved_file = False

        session.commit()
        session.close()

        return 0


if __name__ == "__main__":
    DEBUG = True
    db_fullpath = Path("J:\\twitter") / "PG_DB.db"
    db_cont = FavDBController(db_fullpath=str(db_fullpath), save_operation=True)
    # db_cont.DBReflectFromFile("./archive/operatefile.txt")
    pass
