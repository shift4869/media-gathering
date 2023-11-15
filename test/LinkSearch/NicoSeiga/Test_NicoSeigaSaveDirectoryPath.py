"""NicoSeigaSaveDirectoryPath のテスト

NicoSeigaSaveDirectoryPathを表すクラスをテストする
"""
import re
import shutil
import sys
import unittest
from pathlib import Path

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSaveDirectoryPath import NicoSeigaSaveDirectoryPath


class TestNicoSeigaSaveDirectoryPath(unittest.TestCase):
    def test_NicoSeigaSaveDirectoryPath(self):
        illust_id = Illustid(12345678)
        illust_name = Illustname("作品名1")
        author_id = Authorid(1234567)
        author_name = Authorname("作者名1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        def traverse(base_path) -> Path:
            illust_id = illust_info.illust_id.id
            illust_name = illust_info.illust_name.name
            author_id = illust_info.author_id.id
            author_name = illust_info.author_name.name

            sd_path = ""
            save_path = Path(base_path)
            filelist = []
            filelist_tp = [(sp.stat().st_mtime, sp.name) for sp in save_path.glob("*") if sp.is_dir()]
            for mtime, path in sorted(filelist_tp, reverse=True):
                filelist.append(path)

            regex = re.compile(r'.*\(([0-9]*)\)$')
            for dir_name in filelist:
                result = regex.match(dir_name)
                if result:
                    ai = result.group(1)
                    if ai == str(author_id):
                        sd_path = f"./{dir_name}/{illust_name}({illust_id})/"
                        break

            if sd_path == "":
                sd_path = f"./{author_name}({author_id})/{illust_name}({illust_id})/"

            return save_path / sd_path

        base_path = Path("./test/LinkSearch/NicoSeiga")
        expect = traverse(base_path)
        if expect.is_dir():
            shutil.rmtree(expect.parent)
        actual = NicoSeigaSaveDirectoryPath.create(illust_info, base_path).path
        self.assertEqual(expect, actual)

        expect.mkdir(exist_ok=True, parents=True)
        base_path = Path("./test/LinkSearch/NicoSeiga")
        expect = traverse(base_path)
        actual = NicoSeigaSaveDirectoryPath.create(illust_info, base_path).path
        self.assertEqual(expect, actual)

        if expect.is_dir():
            shutil.rmtree(expect.parent)

    def test_is_valid(self):
        illust_id = Illustid(12345678)
        illust_name = Illustname("作品名1")
        author_id = Authorid(1234567)
        author_name = Authorname("作者名1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        base_path = Path("./test/LinkSearch/NicoSeiga")
        actual = NicoSeigaSaveDirectoryPath.create(illust_info, base_path)
        self.assertEqual(True, actual._is_valid())

        actual = NicoSeigaSaveDirectoryPath(base_path)
        self.assertEqual(True, actual._is_valid())

        with self.assertRaises(TypeError):
            actual = NicoSeigaSaveDirectoryPath("invalid argument")
            self.assertEqual(True, actual._is_valid())


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
