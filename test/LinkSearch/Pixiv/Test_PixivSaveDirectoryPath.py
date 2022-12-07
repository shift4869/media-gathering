# coding: utf-8
import re
import shutil
import sys
import unittest
from mock import MagicMock, patch, mock_open
from pathlib import Path

from PictureGathering.LinkSearch.Pixiv.Authorid import Authorid
from PictureGathering.LinkSearch.Pixiv.Authorname import Authorname
from PictureGathering.LinkSearch.Pixiv.PixivSaveDirectoryPath import PixivSaveDirectoryPath
from PictureGathering.LinkSearch.Pixiv.PixivWorkURL import PixivWorkURL
from PictureGathering.LinkSearch.Pixiv.Workid import Workid
from PictureGathering.LinkSearch.Pixiv.Worktitle import Worktitle


class TestPixivSaveDirectoryPath(unittest.TestCase):
    def mock_aapi(self, work_id, work_title, author_id, author_name, error_occur) -> MagicMock:
        aapi = MagicMock()
        illust = MagicMock()
        illust.user.name = author_name
        illust.user.id = author_id
        illust.title = work_title

        works = MagicMock()
        works.error = error_occur
        works.illust = illust

        aapi.illust_detail.side_effect = lambda work_id: works
        return aapi

    def test_PixivSaveDirectoryPath(self):
        s_work_id = Workid(123456789)
        s_work_title = Worktitle("作品名1")
        s_author_id = Authorid(1234567)
        s_author_name = Authorname("作者名1")

        def traverse(base_path) -> Path:
            work_id = s_work_id.id
            work_title = s_work_title.title
            author_id = s_author_id.id
            author_name = s_author_name.name

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

        work_id = s_work_id.id
        work_title = s_work_title.title
        author_id = s_author_id.id
        author_name = s_author_name.name
        m_aapi = self.mock_aapi(work_id, work_title, author_id, author_name, None)
        work_url = PixivWorkURL.create("https://www.pixiv.net/artworks/123456789")
        base_path = Path("./test/LinkSearch/Pixiv")
        expect = traverse(base_path)
        if expect.is_dir():
            shutil.rmtree(expect.parent)
        actual = PixivSaveDirectoryPath.create(m_aapi, work_url, base_path).path
        self.assertEqual(expect, actual)

        expect.mkdir(exist_ok=True, parents=True)
        base_path = Path("./test/LinkSearch/Pixiv")
        expect = traverse(base_path)
        actual = PixivSaveDirectoryPath.create(m_aapi, work_url, base_path).path
        self.assertEqual(expect, actual)

        m_aapi = self.mock_aapi(work_id, work_title, author_id, author_name, True)
        with self.assertRaises(ValueError):
            actual = PixivSaveDirectoryPath.create(m_aapi, work_url, base_path).path

        if expect.is_dir():
            shutil.rmtree(expect.parent)

    def test_is_valid(self):
        base_path = Path("./test/LinkSearch/Pixiv")

        actual = PixivSaveDirectoryPath(base_path)
        self.assertEqual(True, actual._is_valid())

        with self.assertRaises(TypeError):
            actual = PixivSaveDirectoryPath("invalid argument")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
