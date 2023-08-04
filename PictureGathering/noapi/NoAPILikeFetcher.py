# coding: utf-8
import json
import pprint
import re
import shutil
import sys
import urllib.parse
from datetime import datetime, timedelta
from logging import INFO, getLogger
from pathlib import Path

from twitter.scraper import Scraper

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.Model import ExternalLink
from PictureGathering.noapi.TweetInfo import TweetInfo
from PictureGathering.noapi.Username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


class NoAPILikeFetcher():
    ct0: str
    auth_token: str
    target_screen_name: Username
    target_id: int

    # キャッシュファイルパス
    TWITTER_CACHE_PATH = Path(__file__).parent / "cache/"

    def __init__(self, ct0: str, auth_token: str, target_username: Username | str, target_id: int) -> None:
        self.ct0 = ct0
        self.auth_token = auth_token
        if isinstance(target_username, Username):
            target_username = target_username.name
        self.target_username = Username(target_username)
        self.target_id = int(target_id)

    def get_like_jsons(self, max_scroll: int = 40, each_scroll_wait: float = 1.5) -> list[dict]:
        logger.info("Fetched Tweet by TAC -> start")

        # キャッシュ保存場所の準備
        base_path = Path(self.TWITTER_CACHE_PATH)
        if base_path.is_dir():
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # TAC で likes ページをスクレイピング
        scraper = Scraper(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
        likes = scraper.likes([self.target_id], limit=400)

        # キャッシュに保存
        for i, like in enumerate(likes):
            with Path(base_path / f"likes_{i:02}.json").open("w", encoding="utf8") as fout:
                json.dump(like, fout, indent=4, sort_keys=True)

        # キャッシュから読み込み
        # 保存して読み込みをするのでほぼ同一の内容になる
        # 違いは result は json.dump→json.load したときに、エンコード等が吸収されていること
        result: list[dict] = []
        n = len(likes)
        for i in range(n):
            with Path(base_path / f"likes_{i:02}.json").open("r", encoding="utf8") as fin:
                json_dict = json.load(fin)
                result.append(json_dict)

        logger.info("Fetched Tweet by TAC -> done")
        return result

    def interpret_json(self, tweet: dict) -> list[dict]:
        """ツイートオブジェクトの辞書構成をたどり、ツイートがメディアを含むかどうか調べる

        Note:
            主に legacy を直下に含むツイートオブジェクトを引数として受け取り
            以下のように result を返す
            (1)ツイートにメディアが添付されている場合
                result に tweet を追加
            (2)ツイートに外部リンクが含まれている場合
                result に tweet を追加
            (3)メディアが添付されているツイートがRTされている場合
                result に tweet.retweeted_status_result.result を追加
            (4)メディアが添付されているツイートが引用RTされている場合
                result に tweet.quoted_status_result.result を追加
            (5)メディアが添付されているツイートの引用RTがRTされている場合
                result に tweet.retweeted_status_result.result.quoted_status_result.result を追加

            引用RTはRTできるがRTは引用RTできない
            (3)~(5)のケースで、メディアを含んでいるツイートがたどる途中にあった場合、それもresultに格納する
            id_strが重複しているツイートは格納しない

        Args:
            tweet (dict): ツイートオブジェクト辞書

        Returns:
            result list[dict]: 上記にて出力された辞書リスト
        """
        if not isinstance(tweet, dict):
            raise TypeError("argument tweet is not dict.")

        # 返信できるアカウントを制限しているときなど階層が異なる場合がある
        if "tweet" in tweet:
            tweet = tweet.get("tweet")

        result = []
        id_str_list = []

        # (1)ツイートにメディアが添付されている場合
        match tweet:
            case {
                "legacy": {
                    "extended_entities": {
                        "media": _
                    },
                    "id_str": id_str,
                },
            } if id_str not in id_str_list:
                result.append(tweet)
                id_str_list.append(id_str)

        # (2)ツイートに外部リンクが含まれている場合
        match tweet:
            case {
                "legacy": {
                    "entities": {
                        "urls": urls_dict,
                    },
                    "id_str": id_str,
                },
            } if id_str not in id_str_list:
                if isinstance(urls_dict, list):
                    url_flags = [url_dict.get("expanded_url", "") != "" for url_dict in urls_dict]
                    if any(url_flags):
                        result.append(tweet)
                        id_str_list.append(id_str)

        # (3)メディアが添付されているツイートがRTされている場合
        match tweet:
            case {
                "legacy": {
                    "retweeted": True,
                },
                "retweeted_status_result": {
                    "result": {
                        "legacy": {
                            "extended_entities": _,
                            "id_str": id_str,
                        },
                    },
                },
            } if id_str not in id_str_list:
                retweeted_tweet = tweet.get("retweeted_status_result", {}).get("result", {})
                result.append(retweeted_tweet)
                id_str_list.append(id_str)

        # (4)メディアが添付されているツイートが引用RTされている場合
        match tweet:
            case {
                "legacy": {
                    "is_quote_status": True,
                },
                "quoted_status_result": {
                    "result": {
                        "legacy": {
                            "extended_entities": _,
                            "id_str": id_str,
                        },
                    },
                },
            } if id_str not in id_str_list:
                quoted_tweet = tweet.get("quoted_status_result", {}).get("result", {})
                result.append(quoted_tweet)
                id_str_list.append(id_str)

        # (5)メディアが添付されているツイートの引用RTがRTされている場合
        match tweet:
            case {
                "legacy": {
                    "retweeted": True,
                },
                "retweeted_status_result": {
                    "result": {
                        "is_quote_status": True,
                        "quoted_status_result": {
                            "result": {
                                "legacy": {
                                    "extended_entities": _,
                                    "id_str": id_str,
                                },
                            },
                        },
                    },
                },
            } if id_str not in id_str_list:
                retweeted_tweet = tweet.get("retweeted_status_result", {}).get("result", {})
                quoted_tweet = retweeted_tweet.get("quoted_status_result", {}).get("result", {})
                result.append(quoted_tweet)
                id_str_list.append(id_str)

        return result

    def fetch(self) -> list[dict]:
        """Likes ページをクロールしてロード時のJSONをキャプチャする

        Returns:
            list[dict]: ツイートオブジェクトを表すJSONリスト
        """
        result = self.get_like_jsons()
        return result

    def _match_data(self, data: dict) -> dict:
        """ツイートオブジェクトのルート解析用match

        Args:
            data (dict): ツイートオブジェクトのルート

        Returns:
            result (dict): data がmatchした場合 result, そうでなければ空辞書
        """
        match data:
            case {
                "core": {"user_results": {"result": {"legacy": author}}},
                "legacy": tweet,
                "source": via_html,
            }:
                via = re.findall("^<.+?>([^<]*?)<.+?>$", via_html)[0]
                result = {
                    "author": author,
                    "tweet": tweet,
                    "via": via,
                }
                return result
        return {}

    def _match_extended_entities_tweet(self, tweet: dict) -> dict:
        """ツイートオブジェクトに主に extended_entities が含まれるかのmatch

        Args:
            tweet (dict): ツイートオブジェクトの legacy ツイート
                          _match_data.tweet を想定

        Returns:
            result (dict): tweet がmatchした場合 result, そうでなければ空辞書
        """
        match tweet:
            case {
                "created_at": created_at,
                # "entities": entities,
                "extended_entities": extended_entities,
                "full_text": full_text,
                "id_str": id_str,
                "user_id_str": author_id,
                # "source": via,
            }:
                result = {
                    "author_id": author_id,
                    "created_at": created_at,
                    # "entities": entities,
                    "extended_entities": extended_entities,
                    "id_str": id_str,
                    "text": full_text,
                }
                return result
        return {}

    def _match_entities_tweet(self, tweet: dict) -> dict:
        """ツイートオブジェクトに主に entities が含まれるかのmatch

        Args:
            tweet (dict): ツイートオブジェクトの legacy ツイート
                          _match_data.tweet を想定

        Returns:
            result (dict): tweet がmatchした場合 result, そうでなければ空辞書
        """
        match tweet:
            case {
                "created_at": created_at,
                "entities": entities,
                "full_text": full_text,
                "id_str": id_str,
                "user_id_str": author_id,
                # "source": via,
            }:
                r = {
                    "author_id": author_id,
                    "created_at": created_at,
                    "entities": entities,
                    "id_str": id_str,
                    "text": full_text,
                }
                return r
        return {}

    def _match_entities(self, entities: dict) -> dict:
        """entities に含まれる expanded_url を収集するためのmatch

        Args:
            entities (dict): _match_entities_tweet.entities

        Returns:
            expanded_urls (dict): entities に含まれる expanded_url のみを抽出した辞書, 解析失敗時は空辞書
        """
        match entities:
            case {"urls": urls_dict}:
                expanded_urls = []
                for url_dict in urls_dict:
                    expanded_url = url_dict.get("expanded_url", "")
                    if not expanded_url:
                        continue
                    expanded_urls.append(expanded_url)
                return {"expanded_urls": expanded_urls}
        return {}

    def _match_media(self, media: dict) -> dict:
        """mediaから保存対象のメディアURLを取得する

        Args:
            media_dict (dict): _match_extended_entities_tweet.extended_entities.media

        Returns:
            result (dict): 成功時 result, そうでなければ空辞書
        """
        match media:
            case {
                "type": "photo",
                "media_url_https": media_url,
            }:
                media_filename = Path(media_url).name
                media_thumbnail_url = media_url + ":large"
                media_url = media_url + ":orig"
                result = {
                    "media_filename": media_filename,
                    "media_url": media_url,
                    "media_thumbnail_url": media_thumbnail_url,
                }
                return result
            case {
                "type": "video" | "animated_gif",
                "video_info": {"variants": video_variants},
                "media_url_https": media_thumbnail_url,
            }:
                media_url = ""
                bitrate = -sys.maxsize  # 最小値
                for video_variant in video_variants:
                    if video_variant["content_type"] == "video/mp4":
                        if int(video_variant["bitrate"]) > bitrate:
                            # 同じ動画の中で一番ビットレートが高い動画を保存する
                            media_url = video_variant["url"]
                            bitrate = int(video_variant["bitrate"])
                # クエリを除去
                url_path = Path(urllib.parse.urlparse(media_url).path)
                media_url = urllib.parse.urljoin(media_url, url_path.name)
                media_filename = Path(media_url).name
                media_thumbnail_url = media_thumbnail_url + ":orig"
                result = {
                    "media_filename": media_filename,
                    "media_url": media_url,
                    "media_thumbnail_url": media_thumbnail_url,
                }
                return result
        return {}

    def to_convert_TweetInfo(self, fetched_tweets: list[dict]) -> list[TweetInfo]:
        """取得した Likes ツイートオブジェクトから TweetInfo リストを作成する

        Args:
            fetched_tweets (list[dict]): self.fetch() 後の返り値

        Returns:
            list[TweetInfo]: TweetInfo リスト
        """
        if not isinstance(fetched_tweets, list):
            return []
        if not isinstance(fetched_tweets[0], dict):
            return []

        # 辞書パース
        # fetched_tweets は Likes のツイートが入っている想定
        # media を含むかどうかはこの時点では don't care
        target_data_list: list[dict] = []
        for r in fetched_tweets:
            r1 = r.get("data", {}) \
                  .get("user", {}) \
                  .get("result", {}) \
                  .get("timeline_v2", {}) \
                  .get("timeline", {}) \
                  .get("instructions", [{}])[0]
            if not r1:
                continue
            entries: list[dict] = r1.get("entries", [])
            for entry in entries:
                e1 = entry.get("content", {}) \
                          .get("itemContent", {}) \
                          .get("tweet_results", {}) \
                          .get("result", {})
                t = self.interpret_json(e1)
                if not t:
                    continue
                target_data_list.extend(t)

        if not target_data_list:
            # 辞書パースエラー or 1件も Likes にツイートが無かった
            # raise ValueError("no tweet included in fetched_tweets.")
            return []

        # target_data_list を入力として media 情報を収集
        # media 情報を含むかどうかを確認しつつ、対象ならば収集する
        seen_ids: list[str] = []
        result: list[TweetInfo] = []
        for data in target_data_list:
            data_dict = self._match_data(data)
            if not data_dict:
                continue
            author = data_dict.get("author", {})
            tweet = data_dict.get("tweet", {})
            via = data_dict.get("via", "")

            tweet_dict = self._match_extended_entities_tweet(tweet)
            if not tweet_dict:
                continue
            created_at = tweet_dict.get("created_at", "")
            extended_entities = tweet_dict.get("extended_entities", {})
            tweet_text = tweet_dict.get("text", "")
            author_id = tweet_dict.get("author_id", "")
            id_str = tweet_dict.get("id_str", "")

            liked_tweet_id = id_str
            tweet_via = via

            if liked_tweet_id in seen_ids:
                continue

            user_id = author_id
            user_name, screan_name = author.get("name"), author.get("screen_name")

            # tweet_url を取得
            # entities 内の expanded_url を採用する
            # ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
            tweet_url = extended_entities.get("media", [{}])[0].get("expanded_url", "")

            # created_at を解釈する
            # Like した時点の時間が取得できる？
            td_format = "%a %b %d %H:%M:%S +0000 %Y"
            dts_format = "%Y-%m-%d %H:%M:%S"
            jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
            dst = jst.strftime(dts_format)

            # media 情報について収集する
            # 1ツイートに対して media は最大4つ添付されている
            media_list = extended_entities.get("media", [])
            for media in media_list:
                media_dict = self._match_media(media)
                if not media_dict:
                    continue
                media_filename = media_dict.get("media_filename", "")
                media_url = media_dict.get("media_url", "")
                media_thumbnail_url = media_dict.get("media_thumbnail_url", "")

                # resultレコード作成
                r = {
                    "media_filename": media_filename,
                    "media_url": media_url,
                    "media_thumbnail_url": media_thumbnail_url,
                    "tweet_id": liked_tweet_id,
                    "tweet_url": tweet_url,
                    "created_at": dst,
                    "user_id": user_id,
                    "user_name": user_name,
                    "screan_name": screan_name,
                    "tweet_text": tweet_text,
                    "tweet_via": tweet_via,
                }
                result.append(TweetInfo.create(r))

                if liked_tweet_id not in seen_ids:
                    seen_ids.append(liked_tweet_id)
        result.reverse()
        return result

    def to_convert_ExternalLink(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        """取得した Likes ツイートオブジェクトから ExternalLink のリストを返す

        Args:
            fetched_tweets (list[dict]): self.fetch() 後の返り値
            link_searcher (LinkSearcher): 外部リンク探索用LinkSearcher
 
        Returns:
            list[ExternalLink]: ExternalLink リスト
        """
        if not isinstance(fetched_tweets, list):
            return []
        if not isinstance(fetched_tweets[0], dict):
            return []
        if not isinstance(link_searcher, LinkSearcher):
            return []

        # 辞書パース
        # 外部リンクを含むかどうかはこの時点では don't care
        target_data_list = []
        for r in fetched_tweets:
            r1 = r.get("data", {}) \
                  .get("user", {}) \
                  .get("result", {}) \
                  .get("timeline_v2", {}) \
                  .get("timeline", {}) \
                  .get("instructions", [{}])[0]
            if not r1:
                continue
            entries: list[dict] = r1.get("entries", [])
            for entry in entries:
                e1 = entry.get("content", {}) \
                          .get("itemContent", {}) \
                          .get("tweet_results", {}) \
                          .get("result", {})
                t = self.interpret_json(e1)
                if not t:
                    continue
                target_data_list.extend(t)

        if not target_data_list:
            # 辞書パースエラー or 1件もツイートが無かった
            # raise ValueError("no tweet included in fetched_tweets.")
            return []

        # target_data_list を入力として 外部リンク情報を収集
        # 外部リンク情報を含むかどうかを確認しつつ、対象ならば収集する
        seen_ids: list[str] = []
        result: list[ExternalLink] = []
        for data in target_data_list:
            data_dict = self._match_data(data)
            if not data_dict:
                continue
            author = data_dict.get("author", {})
            tweet = data_dict.get("tweet", {})
            via = data_dict.get("via", "")

            tweet_dict = self._match_entities_tweet(tweet)
            if not tweet_dict:
                continue
            created_at = tweet_dict.get("created_at", "")
            entities = tweet_dict.get("entities", {})
            tweet_text = tweet_dict.get("text", "")
            author_id = tweet_dict.get("author_id", "")
            id_str = tweet_dict.get("id_str", "")

            tweet_id = id_str
            tweet_via = via
            link_type = ""

            if tweet_id in seen_ids:
                continue

            user_id = author_id
            user_name, screan_name = author.get("name"), author.get("screen_name")

            # tweet_url は screan_name と tweet_id から生成する
            tweet_url = f"https://twitter.com/{screan_name}/status/{tweet_id}"

            # created_at を解釈する
            # Like した時点の時間が取得できる？
            td_format = "%a %b %d %H:%M:%S +0000 %Y"
            dts_format = "%Y-%m-%d %H:%M:%S"
            jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
            dst = jst.strftime(dts_format)

            # 保存時間は現在時刻とする
            saved_created_at = datetime.now().strftime(dts_format)

            # expanded_url を収集する
            expanded_urls = self._match_entities(entities).get("expanded_urls", [])

            # 外部リンクについて対象かどうか判定する
            for expanded_url in expanded_urls:
                if not link_searcher.can_fetch(expanded_url):
                    continue

                # resultレコード作成
                r = {
                    "external_link_url": expanded_url,
                    "tweet_id": tweet_id,
                    "tweet_url": tweet_url,
                    "created_at": dst,
                    "user_id": user_id,
                    "user_name": user_name,
                    "screan_name": screan_name,
                    "tweet_text": tweet_text,
                    "tweet_via": tweet_via,
                    "saved_created_at": saved_created_at,
                    "link_type": link_type,
                }
                result.append(ExternalLink.create(r))

                if tweet_id not in seen_ids:
                    seen_ids.append(tweet_id)
        result.reverse()
        return result


if __name__ == "__main__":
    import configparser
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_api_client"]
    ct0 = config["ct0"]
    auth_token = config["auth_token"]
    target_screen_name = config["target_screen_name"]
    target_id = config["target_id"]
    like = NoAPILikeFetcher(ct0, auth_token, target_screen_name, target_id)

    # like取得
    fetched_tweets = like.fetch()

    # キャッシュから読み込み
    base_path = Path(like.TWITTER_CACHE_PATH)
    fetched_tweets = []
    for cache_path in base_path.glob("*likes*"):
        with cache_path.open("r", encoding="utf8") as fin:
            json_dict = json.load(fin)
            fetched_tweets.append(json_dict)

    # メディア取得
    tweet_info_list = like.to_convert_TweetInfo(fetched_tweets)
    # pprint.pprint(tweet_info_list)
    pprint.pprint(len(tweet_info_list))

    # 外部リンク取得
    config = config_parser
    config["skeb"]["is_skeb_trace"] = "False"
    lsb = LinkSearcher.create(config)
    external_link_list = like.to_convert_ExternalLink(fetched_tweets, lsb)
    # pprint.pprint(external_link_list)
    pprint.pprint(len(external_link_list))
