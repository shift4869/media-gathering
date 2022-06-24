# coding: utf-8
import random
from datetime import datetime
from logging import DEBUG, INFO, getLogger
from pathlib import Path

from PictureGathering.Crawler import Crawler
from PictureGathering.RetweetDBController import RetweetDBController

logger = getLogger("root")
logger.setLevel(INFO)


class RetweetCrawler(Crawler):
    def __init__(self):
        super().__init__()
        try:
            config = self.config["db"]
            save_path = Path(config["save_path"])
            save_path.mkdir(parents=True, exist_ok=True)
            db_fullpath = save_path / config["save_file_name"]
            self.db_cont = RetweetDBController(db_fullpath, False)  # テーブルはRetweetを使用
            if config.getboolean("save_permanent_image_flag"):
                Path(config["save_permanent_image_path"]).mkdir(parents=True, exist_ok=True)

            self.retweet_get_max_loop = int(self.config["tweet_timeline"]["retweet_get_max_loop"])
            self.max_id = None
            self.save_path = Path(self.config["save_directory"]["save_retweet_path"])
            self.type = "RT"
        except KeyError:
            logger.exception("invalid config file eeror.")
            exit(-1)

    def RetweetsGet(self):
        url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        rt_tweets = []
        holding_num = int(self.config["holding"]["holding_file_num"])

        # 存在マーキングをクリアする
        self.db_cont.FlagClear()

        # 既存ファイル一覧を取得する
        exist_filepaths = self.GetExistFilelist()
        exist_filenames = []
        for exist_filepath in exist_filepaths:
            exist_filenames.append(Path(exist_filepath).name)
        if exist_filenames:
            exist_oldest_filename = exist_filenames[-1]
        else:
            exist_oldest_filename = ""

        # 存在マーキングを更新する
        self.db_cont.FlagUpdate(exist_filenames, 1)

        get_cnt = 0
        end_flag = False
        expect_filenames = []
        for i in range(1, self.retweet_get_max_loop):
            # タイムラインツイート取得
            params = {
                "screen_name": self.user_name,
                "count": self.count,
                "max_id": self.max_id,
                "contributor_details": True,
                "include_rts": True,
                "tweet_mode": "extended"
            }
            timeline_tweets = self.TwitterAPIRequest(url, params)

            for t in timeline_tweets:
                # RTまたは引用RTフラグが立っているツイートのみ対象とする
                rt_flag = t.get("retweeted")
                quote_flag = t.get("is_quote_status")
                if not (rt_flag or quote_flag):
                    continue

                # メディアを保持しているツイート部分を取得
                media_tweets = self.GetMediaTweet(t)

                if not media_tweets:
                    continue

                # 取得したメディアツイートツリー（複数想定）
                for media_tweet in media_tweets:
                    # 引用RTなどのツリーで関係ツイートが複数ある場合は最新の日時を一律付与する
                    media_tweet["created_at"] = media_tweets[-1]["created_at"]

                    entities = media_tweet.get("extended_entities")
                    include_new_flag = False
                    if not entities:
                        # 外部リンクが含まれているか
                        if media_tweet.get("entities"):
                            e_urls = media_tweet["entities"].get("urls")
                            for element in e_urls:
                                expanded_url = element.get("expanded_url")
                                if self.lsb.can_fetch(expanded_url):
                                    include_new_flag = True
                        pass
                    else:
                        # 一つでも保存していない画像を含んでいるか判定
                        for entity in entities["media"]:
                            media_url = self.GetMediaUrl(entity)
                            filename = Path(media_url).name

                            # 既存ファイルの最後のファイル名と一致したら探索を途中で打ち切る
                            if filename == exist_oldest_filename:
                                end_flag = True

                            # 現在保存場所に存在しないファイル　かつ
                            # これから収集される予定の、既に収集済のファイルでもない ならば
                            # そのツイートを収集対象とする
                            if filename not in exist_filenames:
                                if filename not in expect_filenames:
                                    include_new_flag = True
                                    expect_filenames.append(filename)
                                    # break

                    # 一つでも保存していない画像を含んでいたらツイートを収集する
                    if include_new_flag:
                        # ツイートオブジェクトの階層を加味して既に取得しているので、
                        # 収集時にはRT,引用RTフラグを消しておく
                        # これによりCrawlerでの解釈時に重複して階層取得することを防ぐ
                        if media_tweet.get("retweeted"):
                            media_tweet["retweeted"] = False
                            if media_tweet.get("retweeted_status"):
                                media_tweet["retweeted_status"] = {"modified_by_crawler": True}
                        if media_tweet.get("is_quote_status"):
                            media_tweet["is_quote_status"] = False
                            if media_tweet.get("quoted_status"):
                                media_tweet["quoted_status"] = {"modified_by_crawler": True}

                        rt_tweets.append(media_tweet)
                        get_cnt = get_cnt + 1

                # 探索を途中で打ち切る
                if end_flag:
                    break

            # 次のRTから取得する
            self.max_id = timeline_tweets[-1]['id'] - 1

            # 収集したツイートが保持数を超えたor既存ファイルの最後まで探索した場合break
            if get_cnt > holding_num or end_flag:
                break

        # 古い順にする
        rt_tweets.reverse()

        return rt_tweets

    def MakeDoneMessage(self):
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Retweet PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images.".format(self.del_cnt)
        done_msg += "\n"

        # 画像URLをランダムにピックアップする
        random_pickup = True
        if random_pickup:
            pickup_url_list = random.sample(self.add_url_list, min(4, len(self.add_url_list)))
            for pickup_url in pickup_url_list:
                pickup_url = str(pickup_url).replace(":orig", "")
                done_msg += pickup_url + "\n"

        return done_msg

    def Crawl(self):
        logger.info("Retweet Crawler crawl start.")
        tweets = self.RetweetsGet()
        self.InterpretTweets(tweets)
        self.ShrinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()
        return 0


if __name__ == "__main__":
    c = RetweetCrawler()

    # クロール前に保存場所から指定枚数削除しておく
    # c.ShrinkFolder(int(c.config["holding"]["holding_file_num"]) - 10)
    # c.del_cnt = 0
    # c.del_url_list = []

    c.Crawl()
