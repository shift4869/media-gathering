# coding: utf-8
import configparser
import copy
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.exc import *

from PictureGathering.Model import *


class DBController:
    dbname = 'PG_DB.db'

    def __init__(self):
        self.engine = create_engine(f"sqlite:///{self.dbname}", echo=False)
        Base.metadata.create_all(self.engine)

        self.__fav_sql = self.__GetFavoriteUpsertSQL()
        self.__retweet_sql = self.__GetRetweetUpsertSQL()
        self.__del_sql = self.__GetDeleteTargetUpsertSQL()

    def __GetFavoriteUpsertSQL(self):
        p1 = 'img_filename,url,url_thumbnail,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        return 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'

    def __GetRetweetUpsertSQL(self):
        p1 = 'img_filename,url,url_thumbnail,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        return 'replace into Retweet (' + p1 + p2 + p3 + ') values (' + pn + ')'

    def __GetDeleteTargetUpsertSQL(self):
        p1 = 'tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num'
        pn = '?,?,?,?,?,?,?'
        return 'replace into DeleteTarget (' + p1 + ') values (' + pn + ')'

    def __GetFavoriteSelectSQL(self, limit=300):
        return 'select * from Favorite order by created_at desc limit {}'.format(limit)

    def __GetFavoriteVideoURLSelectSQL(self, filename):
        return 'select * from Favorite where img_filename = {}'.format(filename)

    def __GetRetweetSelectSQL(self, limit=300):
        return 'select * from Retweet where is_exist_saved_file = 1 order by created_at desc limit {}'.format(limit)

    def __GetRetweetVideoURLSelectSQL(self, filename):
        return 'select * from Retweet where img_filename = {}'.format(filename)

    def __GetRetweetFlagUpdateSQL(self, filename="", set_flag=0):
        # filenameはシングルクォート必要、カンマ区切りOK
        return 'update Retweet set is_exist_saved_file = {} where img_filename in ({})'.format(set_flag, filename)

    def __GetRetweetFlagClearSQL(self):
        return 'update Retweet set is_exist_saved_file = 0'

    def __GetUpdateParam(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath):
        # img_filename,url,url_thumbnail,tweet_id,tweet_url,created_at,
        # user_id,user_name,screan_name,tweet_text,saved_localpath,saved_created_at
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
        return param

    def __GetDelUpdateParam(self, tweet):
        pattern = ' +[0-9]* '
        text = tweet["text"]
        add_num = int(re.findall(pattern, text)[0])
        del_num = int(re.findall(pattern, text)[1])
        td_format = '%a %b %d %H:%M:%S +0000 %Y'
        dts_format = '%Y-%m-%d %H:%M:%S'

        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format)
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

    def DBFavUpsert(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath):
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
            
        param = self.__GetUpdateParam(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath)
        r = Favorite(False, param[0], param[1], param[2], param[3], param[4], param[5],
                     param[6], param[7], param[8], param[9], param[10], param[11])

        try:
            q = session.query(Favorite).filter(
                or_(
                    Favorite.img_filename == r.img_filename,
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

        return res

    def DBFavSelect(self, limit=300):
        """FavoriteからSELECTする

        Note:
            'select * from Favorite order by created_at desc limit {}'.format(limit)

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

    def DBFavVideoURLSelect(self, filename):
        """Favoriteからfilenameを条件としてSELECTする

        Note:
            'select * from Favorite where img_filename = {}'.format(file_name_s)

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

    def DBFavFlagUpdate(self, file_list=[], set_flag=0):
        """Favorite中のfile_listに含まれるファイル名を持つレコードについて
        　 is_exist_saved_fileフラグを更新する

        Note:
            'update Favorite set is_exist_saved_file = {} where img_filename in ({})'.format(set_flag, filename)

        Args:
            file_list (list): 取得対象のファイル名リスト　シングルクォート必要、カンマ区切り
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

        session.close()
        return res_dict

    def DBFavFlagClear(self):
        """Favorite中のis_exist_saved_fileフラグをすべて0に更新する

        Note:
            'update Favorite set is_exist_saved_file = 0'

        Returns:
             int: 0(成功)
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        records = session.query(Favorite).filter(Favorite.is_exist_saved_file).all()
        for record in records:
            record.is_exist_saved_file = False

        session.close()

        return 0

    def DBRetweetUpsert(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath):
        """RetweetにUPSERTする

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
            
        param = self.__GetUpdateParam(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath)
        r = Retweet(False, param[0], param[1], param[2], param[3], param[4], param[5],
                    param[6], param[7], param[8], param[9], param[10], param[11])

        try:
            q = session.query(Retweet).filter(
                or_(
                    Retweet.img_filename == r.img_filename,
                    Retweet.url == r.url,
                    Retweet.url_thumbnail == r.url_thumbnail))
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

        return res

    def DBRetweetSelect(self, limit=300):
        """RetweetからSELECTする

        Note:
            'select * from Retweet order by created_at desc limit {}'.format(limit)

        Args:
            limit (int): 取得レコード数上限

        Returns:
            dict[]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(Retweet).order_by(desc(Retweet.created_at)).limit(limit).all()
        res_dict = [r.toDict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict

    def DBRetweetVideoURLSelect(self, filename):
        """Retweetからfilenameを条件としてSELECTする

        Note:
            'select * from Retweet where img_filename = {}'.format(file_name_s)

        Args:
            filename (str): 取得対象のファイル名

        Returns:
            dict[]: SELECTしたレコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        res = session.query(Retweet).filter_by(img_filename=filename).all()
        res_dict = [r.toDict() for r in res]  # 辞書リストに変換

        session.close()
        return res_dict

    def DBRetweetFlagUpdate(self, file_list=[], set_flag=0):
        """Retweet中のfile_listに含まれるファイル名を持つレコードについて
        　 is_exist_saved_fileフラグを更新する

        Note:
            'update Retweet set is_exist_saved_file = {} where img_filename in ({})'.format(set_flag, filename)

        Args:
            file_list (list): 取得対象のファイル名リスト　シングルクォート必要、カンマ区切り
            set_flag (int): セットするフラグ

        Returns:
            dict[]: フラグが更新された結果レコードの辞書リスト
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        flag = False if set_flag == 0 else True
        records = session.query(Retweet).filter(Retweet.img_filename.in_(file_list)).all()
        for record in records:
            record.is_exist_saved_file = flag

        res_dict = [r.toDict() for r in records]  # 辞書リストに変換

        session.close()
        return res_dict

    def DBRetweetFlagClear(self):
        """Retweet中のis_exist_saved_fileフラグをすべて0に更新する

        Note:
            'update Retweet set is_exist_saved_file = 0'

        Returns:
             int: 0(成功)
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        records = session.query(Retweet).filter(Retweet.is_exist_saved_file).all()
        for record in records:
            record.is_exist_saved_file = False

        session.close()

        return 0

    def DBDelInsert(self, tweet):
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

        # tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num
        param = self.__GetDelUpdateParam(tweet)
        record = DeleteTarget(param["tweet_id"], param["delete_done"], param["created_at"],
                              param["deleted_at"], param["tweet_text"], param["add_num"], param["del_num"])
        # INSERT
        session.add(record)
        session.commit()

        session.close()
        return 0

    def DBDelSelect(self):
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
            filter(DeleteTarget.created_at < t.strftime('%Y-%m-%d %H:%M:%S')).all()

        res_dict = [r.toDict() for r in records]  # 辞書リストに変換

        # 消去フラグを立てる
        for record in records:
            record.delete_done = True
            record.deleted_at = t.strftime('%Y-%m-%d %H:%M:%S')
        session.commit()

        session.close()
        return res_dict


if __name__ == "__main__":
    db_cont = DBController()
