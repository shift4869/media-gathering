import sys
import unittest

from media_gathering.model import ExternalLink


class TestModelExternalLink(unittest.TestCase):
    def make_instance(self, index: int) -> ExternalLink:
        external_link_url = f"external_link_url_{index}"
        tweet_id = f"tweet_id_{index}"
        tweet_url = f"tweet_url_{index}"
        created_at = "created_at"
        user_id = f"user_id_{index}"
        user_name = f"user_name_{index}"
        screan_name = f"screan_name_{index}"
        tweet_text = f"tweet_text_{index}"
        tweet_via = "tweet_via"
        saved_created_at = "saved_created_at"
        link_type = "link_type"

        return ExternalLink(
            external_link_url,
            tweet_id,
            tweet_url,
            created_at,
            user_id,
            user_name,
            screan_name,
            tweet_text,
            tweet_via,
            saved_created_at,
            link_type
        )

    def test_init(self):
        external_link_url = "external_link_url"
        tweet_id = "tweet_id"
        tweet_url = "tweet_url"
        created_at = "created_at"
        user_id = "user_id"
        user_name = "user_name"
        screan_name = "screan_name"
        tweet_text = "tweet_text"
        tweet_via = "tweet_via"
        saved_created_at = "saved_created_at"
        link_type = "link_type"
        actual = ExternalLink(
            external_link_url,
            tweet_id, tweet_url,
            created_at,
            user_id, user_name, screan_name,
            tweet_text, tweet_via,
            saved_created_at,
            link_type
        )
        self.assertEqual(external_link_url, actual.external_link_url)
        self.assertEqual(tweet_id, actual.tweet_id)
        self.assertEqual(tweet_url, actual.tweet_url)
        self.assertEqual(created_at, actual.created_at)
        self.assertEqual(user_id, actual.user_id)
        self.assertEqual(user_name, actual.user_name)
        self.assertEqual(screan_name, actual.screan_name)
        self.assertEqual(tweet_text, actual.tweet_text)
        self.assertEqual(tweet_via, actual.tweet_via)
        self.assertEqual(saved_created_at, actual.saved_created_at)
        self.assertEqual(link_type, actual.link_type)

        params = {
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
        }
        for k in reversed(params.keys()):
            params[k] = -1
            with self.assertRaises(TypeError):
                actual = ExternalLink(
                    params["external_link_url"],
                    params["tweet_id"],
                    params["tweet_url"],
                    params["created_at"],
                    params["user_id"],
                    params["user_name"],
                    params["screan_name"],
                    params["tweet_text"],
                    params["tweet_via"],
                    params["saved_created_at"],
                    params["link_type"]
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
            "external_link_url": "external_link_url_1",
            "tweet_id": "tweet_id_1",
            "tweet_url": "tweet_url_1",
            "created_at": "created_at",
            "user_id": "user_id_1",
            "user_name": "user_name_1",
            "screan_name": "screan_name_1",
            "tweet_text": "tweet_text_1",
            "tweet_via": "tweet_via",
            "saved_created_at": "saved_created_at",
            "link_type": "link_type",
        }
        self.assertEqual(expect, actual)

    def test_to_create(self):
        record = self.make_instance(1)
        actual = ExternalLink.create(record.to_dict())
        self.assertEqual(record.to_dict(), actual.to_dict())

        with self.assertRaises(ValueError):
            actual = ExternalLink.create({"invalid_key": "invalid_value"})


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
