# coding: utf-8
"""Workid のテスト
"""
import sys
import unittest

from PictureGathering.LinkSearch.Skeb.Workid import Workid


class TestWorkid(unittest.TestCase):
    def test_Workid(self):
        id_num = 123
        workid = Workid(id_num)

        with self.assertRaises(ValueError):
            workid = Workid(0)
        with self.assertRaises(ValueError):
            workid = Workid(-1)
        with self.assertRaises(TypeError):
            workid = Workid("invalid id")
        with self.assertRaises(TypeError):
            workid = Workid("")

    def test_id(self):
        id_num = 123
        workid = Workid(id_num)
        self.assertEqual(id_num, workid.id)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
