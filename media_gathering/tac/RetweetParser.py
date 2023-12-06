import orjson

from media_gathering.link_search.LinkSearcher import LinkSearcher
from media_gathering.tac.ParserBase import ParserBase
from media_gathering.Util import find_values


class RetweetParser(ParserBase):
    def __init__(self, fetched_tweets: list[dict], link_searcher: LinkSearcher) -> None:
        super().__init__(fetched_tweets, link_searcher)

    def _interpret(self, tweet: dict) -> list[dict]:
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
        seen_id = []

        # (1)ツイートにメディアが添付されている場合
        if find_values(tweet, "media", False, ["legacy", "extended_entities"]):
            self._interpret_resister(tweet, result, seen_id)

        # (2)ツイートに外部リンクが含まれている場合
        if urls_dict := find_values(tweet, "urls", False, ["legacy", "entities"]):
            urls_dict = urls_dict[0]
            if isinstance(urls_dict, list):
                url_flags = [url_dict.get("expanded_url", "") != "" for url_dict in urls_dict]
                if any(url_flags):
                    self._interpret_resister(tweet, result, seen_id)

        # (3)メディアが添付されているツイートがRTされている場合
        if retweeted_tweet := find_values(tweet, "retweeted_status_result", False, ["legacy"]):
            retweeted_tweet = retweeted_tweet[0].get("result", {})
            self._interpret_resister(retweeted_tweet, result, seen_id)

        # (4)メディアが添付されているツイートが引用RTされている場合
        if quoted_tweet := find_values(tweet, "quoted_status_result", False, [""]):
            quoted_tweet = quoted_tweet[0].get("result", {})
            self._interpret_resister(quoted_tweet, result, seen_id)

        # (5)メディアが添付されているツイートの引用RTがRTされている場合
        retweeted_tweet = find_values(tweet, "retweeted_status_result", False)
        quoted_tweet = find_values(tweet, "quoted_status_result", False)
        if retweeted_tweet and quoted_tweet:
            quoted_tweet = quoted_tweet[0].get("result", {})
            self._interpret_resister(quoted_tweet, result, seen_id)

        return result


if __name__ == "__main__":
    import re
    from pathlib import Path

    from media_gathering.link_search.FetcherBase import FetcherBase
    from media_gathering.link_search.URL import URL

    # キャッシュから読み込み
    base_path = Path("./test/tac/cache/expect/content_cache_timeline_test.json")
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
    parser = RetweetParser([fetched_tweets], link_searcher)

    # TweetInfo リスト取得
    tweet_info_list = parser.parse_to_TweetInfo()
    print(len(tweet_info_list))

    # 外部リンク取得
    external_link_list = parser.parse_to_ExternalLink()
    print(len(external_link_list))
