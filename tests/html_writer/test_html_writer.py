import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from jinja2 import Template
from mock import MagicMock, patch

from media_gathering.db_controller_base import DBControllerBase
from media_gathering.html_writer.HtmlWriter import HtmlWriter
from media_gathering.util import Result


class TestHtmlWriter(unittest.TestCase):
    def test_init(self):
        op_type = "Fav"
        db_controller = MagicMock(spec=DBControllerBase)
        limit = 300
        column_num = 6
        pic_width = 256
        template = (Path(__file__).parent / "template/template.txt").read_text(encoding="utf-8")
        html_writer = HtmlWriter(op_type, db_controller, limit, column_num, pic_width)
        self.assertEqual(op_type, html_writer.op_type)
        self.assertEqual(db_controller, html_writer.db_controller)
        self.assertEqual(limit, html_writer.limit)
        self.assertEqual(column_num, html_writer.column_num)
        self.assertEqual(pic_width, html_writer.pic_width)
        self.assertEqual(template, html_writer.template)
        self.assertEqual("./pointer.png", HtmlWriter.POINTER_PATH)
        self.assertEqual("./html/FavMediaGathering.html", HtmlWriter.FAV_HTML_PATH)
        self.assertEqual("./html/RetweetMediaGathering.html", HtmlWriter.RETWEET_HTML_PATH)

        with self.assertRaises(TypeError):
            html_writer = HtmlWriter(-1, db_controller)
        with self.assertRaises(TypeError):
            html_writer = HtmlWriter(op_type, "invalid_db_controller")
        with self.assertRaises(TypeError):
            html_writer = HtmlWriter(op_type, db_controller, "invalid_limit")
        with self.assertRaises(TypeError):
            html_writer = HtmlWriter(op_type, db_controller, limit, "invalid_column_num")
        with self.assertRaises(TypeError):
            html_writer = HtmlWriter(op_type, db_controller, limit, column_num, "invalid_pic_width")
        with self.assertRaises(ValueError):
            html_writer = HtmlWriter("invalid_op_type", db_controller)
        with self.assertRaises(ValueError):
            html_writer = HtmlWriter(op_type, db_controller, -1)
        with self.assertRaises(ValueError):
            html_writer = HtmlWriter(op_type, db_controller, limit, -1)
        with self.assertRaises(ValueError):
            html_writer = HtmlWriter(op_type, db_controller, limit, column_num, -1)

    def test_write_result_html(self):
        with ExitStack() as stack:
            mock_write_text = stack.enter_context(patch("media_gathering.html_writer.HtmlWriter.Path.write_text"))

            record = {
                "url": "dummy_url",
                "url_thumbnail": "dummy_url_thumbnail",
                "tweet_url": "dummy_tweet_url"
            }
            db_controller = MagicMock(spec=DBControllerBase)
            db_controller.select.side_effect = lambda limit: [record]
            html_writer = HtmlWriter("Fav", db_controller)

            actual = html_writer.write_result_html()
            self.assertEqual(Result.success, actual)

            record_list = [record]
            source_list = [{
                "url": record["url"],
                "url_thumbnail": record["url_thumbnail"],
                "tweet_url": record["tweet_url"],
            } for record in record_list]
            column_num = 6
            pic_width = 256
            template_file = (Path(__file__).parent / "template/template.txt").read_text(encoding="utf-8")
            template: Template = Template(source=template_file)
            html = template.render(
                source_list=source_list,
                column_num=column_num,
                pic_width=pic_width,
                pointer_path=HtmlWriter.POINTER_PATH,
            )
            mock_write_text.assert_called_once_with(html, encoding="utf-8")
            mock_write_text.reset_mock()

            html_writer = HtmlWriter("RT", db_controller)
            actual = html_writer.write_result_html()
            self.assertEqual(Result.success, actual)
            mock_write_text.assert_called_once_with(html, encoding="utf-8")
            mock_write_text.reset_mock()

            html_writer = HtmlWriter("Fav", db_controller)
            html_writer.op_type = "Invalid_op_type"
            actual = html_writer.write_result_html()
            self.assertEqual(Result.failed, actual)
            mock_write_text.assert_not_called()
            mock_write_text.reset_mock()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
