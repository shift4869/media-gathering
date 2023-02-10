# coding: utf-8
from datetime import datetime
from logging import INFO, getLogger
from pathlib import Path
import asyncio
import json
import pprint
import random
import re
import shutil
import sys
import urllib.parse

from pyppeteer.page import Page
from requests_html import HTML
from requests.models import Response

from PictureGathering.LinkSearch.LinkSearcher import LinkSearcher
from PictureGathering.Model import ExternalLink
from PictureGathering.noapi.Password import Password
from PictureGathering.noapi.TweetInfo import TweetInfo
from PictureGathering.noapi.TwitterSession import TwitterSession
from PictureGathering.noapi.Username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


class NoAPILikeFetcher():
    username: Username
    password: Password
    target_username: Username
    twitter_session: TwitterSession

    # キャッシュファイルパス
    TWITTER_CACHE_PATH = Path(__file__).parent / "cache/"

    def __init__(self, username: Username | str, password: Password | str, target_username: Username | str) -> None:
        if isinstance(username, str):
            username = Username(username)
        if isinstance(password, str):
            password = Password(password)
        if isinstance(target_username, str):
            target_username = Username(target_username)

        if not (isinstance(username, Username) and username.name != ""):
            raise ValueError("username is not Username or empty.")
        if not (isinstance(password, Password) and password.password != ""):
            raise ValueError("password is not Password or empty.")
        if not (isinstance(target_username, Username) and target_username.name != ""):
            raise ValueError("password is not Username or empty.")

        self.username = username
        self.password = password
        self.target_username = target_username
        self.twitter_session = TwitterSession.create(username=username, password=password)

    async def get_like_jsons(self) -> list[dict]:
        """Likes ページをクロールしてロード時のJSONをキャプチャする

        Notes:
            対象URLは "https://twitter.com/{self.target_username.name}/likes"
                (self.twitter_session.LIKES_URL_TEMPLATE.format(self.target_username.name))

        Returns:
            list[str]: ツイートオブジェクトを表すJSONリスト
        """
        logger.info("Fetched Tweet by No API -> start")

        # セッション使用準備
        await self.twitter_session.prepare()
        logger.info("session use prepared.")

        # Likes ページに遷移
        # スクロール操作を行うため、pageを保持しておく
        url = self.twitter_session.LIKES_URL_TEMPLATE.format(self.target_username.name)
        res = await self.twitter_session.get(url)
        await res.html.arender(keep_page=True)
        html: HTML = res.html
        page: Page = html.page
        logger.info("Getting Likes page is success.")

        # キャッシュ保存場所の準備
        redirect_urls = []
        content_list = []
        base_path = Path(self.TWITTER_CACHE_PATH)
        if base_path.is_dir():
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # レスポンス監視用リスナー
        async def response_listener(response: Response):
            if "Like" in response.url:
                # レスポンスが Like 関連ならば
                redirect_urls.append(response.url)
                if "application/json" in response.headers.get("content-type", ""):
                    # レスポンスがJSONならばキャッシュに保存
                    content = await response.json()
                    n = len(content_list)
                    with Path(base_path / f"content_cache{n}.txt").open("w", encoding="utf8") as fout:
                        json.dump(content, fout)
                    content_list.append(content)
        page.on("response", lambda response: asyncio.ensure_future(response_listener(response)))

        # スクロール時の待ち秒数をランダムに生成するメソッド
        def get_wait_millisecond() -> float:
            pn = (random.random() - 0.5) * 1.0  # [-0.5, 0.5)
            candidate_sec = (pn + EACH_SCROLL_WAIT_AVERAGE_SECONDS) * 1000.0
            return float(max(candidate_sec, 1000.0))  # [1000.0, 2000.0)

        # Likes ページをスクロールして読み込んでいく
        # ページ下部に達した時に次のツイートが読み込まれる
        # このときレスポンス監視用リスナーがレスポンスをキャッチする
        FAV_GET_MAX_LOOP = 40
        EACH_SCROLL_WAIT_AVERAGE_SECONDS = 1.5
        logger.info("Getting Likes page fetched -> start")
        for i in range(FAV_GET_MAX_LOOP):
            await page.evaluate("""
                () => {
                    let elm = document.documentElement;
                    let bottom = elm.scrollHeight - elm.clientHeight;
                    window.scroll(0, bottom);
                }
            """)
            await page.waitFor(
                get_wait_millisecond()
            )
            logger.info(f"({i+1}/{FAV_GET_MAX_LOOP}) pages fetched.")
        await page.waitFor(2000)
        logger.info("Getting Likes page fetched -> done")

        # リダイレクトURLをキャッシュに保存
        if redirect_urls:
            with Path(base_path / "redirect_urls.txt").open("w", encoding="utf8") as fout:
                fout.write(pprint.pformat(redirect_urls))

        # キャッシュから読み込み
        # content_list と result はほぼ同一の内容になる
        # 違いは result は json.dump→json.load したときに、エンコード等が吸収されていること
        result: list[dict] = []
        for i, content in enumerate(content_list):
            with Path(base_path / f"content_cache{i}.txt").open("r", encoding="utf8") as fin:
                json_dict = json.load(fin)
                result.append(json_dict)

        logger.info("Fetched Tweet by No API -> done")
        return result

    def interpret_json(self, tweet: dict, id_str_list: list[str] = None) -> list[dict]:
        """ツイートオブジェクトの辞書構成をたどり、ツイートがメディアを含むかどうか調べる

        Note:
           legacyを直下に含むツイートオブジェクトを引数として受け取り、以下のようにresultを返す
           (1)tweet.legacyにメディアが添付されている場合、resultにtweetを追加
           (2)tweet.legacyに外部リンクが含まれている場合、resultにtweetを追加
           (3)RTされているツイートにメディアが添付されている場合、resultにtweet.retweeted_status_result.resultを追加
           (3)引用RTされているツイートにメディアが添付されている場合、resultにtweet.quoted_status_result.resultを追加
           (5)引用RTがRTされているツイートの場合、
              resultにtweet.retweeted_status_result.result.quoted_status_result.resultを追加

           引用RTはRTできるがRTは引用RTできないので無限ループにはならない（最大深さ2）
           id_strが重複しているツイートは格納しない

        Args:
            tweet (dict): legacyを直下に含むツイートオブジェクト
            id_str_list (list[str] | None): 格納済みツイートのid_strリスト

        Returns:
            result list[dict]: 上記にて出力された辞書リスト
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
            # リツイートオブジェクトに引用RTフラグも立っている場合
            if retweeted_tweet.get("is_quote_status") and retweeted_tweet.get("quoted_status_result"):
                quoted_tweet = retweeted_tweet.get("quoted_status_result", {}).get("result", {})
                quoted_tweet_legacy = quoted_tweet.get("legacy", {})
                if quoted_tweet_legacy.get("extended_entities"):
                    if quoted_tweet_legacy.get("id_str") not in id_str_list:
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

    def fetch(self) -> list[dict]:
        """Likes ページをクロールしてロード時のJSONをキャプチャする

        Returns:
            list[dict]: ツイートオブジェクトを表すJSONリスト
        """
        result = self.twitter_session.loop.run_until_complete(self.get_like_jsons())
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
            expanded_urls (dict): entities に含まれる expanded_url を含む辞書, 解析失敗時は空辞書
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

            # tweet_url を取得
            # entities 内の expanded_url を採用する
            # ex. https://twitter.com/{screan_name}/status/{tweet_id}/photo/1
            tweet_url = extended_entities.get("media", [{}])[0].get("expanded_url", "")

            # created_at を解釈する
            # Like した時点の時間が取得できる？
            td_format = "%a %b %d %H:%M:%S +0000 %Y"
            dts_format = "%Y-%m-%d %H:%M:%S"
            dst = datetime.strptime(created_at, td_format).strftime(dts_format)

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
        return result

    def to_convert_ExternalLink(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> list[ExternalLink]:
        """取得した Likes ツイートオブジェクトから ExternalLink のリストを返す

        Args:
            fetched_tweets (list[dict]): self.fetch() 後の返り値
            link_searcher (LinkSearcher): 外部リンク探索用LinkSearcher
 
        Returns:
            list[ExternalLink]: ExternalLink リスト
        """
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
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_noapi"]

    if config.getboolean("is_twitter_noapi"):
        username = config["username"]
        password = config["password"]
        target_username = config["target_username"]
        like = NoAPILikeFetcher(Username(username), Password(password), Username(target_username))

        # like取得
        fetched_tweets = like.fetch()

        # キャッシュから読み込み
        base_path = Path(like.TWITTER_CACHE_PATH)
        fetched_tweets = []
        for cache_path in base_path.glob("*content_cache*"):
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
