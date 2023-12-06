"""NijieSaveDirectoryPath のテスト
"""
import re
import shutil
import sys
import unittest
from pathlib import Path

from media_gathering.link_search.nijie.Authorid import Authorid
from media_gathering.link_search.nijie.Authorname import Authorname
from media_gathering.link_search.nijie.NijiePageInfo import NijiePageInfo
from media_gathering.link_search.nijie.NijieSaveDirectoryPath import NijieSaveDirectoryPath
from media_gathering.link_search.nijie.NijieSourceList import NijieSourceList
from media_gathering.link_search.nijie.NijieURL import NijieURL
from media_gathering.link_search.nijie.Workid import Workid
from media_gathering.link_search.nijie.Worktitle import Worktitle


class TestNijieSaveDirectoryPath(unittest.TestCase):
    def test_is_valid(self):
        author_name = Authorname("作者名1")
        author_id = Authorid(1234567)
        work_title = Worktitle("作品名1")
        work_id = Workid(12345678)
        nijie_url = NijieURL.create("https://nijie.info/view.php?id=12345678")
        source_list = NijieSourceList.create([nijie_url.original_url])
        page_info = NijiePageInfo(source_list, author_name, author_id, work_title)

        base_path = Path("./tests/link_search/nijie")
        actual = NijieSaveDirectoryPath.create(nijie_url, page_info, base_path)
        self.assertEqual(True, actual._is_valid())

        actual = NijieSaveDirectoryPath(base_path)
        self.assertEqual(base_path, actual.path)
        self.assertEqual(True, actual._is_valid())

        with self.assertRaises(TypeError):
            actual = NijieSaveDirectoryPath("invalid argument")

    def test_create(self):
        author_name = Authorname("作者名1")
        author_id = Authorid(1234567)
        work_title = Worktitle("作品名1")
        work_id = Workid(12345678)
        nijie_url = NijieURL.create("https://nijie.info/view.php?id=12345678")
        source_list = NijieSourceList.create([nijie_url.original_url])
        page_info = NijiePageInfo(source_list, author_name, author_id, work_title)

        def traverse(nijie_url: NijieURL, page_info: NijiePageInfo, base_path: Path) -> Path:
            author_name = page_info.author_name.name
            author_id = page_info.author_id.id
            work_title = page_info.work_title.title
            work_id = nijie_url.work_id.id

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
                        sd_path = f"./{dir_name}/{work_title}({work_id})/"
                        break

            if sd_path == "":
                sd_path = f"./{author_name}({author_id})/{work_title}({work_id})/"

            return save_path / sd_path

        base_path = Path("./tests/link_search/nijie")
        expect = traverse(nijie_url, page_info, base_path)
        if expect.is_dir():
            shutil.rmtree(expect.parent)
        actual = NijieSaveDirectoryPath.create(nijie_url, page_info, base_path).path
        self.assertEqual(expect, actual)

        expect.mkdir(exist_ok=True, parents=True)
        base_path = Path("./tests/link_search/nijie")
        expect = traverse(nijie_url, page_info, base_path)
        actual = NijieSaveDirectoryPath.create(nijie_url, page_info, base_path).path
        self.assertEqual(expect, actual)

        if expect.is_dir():
            shutil.rmtree(expect.parent)

        with self.assertRaises(TypeError):
            actual = NijieSaveDirectoryPath.create("invalid argument", page_info, base_path).path

        with self.assertRaises(TypeError):
            actual = NijieSaveDirectoryPath.create(nijie_url, "invalid argument", base_path).path

        with self.assertRaises(TypeError):
            actual = NijieSaveDirectoryPath.create(nijie_url, page_info, "invalid argument").path


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
