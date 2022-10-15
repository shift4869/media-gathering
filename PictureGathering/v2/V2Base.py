# coding: utf-8
import json
import pprint
import sys
import urllib
from abc import ABC, abstractmethod
from logging import INFO, getLogger
from pathlib import Path

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.LogMessage import MSG
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.TweetInfo import TweetInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI


logger = getLogger("root")
logger.setLevel(INFO)


class V2Base(ABC):
    pages: str
    api_endpoint_url: str
    params: str
    twitter: TwitterAPI

    def __init__(self, api_endpoint_url: str, params: dict, pages: str, twitter: TwitterAPI) -> None:
        self.api_endpoint_url = api_endpoint_url
        self.params = params
        self.pages = pages
        self.twitter = twitter

    def fetch(self) -> dict:
        """self.api_endpoint_url エンドポイントにて、ツイートを取得する
            self.pages * self.params["max_results"] だけ遡る

        Returns:
            list[dict]: ページごとに格納された API 返り値
        """
        logger.info(MSG.FETCHED_TWEET_BY_TWITTER_API_START.value)
        next_token = ""
        result = []
        for i in range(self.pages):
            if next_token != "":
                self.params["pagination_token"] = next_token
            tweet = self.twitter.get(self.api_endpoint_url, params=self.params)
            result.append(tweet)
            next_token = tweet.get("meta", {}).get("next_token", "")
            logger.info(MSG.FETCHED_TWEET_BY_TWITTER_API_PROGRESS.value.format(i + 1, self.pages))
        logger.info(MSG.FETCHED_TWEET_BY_TWITTER_API_DONE.value)
        return result

    def _find_name(self, user_id: str, users_list: list[str]) -> tuple[str, str]:
        """user_id をキーに user_list を検索する

        Args:
            user_id (str): 検索id
            users_list (list[dict]): 検索対象リスト

        Returns:
            user_name (str), screan_name (str):
                最初に見つかった user 情報から(user_name, screan_name)を返す
                見つからなかった場合、(invalid_name, invalid_name)を返す
        """
        invalid_name = "<null>"
        user_list = [user for user in users_list if user.get("id", "") == user_id]
        if len(user_list) == 0:
            # raise ValueError("(user_name, screan_name) not found.")
            return (invalid_name, invalid_name)
        user = user_list[0]
        user_name = user.get("name", invalid_name)
        screan_name = user.get("username", invalid_name)
        return (user_name, screan_name)

    def _find_media(self, media_key: str, media_list: list[dict]) -> dict:
        """media_key をキーに media_list を検索する

        Args:
            media_key (str): 検索キー
            media_list (list[dict]): 検索対象リスト

        Returns:
            dict: 最初に見つかった media 情報を返す、見つからなかった場合、空辞書を返す
        """
        m_list = [media for media in media_list if media.get("media_key", "") == media_key]
        if len(m_list) == 0:
            # raise ValueError("media not found.")
            return {}
        return m_list[0]
    
    def _match_tweet_url(self, urls: dict) -> str:
        """entities 内の expanded_url を tweet_url として取得する
            ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1

        Args:
            urls (list[dict]): 対象のツイートオブジェクトの一部

        Raises:
            ValueError: tweet_url が見つからなかった場合

        Returns:
            tweet_url (str): 採用された entities 内の expanded_url
        """
        tweet_url = ""
        for url in urls:
            match url:
                case {"expanded_url": expanded_url,
                      "media_key": _}:
                    tweet_url = expanded_url
                    break
                case _:
                    pass
        if tweet_url == "":
            raise ValueError("tweet_url not found.")
        return tweet_url

    def _match_media_info(self, media: dict) -> tuple[str, str, str]:
        """media情報について収集する

        Args:
            media (dict): ツイートオブジェクトの一部

        Returns:
            media_filename (str): ファイル名
            media_url (str): 直リンク
            media_thumbnail_url (str): サムネイル画像直リンク
                エラー時それぞれ空文字列
        """
        media_filename = ""
        media_url = ""
        media_thumbnail_url = ""
        match media:
            case {"media_key": _,
                  "type": "photo",
                  "url": m_url}:
                # 画像
                media_thumbnail_url = m_url + ":large"
                media_url = m_url + ":orig"
                media_filename = Path(m_url).name
            case {"media_key": _,
                  "type": "video" | "animated_gif",
                  "variants": variants,
                  "preview_image_url": p_url}:
                # 動画 or GIF
                m_url = self._match_video_url(variants)
                media_thumbnail_url = p_url + ":orig"
                media_url = m_url
                # クエリを除去
                url_path = Path(urllib.parse.urlparse(media_url).path)
                media_url = urllib.parse.urljoin(media_url, url_path.name)
                media_filename = Path(media_url).name
            case _:
                pass  # 扱えるメディアに紐づくmedia_keyではなかった（エラー？）
        return (media_filename, media_url, media_thumbnail_url)

    def _match_video_url(self, variants: dict) -> str:
        """video情報について収集する
            同じ動画の中で一番ビットレートが高い動画のURLを保存する

        Args:
            variants (dict): ツイートオブジェクトの一部

        Returns:
            video_url (str): 動画直リンク、エラー時空文字列
        """
        video_url = ""
        current_bitrate = -sys.maxsize  # 最小値
        for video_variant in variants:
            match video_variant:
                case {"content_type": "video/mp4",
                      "bit_rate": bitrate,
                      "url": t_url}:
                    bitrate = int(bitrate)
                    if bitrate > current_bitrate:
                        # 同じ動画の中で一番ビットレートが高い動画を保存する
                        video_url = t_url
                        current_bitrate = bitrate
        return video_url

    def _match_expanded_url(self, urls: dict) -> list[str]:
        """entities 内の expanded_url を取得する
            ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
            上記の他に外部リンクも対象とする

        Args:
            urls (dict): ツイートオブジェクトの一部

        Returns:
            list[expanded_url] (list[str]): entities 内の expanded_url をまとめたリスト
        """
        return [url.get("expanded_url", "") for url in urls if "expanded_url" in url]

    @abstractmethod
    def to_convert_TweetInfo(self, fetched_tweets: list[dict]) -> list[TweetInfo]:
        return []

    @abstractmethod
    def to_convert_ExternalLink(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        return []


if __name__ == "__main__":
    import codecs
    import configparser
    from PictureGathering.v2.Like import Like
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_token_keys_v2"]
    twitter = TwitterAPI(
        config["api_key"],
        config["api_key_secret"],
        config["access_token"],
        config["access_token_secret"]
    )

    # 抽象クラスのため直接インスタンス生成はできない
    try:
        v2_base = V2Base(api_endpoint_url="", params={}, pages=3, twitter=twitter)
    except Exception:
        pass

    MY_ID = 175674367
    like = Like(userid=MY_ID, pages=3, max_results=100, twitter=twitter)
    # 実際にAPIを叩いて取得する
    # res = like.fetch()
    # with codecs.open("./PictureGathering/v2/api_response_like_pprint.txt", "w", "utf-8") as fout:
    #     pprint.pprint(res, fout)
    # with codecs.open("./PictureGathering/v2/api_response_like_json.txt", "w", "utf-8") as fout:
    #     json.dump(res, fout)
    # pprint.pprint(res)

    # キャッシュを読み込んでV2BaseInfoリストを作成する
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_like.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = like.to_convert_TweetInfo(input_dict)
    pprint.pprint(res)
    print(len(res))

    # キャッシュを読み込んでExternalLinkリストを作成する
    config = config_parser
    config["skeb"]["is_skeb_trace"] = "False"
    lsb = LinkSearcher.create(config)
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_like.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = like.to_convert_ExternalLink(input_dict, lsb)
    pprint.pprint(res)
    print(len(res))
