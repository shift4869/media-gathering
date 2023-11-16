import sys
import unittest

from PictureGathering.tac.TweetInfo import TweetInfo


class TestTweetInfo(unittest.TestCase):
    def setUp(self):
        pass

    def test_TweetInfo_init(self):
        dummy_media_filename = "dummy_media_filename"
        dummy_media_url = "dummy_media_url"
        dummy_media_thumbnail_url = "dummy_media_thumbnail_url"
        dummy_tweet_id = "dummy_tweet_id"
        dummy_tweet_url = "dummy_tweet_url"
        dummy_created_at = "dummy_created_at"
        dummy_user_id = "dummy_user_id"
        dummy_user_name = "dummy_user_name"
        dummy_screan_name = "dummy_screan_name"
        dummy_tweet_text = "dummy_tweet_text"
        dummy_tweet_via = "dummy_tweet_via"

        tweetinfo = TweetInfo(
            dummy_media_filename,
            dummy_media_url,
            dummy_media_thumbnail_url,
            dummy_tweet_id,
            dummy_tweet_url,
            dummy_created_at,
            dummy_user_id,
            dummy_user_name,
            dummy_screan_name,
            dummy_tweet_text,
            dummy_tweet_via
        )

        self.assertEqual(dummy_media_url, tweetinfo.media_url)
        self.assertEqual(dummy_media_thumbnail_url, tweetinfo.media_thumbnail_url)
        self.assertEqual(dummy_tweet_id, tweetinfo.tweet_id)
        self.assertEqual(dummy_tweet_url, tweetinfo.tweet_url)
        self.assertEqual(dummy_created_at, tweetinfo.created_at)
        self.assertEqual(dummy_user_id, tweetinfo.user_id)
        self.assertEqual(dummy_user_name, tweetinfo.user_name)
        self.assertEqual(dummy_screan_name, tweetinfo.screan_name)
        self.assertEqual(dummy_tweet_text, tweetinfo.tweet_text)
        self.assertEqual(dummy_tweet_via, tweetinfo.tweet_via)

    def test_create(self):
        dummy_media_filename = "dummy_media_filename"
        dummy_media_url = "dummy_media_url"
        dummy_media_thumbnail_url = "dummy_media_thumbnail_url"
        dummy_tweet_id = "dummy_tweet_id"
        dummy_tweet_url = "dummy_tweet_url"
        dummy_created_at = "dummy_created_at"
        dummy_user_id = "dummy_user_id"
        dummy_user_name = "dummy_user_name"
        dummy_screan_name = "dummy_screan_name"
        dummy_tweet_text = "dummy_tweet_text"
        dummy_tweet_via = "dummy_tweet_via"

        arg_dict = {
            "media_filename": dummy_media_filename,
            "media_url": dummy_media_url,
            "media_thumbnail_url": dummy_media_thumbnail_url,
            "tweet_id": dummy_tweet_id,
            "tweet_url": dummy_tweet_url,
            "created_at": dummy_created_at,
            "user_id": dummy_user_id,
            "user_name": dummy_user_name,
            "screan_name": dummy_screan_name,
            "tweet_text": dummy_tweet_text,
            "tweet_via": dummy_tweet_via,
        }
        tweetinfo = TweetInfo.create(arg_dict)

        self.assertEqual(dummy_media_url, tweetinfo.media_url)
        self.assertEqual(dummy_media_thumbnail_url, tweetinfo.media_thumbnail_url)
        self.assertEqual(dummy_tweet_id, tweetinfo.tweet_id)
        self.assertEqual(dummy_tweet_url, tweetinfo.tweet_url)
        self.assertEqual(dummy_created_at, tweetinfo.created_at)
        self.assertEqual(dummy_user_id, tweetinfo.user_id)
        self.assertEqual(dummy_user_name, tweetinfo.user_name)
        self.assertEqual(dummy_screan_name, tweetinfo.screan_name)
        self.assertEqual(dummy_tweet_text, tweetinfo.tweet_text)
        self.assertEqual(dummy_tweet_via, tweetinfo.tweet_via)

        with self.assertRaises(ValueError):
            tweetinfo = TweetInfo.create({})

    def test_to_dict(self):
        dummy_media_filename = "dummy_media_filename"
        dummy_media_url = "dummy_media_url"
        dummy_media_thumbnail_url = "dummy_media_thumbnail_url"
        dummy_tweet_id = "dummy_tweet_id"
        dummy_tweet_url = "dummy_tweet_url"
        dummy_created_at = "dummy_created_at"
        dummy_user_id = "dummy_user_id"
        dummy_user_name = "dummy_user_name"
        dummy_screan_name = "dummy_screan_name"
        dummy_tweet_text = "dummy_tweet_text"
        dummy_tweet_via = "dummy_tweet_via"

        arg_dict = {
            "media_filename": dummy_media_filename,
            "media_url": dummy_media_url,
            "media_thumbnail_url": dummy_media_thumbnail_url,
            "tweet_id": dummy_tweet_id,
            "tweet_url": dummy_tweet_url,
            "created_at": dummy_created_at,
            "user_id": dummy_user_id,
            "user_name": dummy_user_name,
            "screan_name": dummy_screan_name,
            "tweet_text": dummy_tweet_text,
            "tweet_via": dummy_tweet_via,
        }
        tweetinfo = TweetInfo.create(arg_dict)

        self.assertEqual(arg_dict, tweetinfo.to_dict())


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
