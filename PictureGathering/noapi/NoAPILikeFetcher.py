# coding: utf-8
from datetime import datetime
from pathlib import Path
import asyncio
import json
import pprint
import re
import shutil
import sys
import urllib.parse

from pyppeteer.page import Page
from requests_html import HTML

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.Model import ExternalLink
from PictureGathering.noapi.TweetInfo import TweetInfo
from PictureGathering.noapi.TwitterSession import TwitterSession


class NoAPILikeFetcher():
    username: str
    password: str
    twitter_session: TwitterSession

    # キャッシュファイルパス
    TWITTER_CACHE_PATH = Path(__file__).parent / "cache/"

    def __init__(self, username: str, password: str) -> None:
        if not (isinstance(username, str) and username != ""):
            raise ValueError("username is not str or empty.")
        if not (isinstance(password, str) and password != ""):
            raise ValueError("password is not str or empty.")

        self.username = username
        self.password = password
        self.twitter_session = TwitterSession.create(username=username, password=password)
        # super(LikeFetcher, self).__init__(api_endpoint_url, params, pages, twitter)

    async def get_like_jsons(self) -> list[str]:
        await self.twitter_session.prepare()

        url = self.twitter_session.LIKES_URL_TEMPLATE.format(self.username)
        res = await self.twitter_session.get(url)
        await res.html.arender(keep_page=True)
        html: HTML = res.html
        page: Page = html.page

        redirect_urls = []
        content_list = []

        # キャッシュ保存場所の準備
        base_path = Path(self.TWITTER_CACHE_PATH)
        if base_path.is_dir():
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # レスポンス監視
        async def ResponseListener(response):
            if "Like" in response.url:
                redirect_urls.append(response.url)
                # buffer_list.append(await response.buffer())
                # text_list.append(await response.text())
                # content = await response.json()
                if "application/json" in response.headers.get("content-type", ""):
                    content = await response.json()
                    n = len(content_list)
                    # レスポンスJSONをキャッシュに保存
                    with Path(base_path / f"content_cache{n}.txt").open("w", encoding="utf8") as fout:
                        json.dump(content, fout)
                    content_list.append(content)
        page.on("response", lambda response: asyncio.ensure_future(ResponseListener(response)))

        # Likesページをスクロールして読み込んでいく
        for i in range(20):
            await page.evaluate("""
                () => {
                    let elm = document.documentElement;
                    let bottom = elm.scrollHeight - elm.clientHeight;
                    window.scroll(0, bottom);
                }
            """)
            await page.waitFor(1000)

        await page.waitFor(2000)

        # リダイレクトURLをキャッシュに保存
        if redirect_urls:
            with Path(base_path / "redirect_urls.txt").open("w", encoding="utf8") as fout:
                fout.write(pprint.pformat(redirect_urls))

        # キャッシュから読み込み
        result = []
        for i, content in enumerate(content_list):
            with Path(base_path / f"content_cache{i}.txt").open("r", encoding="utf8") as fin:
                json_dict = json.load(fin)
                result.append(json_dict)

        return result

    def interpret_json(self, tweet: dict, id_str_list: list = None) -> list[dict]:
        """ツイートオブジェクトの階層（RT、引用RTの親子関係）をたどり、ツイートがメディアを含むかどうか調べる

        Note:
           ツイートオブジェクトのルートを引数として受け取り、以下のようにresultを返す
           (1)tweetにメディアが添付されている場合、resultにtweetを追加
           (2)tweetに外部リンクが含まれている場合、resultにtweetを追加
           (3)RTされているツイートの場合、resultにtweet["retweeted_status"]とtweetを追加
           (4)引用RTされているツイートの場合、resultにtweet["quoted_status"]とtweetを追加
           (5)引用RTがRTされているツイートの場合、
              resultにtweet["retweeted_status"]["quoted_status"]とtweet["retweeted_status"]とtweetを追加

           引用RTはRTできるがRTは引用RTできないので無限ループにはならない（最大深さ2）
           id_strが重複しているツイートは格納しない
           最終的な返り値となる辞書リストは、タイムスタンプ順に昇順ソートされている
           （昔  RT先ツイート(=A) → （存在するならば）(A)を引用RTしたツイート(=B) → (AまたはB)をRTしたツイート  直近）

        Args:
            tweet (dict): ツイートオブジェクトのルート
            id_str_list (list[str]): 格納済みツイートのid_strリスト

        Returns:
            list[dict]: 上記にて出力された辞書リスト
        """
        result = []

        # デフォルト引数の処理
        if id_str_list is None:
            id_str_list = []
            id_str_list.append(None)

        tweet_legacy = tweet.get("legacy", {})

        # ツイートオブジェクトにRTフラグが立っている場合
        if tweet_legacy.get("retweeted") and tweet.get("retweeted_status_result"):
            retweeted_tweet = tweet.get("retweeted_status_result", {}).get("result", {})
            retweeted_tweet_legacy = retweeted_tweet.get("legacy", {})
            if retweeted_tweet_legacy.get("extended_entities"):
                if retweeted_tweet_legacy.get("id_str") not in id_str_list:
                    result.append(retweeted_tweet)
                    id_str_list.append(retweeted_tweet_legacy.get("id_str"))
                    # result.append(tweet_legacy)
                    # id_str_list.append(tweet_legacy.get("id_str"))
            # リツイートオブジェクトに引用RTフラグも立っている場合
            if retweeted_tweet.get("is_quote_status") and retweeted_tweet.get("quoted_status_result"):
                quoted_tweet = retweeted_tweet.get("quoted_status_result", {}).get("result", {})
                quoted_tweet_legacy = quoted_tweet.get("legacy", {})
                if quoted_tweet_legacy.get("extended_entities"):
                    if quoted_tweet_legacy.get("id_str") not in id_str_list:
                        # result = result + self.GetMediaTweet(retweeted_tweet, id_str_list)
                        result.append(quoted_tweet)
                        id_str_list.append(quoted_tweet_legacy.get("id_str"))
        # ツイートオブジェクトに引用RTフラグが立っている場合
        elif tweet_legacy.get("is_quote_status") and tweet.get("quoted_status_result"):
            quoted_tweet = tweet.get("quoted_status_result", {}).get("result", {})
            quoted_tweet_legacy = quoted_tweet.get("legacy", {})
            if quoted_tweet_legacy.get("extended_entities"):
                if quoted_tweet_legacy.get("id_str") not in id_str_list:
                    result.append(quoted_tweet)
                    id_str_list.append(quoted_tweet_legacy.get("id_str"))
                    # result.append(tweet_legacy)
                    # id_str_list.append(tweet_legacy.get("id_str"))
            # ツイートオブジェクトにRTフラグも立っている場合（仕様上、本来はここはいらない）
            # if quoted_tweet.get("retweeted") and quoted_tweet.get("retweeted_status"):
            #     retweeted_tweet = quoted_tweet.get("retweeted_status", {})
            #     if retweeted_tweet.get("extended_entities"):
            #         if retweeted_tweet.get("id_str") not in id_str_list:
            #             result = result + self.GetMediaTweet(quoted_tweet, id_str_list)
            #             result.append(tweet_legacy)
            #             id_str_list.append(tweet_legacy.get("id_str"))

        # ツイートオブジェクトにメディアがある場合
        if tweet_legacy.get("extended_entities", {}).get("media"):
            if tweet_legacy.get("id_str") not in id_str_list:
                result.append(tweet)
                id_str_list.append(tweet_legacy.get("id_str"))

        # ツイートに外部リンクが含まれている場合
        if tweet_legacy.get("entities", {}).get("urls"):
            urls = tweet_legacy.get("entities", {}).get("urls", [{}])
            url = urls[0].get("expanded_url")
            if url:
                # 何かしらのリンクを含むかどうかだけ見るので、収集対象かどうかはdon't care
                if tweet_legacy.get("id_str") not in id_str_list:
                    result.append(tweet)
                    id_str_list.append(tweet_legacy.get("id_str"))

        return result

    def fetch(self):
        result = self.twitter_session.loop.run_until_complete(self.get_like_jsons())
        return result

    def _match_data(self, data: dict) -> dict:
        match data:
            case {
                "core": {"user_results": {"result": {"legacy": author}}},
                "legacy": tweet,
                "source": via_html,
            }:
                via = re.findall("^<.+?>([^<]*?)<.+?>$", via_html)[0]
                r = {
                    "author": author,
                    "tweet": tweet,
                    "via": via,
                }
                return r
        return {}

    def _match_extended_entities_tweet(self, tweet: dict) -> dict:
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
                r = {
                    "author_id": author_id,
                    "created_at": created_at,
                    # "entities": entities,
                    "extended_entities": extended_entities,
                    "id_str": id_str,
                    "text": full_text,
                }
                return r
        return {}

    def _match_entities_tweet(self, tweet: dict) -> dict:
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
        """tweet["extended_entities"]["media"]から保存対象のメディアURLを取得する

        Args:
            media_dict (dict): tweet["extended_entities"]["media"]

        Returns:
            str: 成功時メディアURL、引数や辞書構造が不正だった場合空文字列を返す
        """
        match media:
            case {
                "type": "photo",
                "media_url_https": media_url,
            }:
                media_filename = Path(media_url).name
                media_thumbnail_url = media_url + ":large"
                media_url = media_url + ":orig"
                return {
                    "media_filename": media_filename,
                    "media_url": media_url,
                    "media_thumbnail_url": media_thumbnail_url,
                }
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
                return {
                    "media_filename": media_filename,
                    "media_url": media_url,
                    "media_thumbnail_url": media_thumbnail_url,
                }
        return {}

    def to_convert_TweetInfo(self, fetched_tweets: list[dict]) -> list[TweetInfo]:
        # 辞書パース
        # fetched_tweets は Likes のツイートが入っている想定
        # media を含むかどうかはこの時点では don't care
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

            # tweet_url を探索
            # entities内のexpanded_urlを採用する
            # ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
            tweet_url = extended_entities.get("media", [{}])[0].get("expanded_url", "")

            # created_at を解釈する
            # Like した時点の時間が取得できる？
            td_format = "%a %b %d %H:%M:%S +0000 %Y"
            dts_format = "%Y-%m-%d %H:%M:%S"
            dst = datetime.strptime(created_at, td_format).strftime(dts_format)

            # media情報について収集する
            # 1ツイートに対してmedia は最大4つ添付されている
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
        return result

    def to_convert_ExternalLink(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
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
            dst = datetime.strptime(created_at, td_format).strftime(dts_format)

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
        return result


if __name__ == "__main__":
    import configparser
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_noapi"]

    if config.getboolean("is_twitter_noapi"):
        username = config["username"]
        password = config["password"]
        like = NoAPILikeFetcher(username, password)

        # like取得
        # fetched_tweets = like.fetch()

        # キャッシュから読み込み
        base_path = Path(like.TWITTER_CACHE_PATH)
        fetched_tweets = []
        for cache_path in base_path.glob("*content_cache*"):
            with cache_path.open("r", encoding="utf8") as fin:
                json_dict = json.load(fin)
                fetched_tweets.append(json_dict)

        # メディア取得
        # tweet_info_list = like.to_convert_TweetInfo(fetched_tweets)
        # pprint.pprint(tweet_info_list)

        # 外部リンク取得
        config = config_parser
        config["skeb"]["is_skeb_trace"] = "False"
        lsb = LinkSearcher.create(config)
        external_link_list = like.to_convert_ExternalLink(fetched_tweets, lsb)
        pprint.pprint(external_link_list)
