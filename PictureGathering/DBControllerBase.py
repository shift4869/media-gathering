# coding: utf-8
import configparser
import pickle
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from abc import ABCMeta, abstractmethod
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from PictureGathering.Model import *


DEBUG = False


class DBControllerBase(metaclass=ABCMeta):
    def __init__(self, db_fullpath="PG_DB.db", save_operation=True):
        self.dbname = db_fullpath
        self.engine = create_engine(f"sqlite:///{self.dbname}", echo=False)
        Base.metadata.create_all(self.engine)

        self.operatefile = None
        if save_operation and not DEBUG:
            self.operatefile = Path("./archive").absolute() / "operatefile.txt"  # 操作履歴保存ファイル
            
            if not self.operatefile.parent.is_dir():
                self.operatefile.parent.mkdir(parents=True, exist_ok=True)
            with self.operatefile.open(mode="w", encoding="utf_8") as fout:
                fout.write("")

    def _GetUpdateParam(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath, include_blob):
        """DBにUPSERTする際のパラメータを作成する

        Notes:
            include_blobがTrueのとき、save_file_fullpathを読み込み、blobとしてDBに格納する
            そのためinclude_blobをTrueで呼び出す場合は、その前にsave_file_fullpathに
            メディアファイルが保存されていなければならない

        Args:
            file_name (str): ファイル名
            url_orig (str): メディアURL
            url_thumbnail (str): サムネイルメディアURL
            tweet (dict): ツイート
            save_file_fullpath (str): メディア保存パス（ローカル）
            include_blob (boolean): メディアをblobとして格納するかどうかのフラグ(Trueで格納する)

        Returns:
            dict: DBにUPSERTする際のパラメータをまとめた辞書
        """
        # img_filename,url,url_thumbnail,tweet_id,tweet_url,created_at,
        # user_id,user_name,screan_name,tweet_text,tweet_via,saved_localpath,saved_created_at
        td_format = "%a %b %d %H:%M:%S +0000 %Y"
        dts_format = "%Y-%m-%d %H:%M:%S"
        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format) + timedelta(hours=9)
        text = tweet["text"] if "text" in tweet else tweet["full_text"]
        regex = re.compile(r"<[^>]*?>")
        via = regex.sub("", tweet["source"])
        param = {
            "img_filename": file_name,
            "url": url_orig,
            "url_thumbnail": url_thumbnail,
            "tweet_id": tweet["id_str"],
            "tweet_url": tweet["entities"]["media"][0]["expanded_url"],
            "created_at": dst.strftime(dts_format),
            "user_id": tweet["user"]["id_str"],
            "user_name": tweet["user"]["name"],
            "screan_name": tweet["user"]["screen_name"],
            "tweet_text": text,
            "tweet_via": via,
            "saved_localpath": save_file_fullpath,
            "saved_created_at": datetime.now().strftime(dts_format)
        }

        # media_size,media_blob
        try:
            if include_blob:
                with open(save_file_fullpath, "rb") as fout:
                    param["media_blob"] = fout.read()
                    param["media_size"] = len(param["media_blob"])
            else:
                param["media_blob"] = None
                param["media_size"] = Path(save_file_fullpath).stat().st_size
        except Exception:
            param["media_blob"] = None
            param["media_size"] = -1

        return param

    def _GetDelUpdateParam(self, tweet):
        pattern = " +[0-9]* "
        text = tweet["text"]
        add_num = int(re.findall(pattern, text)[0])
        del_num = int(re.findall(pattern, text)[1])
        td_format = "%a %b %d %H:%M:%S +0000 %Y"
        dts_format = "%Y-%m-%d %H:%M:%S"

        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format) + timedelta(hours=9)
        # tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num
        return {
            "tweet_id": tweet["id_str"],
            "delete_done": False,
            "created_at": dst.strftime(dts_format),
            "deleted_at": None,
            "tweet_text": tweet["text"],
            "add_num": add_num,
            "del_num": del_num
        }

    @abstractmethod
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
        return -1

    @abstractmethod
    def Select(self, limit=300):
        """FavoriteからSELECTする

        Note:
            "select * from Favorite order by created_at desc limit {}".format(limit)

        Args:
            limit (int): 取得レコード数上限

        Returns:
            dict[]: SELECTしたレコードの辞書リスト
        """
        return []

    @abstractmethod
    def SelectFromMediaURL(self, filename):
        """filenameを条件としてSELECTする

        Note:
            "select * from Favorite where img_filename = {}".format(file_name_s)

        Args:
            filename (str): 取得対象のファイル名

        Returns:
            dict[]: SELECTしたレコードの辞書リスト
        """
        return []

    @abstractmethod
    def FlagUpdate(self, file_list=[], set_flag=0):
        """file_listに含まれるファイル名を持つレコードについて
        　 is_exist_saved_fileフラグを更新する

        Note:
            "update Favorite set is_exist_saved_file = {} where img_filename in ({})".format(set_flag, filename)

        Args:
            file_list (list): 取得対象のファイル名リスト
            set_flag (int): セットするフラグ

        Returns:
            dict[]: フラグが更新された結果レコードの辞書リスト
        """
        return []

    @abstractmethod
    def FlagClear(self):
        """Favorite中のis_exist_saved_fileフラグをすべて0に更新する

        Note:
            "update Favorite set is_exist_saved_file = 0"

        Returns:
             int: 0(成功)
        """
        return -1

    def DelUpsert(self, tweet):
        """DeleteTargetにInsertする

        Note:
            insert into DeleteTarget (tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num) values (*)

        Args:
            tweet (dict): Insert対象ツイートオブジェクト

        Returns:
             int: 0(成功)
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()
        res = -1

        # tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num
        param = self._GetDelUpdateParam(tweet)
        r = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                         param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])

        try:
            q = session.query(DeleteTarget).filter(
                or_(DeleteTarget.tweet_id == r.tweet_id))
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
        
        # INSERT
        session.commit()
        session.close()

        # 操作履歴保存
        if self.operatefile and self.operatefile.is_file():
            bname = "DBDelUpsert" + ".bin"
            bin_file_path = self.operatefile.parent / bname
            with bin_file_path.open(mode="wb") as fout:
                pickle.dump(tweet, fout)
            with self.operatefile.open(mode="a", encoding="utf_8") as fout:
                fout.write("DBDelUpsert\n")

        return res

    def DelSelect(self):
        """DeleteTargetからSELECTしてフラグをUPDATEする

        Note:
            2日前の通知ツイートを削除対象とする

        Returns:
             dict[]: 削除対象となる通知ツイートの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        # 2日前の通知ツイートを削除する(1日前の日付より前)
        t = date.today() - timedelta(1)
        # 今日未満 = 昨日以前の通知ツイートをDBから取得
        records = session.query(DeleteTarget).filter(~DeleteTarget.delete_done).\
            filter(DeleteTarget.created_at < t.strftime("%Y-%m-%d %H:%M:%S")).all()

        res_dict = [r.toDict() for r in records]  # 辞書リストに変換

        # 消去フラグを立てる
        for record in records:
            record.delete_done = True
            record.deleted_at = t.strftime("%Y-%m-%d %H:%M:%S")
        session.commit()

        session.close()
        return res_dict

    # def ReflectFromFile(self, operate_file_path):
    #     """操作履歴ファイルから操作を反映する

    #     Returns:
    #          int: 0(成功)
    #     """
    #     fav_upsert_file_list = []
    #     rt_upsert_file_list = []
    #     fp = Path(operate_file_path)
    #     with fp.open(mode="r", encoding="utf_8") as fin:
    #         lines = fin.readlines()
    #         for line_str in lines:
    #             token = re.split("[,\n]", line_str)
    #             params = token[:-1]
    #             if params[0] == "DBFavUpsert":
    #                 bin_file = "DBFavUpsert_" + params[1].split(".")[0] + ".bin"
    #                 with (fp.parent / bin_file).open(mode="rb") as bin:
    #                     tweet = pickle.load(bin)
    #                 self.DBFavUpsert(params[1], params[2], params[3], tweet, params[4], params[5] == "True")
    #                 fav_upsert_file_list.append(params[1])
    #             elif params[0] == "DBRetweetUpsert":
    #                 bin_file = "DBRetweetUpsert_" + params[1].split(".")[0] + ".bin"
    #                 with (fp.parent / bin_file).open(mode="rb") as bin:
    #                     tweet = pickle.load(bin)
    #                 self.DBRetweetUpsert(params[1], params[2], params[3], tweet, params[4], params[5] == "True")
    #                 rt_upsert_file_list.append(params[1])
    #             elif params[0] == "DBDelUpsert":
    #                 bin_file = "DBDelUpsert" + ".bin"
    #                 with (fp.parent / bin_file).open(mode="rb") as bin:
    #                     tweet = pickle.load(bin)
    #                 self.DBDelUpsert(tweet)

    #     if fav_upsert_file_list:
    #         self.DBFavFlagUpdate(fav_upsert_file_list, 1)
    #     if rt_upsert_file_list:
    #         self.DBRetweetFlagUpdate(rt_upsert_file_list, 1)

    #     return 0


if __name__ == "__main__":
    DEBUG = True
    db_fullpath = Path("J:\\twitter") / "PG_DB.db"
    db_cont = DBController(db_fullpath=str(db_fullpath), save_operation=True)
    # db_cont.DBReflectFromFile("./archive/operatefile.txt")
