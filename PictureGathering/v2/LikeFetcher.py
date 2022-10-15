# coding: utf-8
import json
import pprint
from datetime import datetime, timedelta

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.Model import ExternalLink
from PictureGathering.v2.TweetInfo import TweetInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI, TwitterAPIEndpoint
from PictureGathering.v2.V2Base import V2Base


class LikeInfo(TweetInfo):
    pass


class LikeFetcher(V2Base):
    userid: str
    max_results: int

    def __init__(self, userid: str, pages: int, max_results: int, twitter: TwitterAPI) -> None:
        self.userid = userid
        self.max_results = max_results

        api_endpoint_url = TwitterAPIEndpoint.LIKED_TWEET.value[0].format(self.userid)

        params = {
            "expansions": "author_id,attachments.media_keys",
            "tweet.fields": "id,attachments,author_id,entities,text,source,created_at",
            "user.fields": "id,name,username,url",
            "media.fields": "url,variants,preview_image_url,alt_text",
            "max_results": self.max_results,
        }
        super(LikeFetcher, self).__init__(api_endpoint_url, params, pages, twitter)

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

    def to_convert_TweetInfo(self, fetched_tweets: list[dict]) -> list[TweetInfo]:
        """self.fetch() 後の返り値から LikeInfo のリストを返す

        Args:
            fetched_tweets (list[dict]): self.fetch() 後の返り値

        Returns:
            list[LikeInfo]: LikeInfo リスト
        """
        liked_tweet = fetched_tweets
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

    def to_convert_ExternalLink(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        """self.fetch() 後の返り値から ExternalLink のリストを返す

        Args:
            liked_tweet (list[dict]): self.fetch() 後の返り値
            link_searcher (LinkSearcher): 外部リンク探索用LinkSearcher

        Returns:
            list[ExternalLink]: ExternalLink リスト
        """
        liked_tweet = fetched_tweets
        # liked_tweet のおおまかな構造解析
        # ページに分かれているので平滑化
        data_list, media_list, users_list = self._flatten(liked_tweet)

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
                        result.append(ExternalLink.create(r))
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
    like = LikeFetcher(userid=MY_ID, pages=3, max_results=100, twitter=twitter)
    # 実際にAPIを叩いて取得する
    # res = like.fetch()
    # with codecs.open("./PictureGathering/v2/api_response_like_pprint.txt", "w", "utf-8") as fout:
    #     pprint.pprint(res, fout)
    # with codecs.open("./PictureGathering/v2/api_response_like_json.txt", "w", "utf-8") as fout:
    #     json.dump(res, fout)
    # pprint.pprint(res)

    # キャッシュを読み込んでLikeInfoリストを作成する
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_like_json.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = like.to_convert_TweetInfo(input_dict)
    pprint.pprint(res)
    print(len(res))

    # キャッシュを読み込んでExternalLinkリストを作成する
    config = config_parser
    config["skeb"]["is_skeb_trace"] = "False"
    lsb = LinkSearcher.create(config)
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_like_json.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = like.to_convert_ExternalLink(input_dict, lsb)
    pprint.pprint(res)
    print(len(res))
