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
from PictureGathering.v2.RetweetInfo import RetweetInfo
from PictureGathering.v2.TwitterAPI import TwitterAPI, TwitterAPIEndpoint


@dataclass
class Retweet():
    userid: str
    pages: str
    max_results: int
    twitter: TwitterAPI

    def fetch(self) -> list[dict]:
        """TIMELINE_TWEET エンドポイントにて、self.userid に紐づくタイムラインを取得する
            self.pages * self.max_results だけ遡る

        Returns:
            list[dict]: ページごとに格納された TIMELINE_TWEET API 返り値
        """
        url = TwitterAPIEndpoint.TIMELINE_TWEET.value[0].format(self.userid)
        next_token = ""
        result = []
        for _ in range(self.pages):
            params = {
                "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id,attachments.media_keys",
                "tweet.fields": "id,attachments,author_id,referenced_tweets,entities,text,source,created_at",
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

    def _find_tweets(self, tweet_id: str, tweets_list: list[dict]) -> dict:
        """tweet_id をキーに tweets_list を検索する

        Args:
            tweet_id (str): 検索id
            tweets_list (list[dict]): 検索対象リスト

        Returns:
            dict: 最初に見つかった tweets 情報を返す、見つからなかった場合、空辞書を返す
        """
        t_list = [tweet for tweet in tweets_list if tweet.get("id", "") == tweet_id]
        if len(t_list) == 0:
            return {}
        return t_list[0]

    def _find_name(self, user_id: str, users_list: list[dict]) -> tuple[str, str]:
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
        return user_name, screan_name

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
                    # media_key が振られている media について、
                    # expanded_url は共通で紐づくツイートを指すため、見つけたらすぐ確定して良い
                    tweet_url = expanded_url
                    break
                case _:
                    pass
        if tweet_url == "":
            raise ValueError("tweet_url not found.")
        return tweet_url

    def _match_media_info(self, media: dict) -> tuple[str, str, str]:
        """media情報について収集する
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
                pass  # 扱えるメディアに紐づく media_key ではなかった（エラー？）
        return media_filename, media_url, media_thumbnail_url

    def _match_video_url(self, variants: dict) -> str:
        """video情報について収集する
            同じ動画の中で一番ビットレートが高い動画のURLを保存する
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
                case _:
                    pass  # 扱えるメディアではなかった
        return video_url

    def _match_expanded_url(self, urls: dict) -> list[str]:
        """entities 内の expanded_url を取得する
            ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
            上記の他に外部リンクも対象とする
        """
        result = [url.get("expanded_url", "") for url in urls if "expanded_url" in url]
        return result

    def _flatten(self, retweeted_tweet: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        """retweeted_tweet のおおまかな構造解析
            retweeted_tweet は self.fetch() の返り値を想定している
            ページごとに分かれているので平滑化
        """
        data_list = []
        media_list = []
        tweets_list = []
        users_list = []
        for t in retweeted_tweet:
            match t:
                case {"data": data, "includes": {"media": media, "tweets": tweets, "users": users}}:
                    # ページをまたいでそれぞれ重複しているかもしれないが以後の処理に影響はしない
                    data_list.extend(data)
                    media_list.extend(media)
                    tweets_list.extend(tweets)
                    users_list.extend(users)
                case _:
                    # RTが1件もない場合、tweetsはおそらく空になる
                    # raise ValueError("argument retweeted_tweet is invalid.")
                    pass
        return data_list, media_list, tweets_list, users_list

    def _is_include_referenced_tweets(self, data: dict) -> bool:
        """data に referenced_tweet が含まれる、かつ、
            referenced_tweet.type が["retweeted", "quoted"]のいずれかならばTrue,
            そうでないならFalse
            ※referenced_tweet.type = "replied_to" はリプライツリー用

        Args:
            data (dict): self.fetch()[].data

        Returns:
            bool: 説明参照
        """
        if "referenced_tweets" in data:
            referenced_tweets = data.get("referenced_tweets", [])
            for referenced_tweet in referenced_tweets:
                referenced_tweet_id = referenced_tweet.get("id", "")
                referenced_tweet_type = referenced_tweet.get("type", "")
                if referenced_tweet_id == "":
                    continue
                if referenced_tweet_type in ["retweeted", "quoted"]:
                    return True
        return False

    def _find_retweet_tree_with_attachments(self, data_with_referenced_tweets: list[dict], tweets_list: list[dict]) -> tuple[list[str], list[dict]]:
        """attachments を基準にRTツリーを探索する
            data_with_referenced_tweets[].referenced_tweets[].id に紐づくツイートを tweets_list 内から探索する
            見つかった tweets に attachments があっても、
            その media_key に対応する media 情報は media_list に含まれてないため、
            別途追加で問い合わせを行う必要がある

        Args:
            data_with_referenced_tweets (dict): referenced_tweets を持つツイートオブジェクト
            tweets_list (list[dict]): 参照用 tweets_list

        Returns:
            query_need_ids (list[str]): 別途問い合わせが必要なツイートidリスト
            query_need_tweets (list[dict]): 問い合わせ後に有効になる attachments を持つツイートオブジェクト
        """
        query_need_ids = []
        query_need_tweets = []
        for data in data_with_referenced_tweets:
            referenced_tweets = data.get("referenced_tweets", [])
            for referenced_tweet in referenced_tweets:
                referenced_tweet_id = referenced_tweet.get("id", "")
                referenced_tweet_type = referenced_tweet.get("type", "")
                if referenced_tweet_id == "":
                    continue
                if referenced_tweet_type not in ["retweeted", "quoted"]:
                    continue

                tweets = self._find_tweets(referenced_tweet_id, tweets_list)
                if not tweets:
                    # ツイートが削除された等で参照用 tweets_list に存在しない場合
                    continue

                match tweets:
                    case {
                        "attachments": {"media_keys": media_keys},
                        "referenced_tweets": n_referenced_tweets,
                    }:
                        # attachmentsとreferenced_tweets両方ある場合
                        # 1階層目のツイートに media が添付されており、かつ、
                        # 2階層目のツイートが存在している
                        # TODO::構造チェックが甘いかも

                        # 1階層目のツイートを問い合わせ対象に含める
                        query_need_ids.append(referenced_tweet_id)
                        # first_level_tweets_list 候補として保持しておく
                        query_need_tweets.append(tweets)

                        # 2階層目のツイートを問い合わせ対象に含める
                        for n_referenced_tweet in n_referenced_tweets:
                            query_need_id = n_referenced_tweet.get("id", "")
                            query_need_ids.append(query_need_id)
                    case {
                        "attachments": {"media_keys": media_keys},
                    }:
                        # attachmentsのみがある場合
                        # 1階層目のツイートに media が添付されており、かつ、
                        # 2階層目のツイートが存在しない

                        # 1階層目のツイートを問い合わせ対象に含める
                        query_need_ids.append(referenced_tweet_id)
                        # first_level_tweets_list 候補として保持しておく
                        query_need_tweets.append(tweets)
                    case {
                        "referenced_tweets": n_referenced_tweets,
                    }:
                        # attachmentsがない、かつreferenced_tweetsがある場合
                        # 1階層目のツイートに media が添付されていない、かつ、
                        # 2階層目のツイートが存在する

                        # 2階層目のツイートを問い合わせ対象に含める
                        for n_referenced_tweet in n_referenced_tweets:
                            query_need_id = n_referenced_tweet.get("id", "")
                            query_need_ids.append(query_need_id)
                    case _:
                        pass
        return query_need_ids, query_need_tweets

    def _find_retweet_tree_with_entities(self, data_with_referenced_tweets: dict, tweets_list: list[dict]) -> tuple[list[str], list[dict]]:
        """entities を基準にRTツリーを探索する
            data_with_referenced_tweets[].referenced_tweets[].id に紐づくツイートを tweets_list 内から探索する
            途中で見つかった tweets にある entities は有効なので、追加で問い合わせを行う必要はない
            ただしRTツリー末端の収集のために、問い合わせる必要があるidは収集する

        Args:
            data_with_referenced_tweets (dict): referenced_tweets を持つツイートオブジェクト
            tweets_list (list[dict]): 参照用 tweets_list

        Returns:
            query_need_ids (list[str]): 別途問い合わせが必要なツイートidリスト（RTツリー末端）
            first_level_tweets_list (list[dict]): entities を持つツイートオブジェクト
        """
        query_need_ids = []
        first_level_tweets_list = []
        for data in data_with_referenced_tweets:
            referenced_tweets = data.get("referenced_tweets", [])
            for referenced_tweet in referenced_tweets:
                referenced_tweet_id = referenced_tweet.get("id", "")
                referenced_tweet_type = referenced_tweet.get("type", "")
                if referenced_tweet_id == "":
                    continue
                if referenced_tweet_type not in ["retweeted", "quoted"]:
                    continue

                tweets = self._find_tweets(referenced_tweet_id, tweets_list)
                if not tweets:
                    # 本来ここには入ってこないはず
                    continue

                match tweets:
                    case {
                        "entities": {"urls": urls},
                        "referenced_tweets": n_referenced_tweets,
                    }:
                        # entities と referenced_tweets 両方ある場合
                        # 1階層目のツイートに entities があり、かつ、
                        # 2階層目のツイートが存在している
                        # TODO::構造チェックが甘いかも

                        # entities 情報は有効なので1階層目のツイートは問い合わせ対象に含めない
                        # query_need_ids.append(referenced_tweet_id)
                        # first_level_tweets_list 確定として取得
                        first_level_tweets_list.append(tweets)

                        # 2階層目のツイートを問い合わせ対象に含める
                        for n_referenced_tweet in n_referenced_tweets:
                            query_need_id = n_referenced_tweet.get("id", "")
                            query_need_ids.append(query_need_id)
                    case {
                        "entities": {"urls": urls},
                    }:
                        # entitiesのみがある場合
                        # 1階層目のツイートに entities があり、かつ、
                        # 2階層目のツイートが存在しない

                        # entities 情報は有効なので1階層目のツイートは問い合わせ対象に含めない
                        # query_need_ids.append(referenced_tweet_id)
                        # first_level_tweets_list 確定として取得
                        first_level_tweets_list.append(tweets)
                    case {
                        "referenced_tweets": n_referenced_tweets,
                    }:
                        # entitiesがない、かつreferenced_tweetsがある場合
                        # 1階層目のツイートに entities が存在しない、かつ、
                        # 2階層目のツイートが存在する

                        # 2階層目のツイートを問い合わせ対象に含める
                        for n_referenced_tweet in n_referenced_tweets:
                            query_need_id = n_referenced_tweet.get("id", "")
                            query_need_ids.append(query_need_id)
                    case _:
                        pass
        return query_need_ids, first_level_tweets_list

    def _fetch_tweet_lookup(self, query_need_ids: list[str], MAX_IDS_NUM: int = 100) -> tuple[list[dict], list[dict], list[dict]]:
        """追加問い合わせ
            TWEETS_LOOKUP エンドポイントにて各ツイートIDに紐づくツイートをAPIを通して取得する
            TWEETS_LOOKUP エンドポイントは取得ツイートキャップには影響しない

        Args:
            query_need_ids (list[str]): 問い合わせ対象ツイートidリスト
            MAX_IDS_NUM (int, optional): TWEETS_LOOKUP エンドポイントの1ループでの制限個数

        Returns:
            data_list (list[dict]): TWEETS_LOOKUP 返り値のうちdata部分
            media_list (list[dict]): TWEETS_LOOKUP 返り値のうちmedia部分
            users_list (list[dict]): TWEETS_LOOKUP 返り値のうちusers部分
        """
        url = TwitterAPIEndpoint.TWEETS_LOOKUP.value[0]
        data_list = []
        media_list = []
        users_list = []
        for i in range(0, len(query_need_ids), MAX_IDS_NUM):
            query_need_ids_sub = query_need_ids[i: i + MAX_IDS_NUM]
            params = {
                "ids": ",".join(query_need_ids_sub),
                "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id,attachments.media_keys",
                "tweet.fields": "id,attachments,author_id,referenced_tweets,entities,text,source,created_at",
                "user.fields": "id,name,username,url",
                "media.fields": "url,variants,preview_image_url,alt_text",
            }
            tweets_lookup_result = self.twitter.get(url, params=params)
            # キャッシュ用
            # with codecs.open("./PictureGathering/v2/api_response_tweet_lookup_json.txt", "w", "utf-8") as fout:
            #     json.dump(tweet, fout)
            # with codecs.open("./PictureGathering/v2/api_response_tweet_lookup_pprint.txt", "w", "utf-8") as fout:
            #     pprint.pprint(tweet, fout)

            # 問い合わせ結果を解釈する
            match tweets_lookup_result:
                case {"data": data, "includes": {"media": media, "users": users}}:
                    data_list.extend(data)
                    media_list.extend(media)
                    users_list.extend(users)
                case _:
                    # raise ValueError("TwitterAPIEndpoint.TWEETS_LOOKUP access failed.")
                    pass
        return data_list, media_list, users_list

    def to_convert_RetweetInfo(self, retweeted_tweet: list[dict]) -> list[RetweetInfo]:
        """self.fetch() 後の返り値からRetweetInfoのリストを返す

        Args:
            retweeted_tweet (list[dict]): self.fetch() 後の返り値

        Returns:
            list[RetweetInfo]: RetweetInfoリスト
        """
        # retweeted_tweet のおおまかな構造解析
        # ページに分かれているので平滑化
        data_list, media_list, tweets_list, users_list = self._flatten(retweeted_tweet)

        # 以下の構造となっている
        # (A)自分のTL上でのRTツイート
        #    0階層目
        #    author_id 等がすべて自分のツイート
        #    最終的な収集対象には含めない
        #    = data_with_referenced_tweets
        # (B)RT先ツイート
        #    (A)のRT先のツイート
        #    (A)から見て1階層目
        #    media が含まれているかもしれない
        #    (C)に紐づく referenced_tweets が含まれているかもしれない
        #    最終的な収集対象に含める
        #    = first_level_tweets_list
        # (C)RT先のRT先ツイート
        #    (B)のRT先のツイート(引用RTをRTしたときなど)
        #    (A)から見て2階層目
        #    media が含まれているかもしれない
        #    最終的な収集対象に含める
        #    = second_level_tweets_list

        # (A)自分のTL上でのRTツイートを探索
        # referenced_tweets が存在するかで判定
        # より詳細には referenced_tweet.type が["retweeted", "quoted"]のもののみ対象とする
        # ※referenced_tweet.type = "replied_to" はリプライツリー用
        data_with_referenced_tweets = [data for data in data_list if self._is_include_referenced_tweets(data)]

        # (B)RT先ツイートを探索
        # (A)の referenced_tweet.id に紐づくツイートを tweets_list 内から探索する
        # 見つかった tweets に attachments があっても、
        # その media_key に対応する media 情報は media_list に含まれてないため、
        # 別途追加で問い合わせを行う必要がある
        # first_level_tweets_list := query_need_tweets だが、
        # 問い合わせを行うまでは上記の通り media 情報が有効でない
        # ここでは問い合わせに必要な情報を収集する = (C)収集の準備
        query_need_ids, query_need_tweets = self._find_retweet_tree_with_attachments(data_with_referenced_tweets, tweets_list)
        # 重複排除
        seen = []
        query_need_ids = [i for i in query_need_ids if i not in seen and not seen.append(i)]

        # (B),(C)追加問い合わせ
        # TWEETS_LOOKUP エンドポイントにて各ツイートIDに紐づくツイートをAPIを通して取得する
        # 100件ずつ回す
        MAX_IDS_NUM = 100
        second_level_tweets_list, lookuped_media_list, lookuped_users_list = self._fetch_tweet_lookup(query_need_ids, MAX_IDS_NUM)
        media_list.extend(lookuped_media_list)
        users_list.extend(lookuped_users_list)

        # (B)問い合わせ完了したので以降は正しく扱える
        first_level_tweets_list = []
        first_level_tweets_list.extend(query_need_tweets)

        # 収集対象を確定させる
        # TODO::重複チェック？
        # キーについては互換性がある
        target_data_list = []
        # target_data_list.extend(data_with_referenced_tweets)  # (A)自分のTL上でのRTツイート
        target_data_list.extend(first_level_tweets_list)  # (B)RT先ツイート（必ずmediaを含む）
        target_data_list.extend(second_level_tweets_list)  # (C)RT先のRT先ツイート（mediaが含まれているかもしれない）

        # target_data_list を入力として media 情報を収集
        result = []
        seen = []
        for data in target_data_list:
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
                    referenced_tweet_id = id_str
                    tweet_via = via
                    tweet_text = text

                    if referenced_tweet_id in seen:
                        continue

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
                            "tweet_id": referenced_tweet_id,
                            "tweet_url": tweet_url,
                            "created_at": dst,
                            "user_id": user_id,
                            "user_name": user_name,
                            "screan_name": screan_name,
                            "tweet_text": tweet_text,
                            "tweet_via": tweet_via,
                        }
                        result.append(RetweetInfo.create(r))

                        if referenced_tweet_id not in seen:
                            seen.append(referenced_tweet_id)
                case _:
                    # mediaが含まれているツイートではなかった
                    continue
        return result

    def to_convert_ExternalLink(self, retweeted_tweet: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        """fetch後の返り値からExternalLinkのリストを返す
        """
        # retweeted_tweet のおおまかな構造解析
        # ページに分かれているので平滑化
        data_list, media_list, tweets_list, users_list = self._flatten(retweeted_tweet)

        # 以下の構造となっている
        # (A)自分のTL上でのRTツイート
        #    0階層目
        #    author_id 等がすべて自分のツイート
        #    最終的な収集対象には含めない
        #    = data_with_referenced_tweets
        # (B)RT先ツイート
        #    (A)のRT先のツイート
        #    (A)から見て1階層目
        #    media が含まれているかもしれない
        #    (C)に紐づく referenced_tweets が含まれているかもしれない
        #    最終的な収集対象に含める
        #    = first_level_tweets_list
        # (C)RT先のRT先ツイート
        #    (B)のRT先のツイート(引用RTをRTしたときなど)
        #    (A)から見て2階層目
        #    media が含まれているかもしれない
        #    最終的な収集対象に含める
        #    = second_level_tweets_list

        # (A)自分のTL上でのRTツイートを探索
        # referenced_tweets が存在するかで判定
        # より詳細には referenced_tweet.type が["retweeted", "quoted"]のもののみ対象とする
        # ※referenced_tweet.type = "replied_to" はリプライツリー用
        data_with_referenced_tweets = [data for data in data_list if self._is_include_referenced_tweets(data)]

        # (B)RT先ツイートを探索
        # (A)の referenced_tweet.id に紐づくツイートを tweets_list 内から探索する
        # 見つかった tweets にある entities は有効なので、
        # (B)について追加で問い合わせを行う必要はない
        # (C)収集の準備として、問い合わせに必要な情報を収集する
        query_need_ids, first_level_tweets_list = self._find_retweet_tree_with_entities(data_with_referenced_tweets, tweets_list)
        # 重複排除
        seen = []
        query_need_ids = [i for i in query_need_ids if i not in seen and not seen.append(i)]

        # (C)追加問い合わせ
        # TWEETS_LOOKUP エンドポイントにて各ツイートIDに紐づくツイートをAPIを通して取得する
        # 100件ずつ回す
        MAX_IDS_NUM = 100
        second_level_tweets_list, lookuped_media_list, lookuped_users_list = self._fetch_tweet_lookup(query_need_ids, MAX_IDS_NUM)
        media_list.extend(lookuped_media_list)  # 不要？
        users_list.extend(lookuped_users_list)  # 不要？

        # 収集対象を確定させる
        # TODO::重複チェック？
        # キーについては互換性がある
        target_data_list = []
        # target_data_list.extend(data_with_referenced_tweets)  # (A)自分のTL上でのRTツイート
        target_data_list.extend(first_level_tweets_list)  # (B)RT先ツイート
        target_data_list.extend(second_level_tweets_list)  # (C)RT先のRT先ツイート

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
                    raise ValueError("LikeTweet create failed.")

        # target_data_list を入力として外部リンクを探索
        result = []
        for data in target_data_list:
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
                    # 外部リンクが含まれているツイートではなかった
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
    retweet = Retweet(userid=MY_ID, pages=3, max_results=100, twitter=twitter)
    # 実際にAPIを叩いて取得する
    # res = retweet.fetch()
    # with codecs.open("./PictureGathering/v2/api_response_timeline_json.txt", "w", "utf-8") as fout:
    #     # pprint.pprint(res, fout)
    #     json.dump(res, fout)
    # # pprint.pprint(res)

    # キャッシュを読み込んでRetweetInfoリストを作成する
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_timeline_json.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = retweet.to_convert_RetweetInfo(input_dict)
    pprint.pprint(res)
    print(len(res))

    # キャッシュを読み込んでExternalLinkリストを作成する
    config = config_parser
    config["skeb"]["is_skeb_trace"] = "False"
    lsb = LinkSearcher.create(config)
    input_dict = {}
    with codecs.open("./PictureGathering/v2/api_response_timeline_json.txt", "r", "utf-8") as fin:
        input_dict = json.load(fin)
    res = retweet.to_convert_ExternalLink(input_dict, lsb)
    pprint.pprint(res)
    print(len(res))
