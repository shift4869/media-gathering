import re
import shutil
import sys
import unittest
from pathlib import Path

from mock import MagicMock, mock_open, patch

from media_gathering.link_search.pixiv_novel.Authorid import Authorid
from media_gathering.link_search.pixiv_novel.Authorname import Authorname
from media_gathering.link_search.pixiv_novel.Novelid import Novelid
from media_gathering.link_search.pixiv_novel.Noveltitle import Noveltitle
from media_gathering.link_search.pixiv_novel.PixivNovelSaveDirectoryPath import PixivNovelSaveDirectoryPath
from media_gathering.link_search.pixiv_novel.PixivNovelURL import PixivNovelURL


class TestPixivNovelSaveDirectoryPath(unittest.TestCase):
    def mock_aapi(self, novel_id, novel_title, author_id, author_name, error_occur) -> MagicMock:
        aapi = MagicMock()
        novel = MagicMock()
        novel.user.name = author_name
        novel.user.id = author_id
        novel.title = novel_title

        works = MagicMock()
        works.error = error_occur
        works.novel = novel

        aapi.novel_detail.side_effect = lambda novel_id: works
        return aapi

    def test_PixivNovelSaveDirectoryPath(self):
        s_novel_id = Novelid(123456789)
        s_novel_title = Noveltitle("作品名1")
        s_author_id = Authorid(1234567)
        s_author_name = Authorname("作者名1")

        def traverse(base_path) -> Path:
            novel_id = s_novel_id.id
            novel_title = s_novel_title.title
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
                        sd_path = f"./{dir_name}/{novel_title}({novel_id})/"
                        break

            if sd_path == "":
                sd_path = f"./{author_name}({author_id})/{novel_title}({novel_id})/"

            return save_path / sd_path

        novel_id = s_novel_id.id
        novel_title = s_novel_title.title
        author_id = s_author_id.id
        author_name = s_author_name.name
        m_aapi = self.mock_aapi(novel_id, novel_title, author_id, author_name, None)
        work_url = PixivNovelURL.create(f"https://www.pixiv.net/novel/show.php?id={novel_id}")
        base_path = Path("./tests/link_search/pixiv_novel")
        expect = traverse(base_path)
        if expect.is_dir():
            shutil.rmtree(expect.parent)
        actual = PixivNovelSaveDirectoryPath.create(m_aapi, work_url, base_path).path
        self.assertEqual(expect, actual)

        expect.mkdir(exist_ok=True, parents=True)
        base_path = Path("./tests/link_search/pixiv_novel")
        expect = traverse(base_path)
        actual = PixivNovelSaveDirectoryPath.create(m_aapi, work_url, base_path).path
        self.assertEqual(expect, actual)

        m_aapi = self.mock_aapi(novel_id, novel_title, author_id, author_name, True)
        with self.assertRaises(ValueError):
            actual = PixivNovelSaveDirectoryPath.create(m_aapi, work_url, base_path).path

        if expect.is_dir():
            shutil.rmtree(expect.parent)

    def test_is_valid(self):
        base_path = Path("./tests/link_search/pixiv_novel")

        actual = PixivNovelSaveDirectoryPath(base_path)
        self.assertEqual(True, actual._is_valid())

        with self.assertRaises(TypeError):
            actual = PixivNovelSaveDirectoryPath("invalid argument")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
