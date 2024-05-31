import sys
import unittest

from media_gathering.tac.tweet_info import TweetInfo


class TestTweetInfo(unittest.TestCase):
    def setUp(self):
        self.instance = self.make_instance()

    def get_arg_dict(self) -> dict:
        return {
            "media_filename": "dummy_media_filename",
            "media_url": "dummy_media_url",
            "media_thumbnail_url": "dummy_media_thumbnail_url",
            "tweet_id": "dummy_tweet_id",
            "tweet_url": "dummy_tweet_url",
            "created_at": "dummy_created_at",
            "user_id": "dummy_user_id",
            "user_name": "dummy_user_name",
            "screan_name": "dummy_screan_name",
            "tweet_text": "dummy_tweet_text",
            "tweet_via": "dummy_tweet_via",
        }

    def make_instance(self, error_occur_index: int = -1) -> TweetInfo:
        arg_dict = self.get_arg_dict()
        if error_occur_index > -1:
            for i, k in enumerate(arg_dict.keys()):
                if i == error_occur_index:
                    arg_dict[k] = None

        tweetinfo = TweetInfo(
            arg_dict["media_filename"],
            arg_dict["media_url"],
            arg_dict["media_thumbnail_url"],
            arg_dict["tweet_id"],
            arg_dict["tweet_url"],
            arg_dict["created_at"],
            arg_dict["user_id"],
            arg_dict["user_name"],
            arg_dict["screan_name"],
            arg_dict["tweet_text"],
            arg_dict["tweet_via"],
        )
        return tweetinfo

    def test_TweetInfo_init(self):
        tweetinfo = self.instance
        arg_dict = self.get_arg_dict()

        self.assertEqual(arg_dict["media_filename"], tweetinfo.media_filename)
        self.assertEqual(arg_dict["media_url"], tweetinfo.media_url)
        self.assertEqual(arg_dict["media_thumbnail_url"], tweetinfo.media_thumbnail_url)
        self.assertEqual(arg_dict["tweet_id"], tweetinfo.tweet_id)
        self.assertEqual(arg_dict["tweet_url"], tweetinfo.tweet_url)
        self.assertEqual(arg_dict["created_at"], tweetinfo.created_at)
        self.assertEqual(arg_dict["user_id"], tweetinfo.user_id)
        self.assertEqual(arg_dict["user_name"], tweetinfo.user_name)
        self.assertEqual(arg_dict["screan_name"], tweetinfo.screan_name)
        self.assertEqual(arg_dict["tweet_text"], tweetinfo.tweet_text)
        self.assertEqual(arg_dict["tweet_via"], tweetinfo.tweet_via)

        n = len(arg_dict.keys())
        for i in range(n):
            with self.assertRaises(TypeError):
                tweetinfo = self.make_instance(i)

    def test_create(self):
        arg_dict = self.get_arg_dict()
        tweetinfo = TweetInfo.create(arg_dict)

        self.assertEqual(self.instance.media_filename, tweetinfo.media_filename)
        self.assertEqual(self.instance.media_url, tweetinfo.media_url)
        self.assertEqual(self.instance.media_thumbnail_url, tweetinfo.media_thumbnail_url)
        self.assertEqual(self.instance.tweet_id, tweetinfo.tweet_id)
        self.assertEqual(self.instance.tweet_url, tweetinfo.tweet_url)
        self.assertEqual(self.instance.created_at, tweetinfo.created_at)
        self.assertEqual(self.instance.user_id, tweetinfo.user_id)
        self.assertEqual(self.instance.user_name, tweetinfo.user_name)
        self.assertEqual(self.instance.screan_name, tweetinfo.screan_name)
        self.assertEqual(self.instance.tweet_text, tweetinfo.tweet_text)
        self.assertEqual(self.instance.tweet_via, tweetinfo.tweet_via)

        with self.assertRaises(ValueError):
            tweetinfo = TweetInfo.create({})

    def test_to_dict(self):
        arg_dict = self.get_arg_dict()
        tweetinfo = TweetInfo.create(arg_dict)
        self.assertEqual(arg_dict, tweetinfo.to_dict())


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
