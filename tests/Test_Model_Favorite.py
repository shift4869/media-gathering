import sys
import unittest

from media_gathering.model import Favorite


class TestModelFavorite(unittest.TestCase):
    def make_instance(self, index: int) -> Favorite:
        is_exist_saved_file = True
        img_filename = f"img_filename_{index}"
        url = f"url_{index}"
        url_thumbnail = f"url_thumbnail_{index}"
        tweet_id = f"tweet_id_{index}"
        tweet_url = f"tweet_url_{index}"
        created_at = "created_at"
        user_id = f"user_id_{index}"
        user_name = f"user_name_{index}"
        screan_name = f"screan_name_{index}"
        tweet_text = f"tweet_text_{index}"
        tweet_via = "tweet_via"
        saved_localpath = "saved_localpath"
        saved_created_at = "saved_created_at"
        media_size = index
        media_blob = None
        return Favorite(
            is_exist_saved_file,
            img_filename,
            url,
            url_thumbnail,
            tweet_id,
            tweet_url,
            created_at,
            user_id,
            user_name,
            screan_name,
            tweet_text,
            tweet_via,
            saved_localpath,
            saved_created_at,
            media_size,
            media_blob
        )

    def test_init(self):
        is_exist_saved_file = True
        img_filename = "img_filename"
        url = "url"
        url_thumbnail = "url_thumbnail"
        tweet_id = "tweet_id"
        tweet_url = "tweet_url"
        created_at = "created_at"
        user_id = "user_id"
        user_name = "user_name"
        screan_name = "screan_name"
        tweet_text = "tweet_text"
        tweet_via = "tweet_via"
        saved_localpath = "saved_localpath"
        saved_created_at = "saved_created_at"
        media_size = 10
        media_blob = None
        actual = Favorite(
            is_exist_saved_file,
            img_filename, url, url_thumbnail,
            tweet_id, tweet_url,
            created_at,
            user_id, user_name, screan_name,
            tweet_text, tweet_via,
            saved_localpath, saved_created_at,
            media_size, media_blob
        )
        self.assertEqual(is_exist_saved_file, actual.is_exist_saved_file)
        self.assertEqual(img_filename, actual.img_filename)
        self.assertEqual(url, actual.url)
        self.assertEqual(url_thumbnail, actual.url_thumbnail)
        self.assertEqual(tweet_id, actual.tweet_id)
        self.assertEqual(tweet_url, actual.tweet_url)
        self.assertEqual(created_at, actual.created_at)
        self.assertEqual(user_id, actual.user_id)
        self.assertEqual(user_name, actual.user_name)
        self.assertEqual(screan_name, actual.screan_name)
        self.assertEqual(tweet_text, actual.tweet_text)
        self.assertEqual(tweet_via, actual.tweet_via)
        self.assertEqual(saved_localpath, actual.saved_localpath)
        self.assertEqual(saved_created_at, actual.saved_created_at)
        self.assertEqual(media_size, actual.media_size)
        self.assertEqual(media_blob, actual.media_blob)

        params = {
            "is_exist_saved_file": is_exist_saved_file,
            "img_filename": img_filename,
            "url": url,
            "url_thumbnail": url_thumbnail,
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "created_at": created_at,
            "user_id": user_id,
            "user_name": user_name,
            "screan_name": screan_name,
            "tweet_text": tweet_text,
            "tweet_via": tweet_via,
            "saved_localpath": saved_localpath,
            "saved_created_at": saved_created_at,
            "media_size": media_size,
            "media_blob": media_blob,
        }
        with self.assertRaises(ValueError):
            actual = Favorite(
                params["is_exist_saved_file"],
                params["img_filename"],
                params["url"],
                params["url_thumbnail"],
                params["tweet_id"],
                params["tweet_url"],
                params["created_at"],
                params["user_id"],
                params["user_name"],
                params["screan_name"],
                params["tweet_text"],
                params["tweet_via"],
                params["saved_localpath"],
                params["saved_created_at"],
                -1,
                params["media_blob"]
            )
        for k in reversed(params.keys()):
            if k == "media_size":
                params[k] = "invalid_media_size"
            else:
                params[k] = -1
            with self.assertRaises(TypeError):
                actual = Favorite(
                    params["is_exist_saved_file"],
                    params["img_filename"],
                    params["url"],
                    params["url_thumbnail"],
                    params["tweet_id"],
                    params["tweet_url"],
                    params["created_at"],
                    params["user_id"],
                    params["user_name"],
                    params["screan_name"],
                    params["tweet_text"],
                    params["tweet_via"],
                    params["saved_localpath"],
                    params["saved_created_at"],
                    params["media_size"],
                    params["media_blob"]
                )

    def test_repr(self):
        record = self.make_instance(1)
        columns = ", ".join([
            f"{k}={v}"
            for k, v in record.__dict__.items() if k[0] != "_"
        ])
        expect = f"<{record.__class__.__name__}({columns})>"
        actual = repr(record)
        self.assertEqual(expect, actual)

    def test_eq(self):
        record_1 = self.make_instance(1)
        record_2 = self.make_instance(2)
        record_another_1 = self.make_instance(1)

        self.assertTrue(record_1 == record_another_1)
        self.assertFalse(record_1 == record_2)
        self.assertFalse(record_1 == "not_equal_instance")
        self.assertFalse(record_1 == -1)

    def test_to_dict(self):
        record = self.make_instance(1)
        actual = record.to_dict()
        expect = {
            "id": None,
            "is_exist_saved_file": True,
            "img_filename": "img_filename_1",
            "url": "url_1",
            "url_thumbnail": "url_thumbnail_1",
            "tweet_id": "tweet_id_1",
            "tweet_url": "tweet_url_1",
            "created_at": "created_at",
            "user_id": "user_id_1",
            "user_name": "user_name_1",
            "screan_name": "screan_name_1",
            "tweet_text": "tweet_text_1",
            "tweet_via": "tweet_via",
            "saved_localpath": "saved_localpath",
            "saved_created_at": "saved_created_at",
            "media_size": 1,
            "media_blob": None,
        }
        self.assertEqual(expect, actual)

    def test_to_create(self):
        record = self.make_instance(1)
        actual = Favorite.create(record.to_dict())
        self.assertEqual(record.to_dict(), actual.to_dict())

        with self.assertRaises(ValueError):
            actual = Favorite.create({"invalid_key": "invalid_value"})


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
