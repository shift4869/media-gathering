import re
import sys
import urllib.parse
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

import orjson

from media_gathering.LinkSearch.FetcherBase import FetcherBase
from media_gathering.LinkSearch.LinkSearcher import LinkSearcher
from media_gathering.Model import ExternalLink
from media_gathering.tac.TweetInfo import TweetInfo
from media_gathering.Util import Result, find_values


class ParserBase(metaclass=ABCMeta):
    fetched_tweets: list[dict]
    link_searcher: LinkSearcher

    def __init__(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> None:
        if not isinstance(fetched_tweets, list):
            raise TypeError("fetched_tweets must be list.")
        if not all([isinstance(t, dict) for t in fetched_tweets]):
            raise TypeError("fetched_tweets[] element must be dict.")
        if not isinstance(link_searcher, LinkSearcher):
            raise TypeError("link_searcher must be LinkSearcher.")
        self.fetched_tweets = fetched_tweets
        self.link_searcher = link_searcher

    def _interpret_resister(self, tweet: dict, result: list[dict], seen_id: list[str]) -> Result:
        """tweet を result に追加する前に、本当に追加して良いか調べる

        Args:
            tweet (dict): 対象ツイートオブジェクト辞書
            result (list[dict]): 結果保存用リスト
            seen_id (list): 既に追加済の tweet_id リスト

        Returns:
            Result: tweet を result に追加成功したら Result.success
                    追加失敗したら Result.failed
        """
        try:
            # _match_data の形式 {"core", "legacy", "source"} を直下に持つか
            data = self._match_data(tweet)
            if not data:
                return Result.failed

            # extended_entities を持つか
            extended_entities = find_values(tweet, "extended_entities", False, ["legacy"])
            if not extended_entities:
                # entities を持つか
                entities = find_values(tweet, "entities", False, ["legacy"])
                if not entities:
                    # extended_entities も entities も持っていない場合はfailed
                    return Result.failed

            # 既に追加済の tweet_id か
            id_str = find_values(tweet, "id_str", True, ["legacy"])
            if id_str in seen_id:
                return Result.failed

            # result に追加
            result.append(tweet)
            seen_id.append(id_str)
            return Result.success
        except Exception:
            return Result.failed

    @abstractmethod
    def _interpret(self, tweet: dict) -> list[dict]:
        """ツイートオブジェクトの辞書構成をたどり、ツイートがメディアを含むかどうか調べる

        Args:
            tweet (dict): ツイートオブジェクト辞書

        Returns:
            result list[dict]: 結果辞書リスト
        """
        raise NotImplementedError

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
                via = re.findall(r"^<.+?>([^<]*?)<.+?>$", via_html)[0]
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
                "extended_entities": extended_entities,
                "full_text": full_text,
                "id_str": id_str,
                "user_id_str": author_id,
            }:
                result = {
                    "author_id": author_id,
                    "created_at": created_at,
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
                bitrate = -sys.maxsize
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

    def parse_to_TweetInfo(self) -> list[TweetInfo]:
        """取得した TL ツイートオブジェクトから TweetInfo リストを作成する

        Returns:
            list[TweetInfo]: TweetInfo リスト
        """
        # 辞書パース
        # fetched_tweets は TL 内のツイートが入っている想定
        # media を含むかどうかはこの時点では don't care
        target_data_list: list[dict] = []
        tweet_results: list[dict] = find_values(self.fetched_tweets, "tweet_results")
        for t in tweet_results:
            t1 = t.get("result", {})
            if t2 := self._interpret(t1):
                target_data_list.extend(t2)

        if not target_data_list:
            # 辞書パースエラー or 1件も TL にツイートが無かった
            # raise ValueError("no tweet included in fetched_tweets.")
            return []

        # target_data_list を入力として media 情報を収集
        # media 情報を含むかどうかを確認しつつ、対象ならば収集する
        seen_ids: list[str] = []
        result: list[TweetInfo] = []
        for data in target_data_list:
            try:
                data_dict = self._match_data(data)
                if not data_dict:
                    continue
                author = data_dict["author"]
                tweet = data_dict["tweet"]
                via = data_dict["via"]
                user_name, screan_name = author["name"], author["screen_name"]
                tweet_via = via

                tweet_dict = self._match_extended_entities_tweet(tweet)
                if not tweet_dict:
                    continue
                author_id = tweet_dict["author_id"]
                created_at = tweet_dict["created_at"]
                extended_entities = tweet_dict["extended_entities"]
                id_str = tweet_dict["id_str"]
                tweet_text = tweet_dict["text"]
                user_id = author_id

                if id_str in seen_ids:
                    continue

                # tweet_url を取得
                # entities 内の expanded_url を採用する
                # ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
                tweet_url = extended_entities["media"][0]["expanded_url"]

                # created_at を解釈する
                td_format = "%a %b %d %H:%M:%S +0000 %Y"
                dts_format = "%Y-%m-%d %H:%M:%S"
                jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
                dst = jst.strftime(dts_format)

                # media 情報について収集する
                # 1ツイートに対して media は最大4つ添付されている
                media_list = extended_entities["media"]
                for media in media_list:
                    media_dict = self._match_media(media)
                    if not media_dict:
                        continue
                    media_filename = media_dict["media_filename"]
                    media_url = media_dict["media_url"]
                    media_thumbnail_url = media_dict["media_thumbnail_url"]

                    # resultレコード作成
                    tweet = {
                        "media_filename": media_filename,
                        "media_url": media_url,
                        "media_thumbnail_url": media_thumbnail_url,
                        "tweet_id": id_str,
                        "tweet_url": tweet_url,
                        "created_at": dst,
                        "user_id": user_id,
                        "user_name": user_name,
                        "screan_name": screan_name,
                        "tweet_text": tweet_text,
                        "tweet_via": tweet_via,
                    }
                    result.append(TweetInfo.create(tweet))

                    if id_str not in seen_ids:
                        seen_ids.append(id_str)
            except KeyError:
                continue
        result.reverse()
        return result

    def parse_to_ExternalLink(self) -> list[ExternalLink]:
        """取得した TL ツイートオブジェクトから ExternalLink のリストを返す
 
        Returns:
            list[ExternalLink]: ExternalLink リスト
        """
        # 辞書パース
        # 外部リンクを含むかどうかはこの時点では don't care
        target_data_list: list[dict] = []
        tweet_results: list[dict] = find_values(self.fetched_tweets, "tweet_results")
        for t in tweet_results:
            t1 = t.get("result", {})
            if t2 := self._interpret(t1):
                target_data_list.extend(t2)

        if not target_data_list:
            # 辞書パースエラー or 1件もツイートが無かった
            # raise ValueError("no tweet included in fetched_tweets.")
            return []

        # target_data_list を入力として 外部リンク情報を収集
        # 外部リンク情報を含むかどうかを確認しつつ、対象ならば収集する
        seen_ids: list[str] = []
        result: list[ExternalLink] = []
        for data in target_data_list:
            try:
                data_dict = self._match_data(data)
                if not data_dict:
                    continue
                author = data_dict["author"]
                tweet = data_dict["tweet"]
                via = data_dict["via"]
                user_name, screan_name = author["name"], author["screen_name"]
                tweet_via = via

                tweet_dict = self._match_entities_tweet(tweet)
                if not tweet_dict:
                    continue
                author_id = tweet_dict["author_id"]
                created_at = tweet_dict["created_at"]
                entities = tweet_dict["entities"]
                tweet_text = tweet_dict["text"]
                id_str = tweet_dict["id_str"]
                user_id = author_id
                tweet_id = id_str

                if tweet_id in seen_ids:
                    continue

                # tweet_url は screan_name と tweet_id から生成する
                tweet_url = f"https://twitter.com/{screan_name}/status/{tweet_id}"

                # created_at を解釈する
                td_format = "%a %b %d %H:%M:%S +0000 %Y"
                dts_format = "%Y-%m-%d %H:%M:%S"
                jst = datetime.strptime(created_at, td_format) + timedelta(hours=9)
                dst = jst.strftime(dts_format)

                # 保存時間は現在時刻とする
                saved_created_at = datetime.now().strftime(dts_format)

                # expanded_url を収集する
                expanded_urls = self._match_entities(entities).get("expanded_urls", [])
                link_type = ""

                # 外部リンクについて対象かどうか判定する
                for expanded_url in expanded_urls:
                    if not self.link_searcher.can_fetch(expanded_url):
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
            except KeyError:
                continue
        result.reverse()
        return result


if __name__ == "__main__":
    from media_gathering.LinkSearch.FetcherBase import FetcherBase
    from media_gathering.LinkSearch.URL import URL
    from media_gathering.tac.LikeParser import LikeParser

    # キャッシュから読み込み
    base_path = Path("./test/tac/cache/expect/content_cache_likes_test.json")
    # base_path = Path("./PictureGathering/tac/cache/likes_00.json")
    fetched_tweets = orjson.loads(base_path.read_bytes())

    # インスタンス作成
    class SampleFetcher(FetcherBase):
        def is_target_url(self, url: URL):
            estimated_url = url.non_query_url
            f1 = re.search(r"^https://www.pixiv.net/artworks/[0-9]+", estimated_url) is not None
            return f1

        def fetch(self):
            pass
    sample_fetcher = SampleFetcher()
    link_searcher = LinkSearcher()
    link_searcher.register(sample_fetcher)
    parser = LikeParser([fetched_tweets], link_searcher)

    # TweetInfo リスト取得
    tweet_info_list = parser.parse_to_TweetInfo()
    print(len(tweet_info_list))

    # 外部リンク取得
    external_link_list = parser.parse_to_ExternalLink()
    print(len(external_link_list))
