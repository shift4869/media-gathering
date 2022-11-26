# coding: utf-8
"""NicoSeigaSession のテスト

NicoSeigaSessionを表すクラスをテストする
"""
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession import NicoSeigaSession


class TestNicoSeigaSession(unittest.TestCase):
    def _get_session(self):
        with ExitStack() as stack:
            mock_session = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession.requests.session"))
            mock_is_valid = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession.NicoSeigaSession._is_valid"))
            mock_session.side_effect = lambda: MagicMock()
            username = Username("name")
            password = Password("pass")
            return NicoSeigaSession(username, password)

        pass

    def test_NicoSeigaSession(self):
        actual = self._get_session()
        pass

    def test_login(self):
        pass

    def test_is_valid(self):
        pass

    def test_get_author_id(self):
        pass

    def test_get_author_name(self):
        pass

    def test_get_illust_title(self):
        pass

    def test_get_source_url(self):
        pass

    def test_get_illust_binary(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
