import sys
import unittest

from media_gathering.model import DeleteTarget


class TestModelDeleteTarget(unittest.TestCase):
    def make_instance(self, index: int) -> DeleteTarget:
        tweet_id = f"tweet_id_{index}"
        delete_done = False
        created_at = "created_at"
        deleted_at = "deleted_at"
        tweet_text = f"tweet_text_{index}"
        add_num = index + 1
        del_num = index

        return DeleteTarget(
            tweet_id,
            delete_done,
            created_at,
            deleted_at,
            tweet_text,
            add_num,
            del_num
        )

    def test_init(self):
        tweet_id = "tweet_id"
        delete_done = False
        created_at = "created_at"
        deleted_at = "deleted_at"
        tweet_text = "tweet_text"
        add_num = 0
        del_num = 0
        actual = DeleteTarget(
            tweet_id,
            delete_done,
            created_at,
            deleted_at,
            tweet_text,
            add_num,
            del_num
        )
        self.assertEqual(tweet_id, actual.tweet_id)
        self.assertEqual(delete_done, actual.delete_done)
        self.assertEqual(created_at, actual.created_at)
        self.assertEqual(deleted_at, actual.deleted_at)
        self.assertEqual(tweet_text, actual.tweet_text)
        self.assertEqual(add_num, actual.add_num)
        self.assertEqual(del_num, actual.del_num)

        params = {
            "tweet_id": "tweet_id",
            "delete_done": False,
            "created_at": "created_at",
            "deleted_at": "deleted_at",
            "tweet_text": "tweet_text",
            "add_num": 0,
            "del_num": 0,
        }
        with self.assertRaises(ValueError):
            actual = DeleteTarget(
                params["tweet_id"],
                params["delete_done"],
                params["created_at"],
                params["deleted_at"],
                params["tweet_text"],
                -1,
                params["del_num"]
            )
        with self.assertRaises(ValueError):
            actual = DeleteTarget(
                params["tweet_id"],
                params["delete_done"],
                params["created_at"],
                params["deleted_at"],
                params["tweet_text"],
                params["add_num"],
                -1
            )
        for k in reversed(params.keys()):
            if "num" in k:
                params[k] = f"invalid_{k}"
            else:
                params[k] = -1
            with self.assertRaises(TypeError):
                actual = DeleteTarget(
                    params["tweet_id"],
                    params["delete_done"],
                    params["created_at"],
                    params["deleted_at"],
                    params["tweet_text"],
                    params["add_num"],
                    params["del_num"]
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
        index = 1
        record = self.make_instance(index)
        actual = record.to_dict()
        expect = {
            "id": None,
            "tweet_id": f"tweet_id_{index}",
            "delete_done": False,
            "created_at": "created_at",
            "deleted_at": "deleted_at",
            "tweet_text": f"tweet_text_{index}",
            "add_num": index + 1,
            "del_num": index,
        }
        self.assertEqual(expect, actual)

    def test_to_create(self):
        record = self.make_instance(1)
        actual = DeleteTarget.create(record.to_dict())
        self.assertEqual(record.to_dict(), actual.to_dict())

        with self.assertRaises(ValueError):
            actual = DeleteTarget.create({"invalid_key": "invalid_value"})


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
