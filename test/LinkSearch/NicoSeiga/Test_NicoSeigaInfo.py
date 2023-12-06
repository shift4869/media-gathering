import sys
import unittest

from media_gathering.LinkSearch.NicoSeiga.Authorid import Authorid
from media_gathering.LinkSearch.NicoSeiga.Authorname import Authorname
from media_gathering.LinkSearch.NicoSeiga.Illustid import Illustid
from media_gathering.LinkSearch.NicoSeiga.Illustname import Illustname
from media_gathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo


class TestNicoSeigaInfo(unittest.TestCase):
    def test_NicoSeigaInfo(self):
        author_id = Authorid(12345678)
        illust_id = Illustid(11111111)
        illust_name = Illustname("作品名1")
        author_name = Authorname("作成者1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        self.assertEqual(illust_id, illust_info.illust_id)
        self.assertEqual(illust_name, illust_info.illust_name)
        self.assertEqual(author_id, illust_info.author_id)
        self.assertEqual(author_name, illust_info.author_name)

    def test_is_valid(self):
        author_id = Authorid(12345678)
        illust_id = Illustid(11111111)
        illust_name = Illustname("作品名1")
        author_name = Authorname("作成者1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        self.assertEqual(True, illust_info._is_valid())

        with self.assertRaises(TypeError):
            illust_info = NicoSeigaInfo("invalid illust_id", illust_name, author_id, author_name)
        with self.assertRaises(TypeError):
            illust_info = NicoSeigaInfo(illust_id, "invalid illust_name", author_id, author_name)
        with self.assertRaises(TypeError):
            illust_info = NicoSeigaInfo(illust_id, illust_name, "invalid author_id", author_name)
        with self.assertRaises(TypeError):
            illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, "invalid author_name")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
