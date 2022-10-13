# coding: utf-8
import json
import pprint
import sys
import urllib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.LikeInfo import LikeInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI, TwitterAPIEndpoint


@dataclass
class Like():
    userid: str
    pages: str
    max_results: int
    twitter: TwitterAPI

    def fetch(self) -> dict:
        """LIKED_TWEET エンドポイントにて、self.userid に紐づく LIKE を取得する
            self.pages * self.max_results だけ遡る

        Returns:
            list[dict]: ページごとに格納された LIKED_TWEET API 返り値
        """
        url = TwitterAPIEndpoint.LIKED_TWEET.value[0].format(self.userid)
        next_token = ""
        result = []
        for _ in range(self.pages):
            params = {
                "expansions": "author_id,attachments.media_keys",
                "tweet.fields": "id,attachments,author_id,entities,text,source,created_at",
                "user.fields": "id,name,username,url",
                "media.fields": "url,variants,preview_image_url,alt_text",
                "max_results": self.max_results,
            }
            if next_token != "":
                params["pagination_token"] = next_token
            tweet = self.twitter.get(url, params=params)
            result.append(tweet)
            next_token = tweet.get("meta", {}).get("next_token", "")
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

    def _flatten(self, liked_tweet: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
        """liked_tweet のおおまかな構造解析
            ページごとに分かれているので平滑化

        Args:
            liked_tweet (list[dict]): self.fetch() の返り値

        Returns:
            data_list (list[dict]): liked_tweetのうちdata部分
            media_list (list[dict]): liked_tweetのうちmedia部分
            users_list (list[dict]): liked_tweetのうちusers部分
                エラー時それぞれ空リスト
        """
        data_list = []
        media_list = []
        users_list = []
        for t in liked_tweet:
            match t:
                case {"data": data, "includes": {"media": media, "users": users}}:
                    # ページをまたいでそれぞれ重複しているかもしれないが以後の処理に影響はしない
                    data_list.extend(data)
                    media_list.extend(media)
                    users_list.extend(users)
                case _:
                    # raise ValueError("argument liked_tweet is invalid.")
                    continue
        return data_list, media_list, users_list

    def to_convert_LikeInfo(self, liked_tweet: list[dict]) -> list[LikeInfo]:
        """self.fetch() 後の返り値から LikeInfo のリストを返す

        Args:
            liked_tweet (list[dict]): self.fetch() 後の返り値

        Returns:
            list[LikeInfo]: LikeInfo リスト
        """
        # liked_tweet のおおまかな構造解析
        # ページに分かれているので平滑化
        data_list, media_list, users_list = self._flatten(liked_tweet)

        # data_listを探索
        result = []
        for data in data_list:
            match data:
                case {
                    "attachments": {"media_keys": media_keys},
                    "author_id": author_id,
                    "created_at": created_at,
                    "entities": {"urls": urls},
                    "id": id_str,
                    "source": via,
                    "text": text
                }:
                    # mediaが添付されているならば収集
                    # 主にattachmentsフィールドが含まれるかで判定する
                    # この段階で判明する情報はそのまま保持する
                    tweet_id = id_str
                    tweet_via = via
                    tweet_text = text

                    # user_name, screan_name はuser_id をキーにuser_list から検索する
                    user_id = author_id
                    user_name, screan_name = self._find_name(user_id, users_list)

                    # tweet_url を探索
                    # entities内のexpanded_urlを採用する
                    # ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
                    tweet_url = self._match_tweet_url(urls)

                    # created_at を解釈する
                    # ex. created_at = "2022-10-10T23:54:18.000Z"
                    # ISO8601拡張形式だが、末尾Zは解釈できないためタイムゾーンに置き換える
                    # その後UTCからJSTに変換(9時間進める)して所定の形式の文字列に変換する
                    dts_format = "%Y-%m-%d %H:%M:%S"
                    zoned_created_at = str(created_at).replace("Z", "+00:00")
                    utc = datetime.fromisoformat(zoned_created_at)
                    jst = utc + timedelta(hours=9)
                    dst = jst.strftime(dts_format)

                    # media情報について収集する
                    # 1ツイートに対してmedia は最大4つ添付されている
                    # それぞれmedia_key をキーにmedia_list から検索する
                    for media_key in media_keys:
                        media_filename = ""
                        media_url = ""
                        media_thumbnail_url = ""

                        media = self._find_media(media_key, media_list)
                        media_filename, media_url, media_thumbnail_url = self._match_media_info(media)

                        if media_filename == "" or media_url == "" or media_thumbnail_url == "":
                            continue  # 扱えるメディアに紐づくmedia_keyではなかった（エラー？）

                        # resultレコード作成
                        r = {
                            "media_filename": media_filename,
                            "media_url": media_url,
                            "media_thumbnail_url": media_thumbnail_url,
                            "tweet_id": tweet_id,
                            "tweet_url": tweet_url,
                            "created_at": dst,
                            "user_id": user_id,
                            "user_name": user_name,
                            "screan_name": screan_name,
                            "tweet_text": tweet_text,
                            "tweet_via": tweet_via,
                        }
                        result.append(LikeInfo.create(r))
                case _:
                    # mediaが含まれているツイートではなかった
                    continue
        return result

    def to_convert_ExternalLink(self, liked_tweet: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        """self.fetch() 後の返り値から ExternalLink のリストを返す

        Args:
            liked_tweet (list[dict]): self.fetch() 後の返り値
            link_searcher (LinkSearcher): 外部リンク探索用LinkSearcher

        Returns:
            list[ExternalLink]: ExternalLink リスト
        """
        # liked_tweet のおおまかな構造解析
        # ページに分かれているので平滑化
        data_list, media_list, users_list = self._flatten(liked_tweet)

        def create_ExternalLink(dict: dict) -> "ExternalLink":
            match dict:
                case {
                    "external_link_url": external_link_url,
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
                }:
                    return ExternalLink(external_link_url,
                                        tweet_id,
                                        tweet_url,
                                        created_at,
                                        user_id,
                                        user_name,
                                        screan_name,
                                        tweet_text,
                                        tweet_via,
                                        saved_created_at,
                                        link_type)
                case _:
                    raise ValueError("ExternalLink create failed.")

        # data_listを探索
        result = []
        for data in data_list:
            match data:
                case {
                    "author_id": author_id,
                    "created_at": created_at,
                    "entities": {"urls": urls},
                    "id": id_str,
                    "source": via,
                    "text": text
                }:
                    # 外部リンクが含まれているならば収集
                    # link_searcherのCoRで対象かどうか判定する
                    # この段階で判明する情報はそのまま保持する
                    tweet_id = id_str
                    tweet_via = via
                    tweet_text = text
                    link_type = ""

                    # user_name, screan_name はuser_id をキーにuser_list から検索する
                    user_id = author_id
                    user_name, screan_name = self._find_name(user_id, users_list)

                    # tweet_url は screan_name と tweet_id から生成する
                    tweet_url = f"https://twitter.com/{screan_name}/status/{tweet_id}"

                    # created_at を解釈する
                    # ex. created_at = "2022-10-10T23:54:18.000Z"
                    # ISO8601拡張形式だが、末尾Zは解釈できないためタイムゾーンに置き換える
                    # その後UTCからJSTに変換(9時間進める)して所定の形式の文字列に変換する
                    dts_format = "%Y-%m-%d %H:%M:%S"
                    zoned_created_at = str(created_at).replace("Z", "+00:00")
                    utc = datetime.fromisoformat(zoned_created_at)
                    jst = utc + timedelta(hours=9)
                    dst = jst.strftime(dts_format)

                    # 保存時間は現在時刻とする
                    saved_created_at = datetime.now().strftime(dts_format)

                    # expanded_url を収集する
                    expanded_urls = self._match_expanded_url(urls)

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
                        result.append(create_ExternalLink(r))
                case _:
                    # mediaが含まれているツイートではなかった
                    continue
        return result


if __name__ == "__main__":
    import codecs
    import configparser
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

    MY_ID = 175674367
    like = Like(userid=MY_ID, pages=3, max_results=100, twitter=twitter)
    # 実際にAPIを叩いて取得する
    # res = like.fetch()
    # with codecs.open("./PictureGathering/v2/api_response_like.txt", "w", "utf-8") as fout:
    #     # pprint.pprint(res, fout)
    #     json.dump(res, fout)
    # pprint.pprint(res)

    # キャッシュを読み込んでLikeInfoリストを作成する
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_like.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = like.to_convert_LikeInfo(input_dict)
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
