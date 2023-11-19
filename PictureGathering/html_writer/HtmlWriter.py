
from pathlib import Path
from typing import Literal

from jinja2 import Template

from PictureGathering.DBControllerBase import DBControllerBase
from PictureGathering.Util import Result


class HtmlWriter():
    POINTER_PATH = "./pointer.png"
    FAV_HTML_PATH = "./html/FavPictureGathering.html"
    RETWEET_HTML_PATH = "./html/RetweetPictureGathering.html"

    def __init__(self, op_type: Literal["Fav", "RT"], db_controller: DBControllerBase,
                 limit=300, column_num: int = 6, pic_width: int = 256) -> None:
        if not isinstance(op_type, str):
            raise ValueError('op_type must be type str ["Fav", "RT"].')
        if op_type not in ["Fav", "RT"]:
            raise ValueError('op_type must be ["Fav", "RT"].')
        if not isinstance(db_controller, DBControllerBase):
            raise ValueError('db_controller must be DBControllerBase.')
        self.op_type = op_type
        self.db_controller = db_controller
        self.limit = limit
        self.column_num = column_num
        self.pic_width = pic_width
        self.template = (Path(__file__).parent / "template/template.txt").read_text(encoding="utf-8")

    def write_result_html(self) -> Result:
        save_path: Path = None
        record_list: list[dict] = self.db_controller.select(self.limit)
        if self.op_type == "Fav":
            save_path = Path(HtmlWriter.FAV_HTML_PATH)
        elif self.op_type == "RT":
            save_path = Path(HtmlWriter.RETWEET_HTML_PATH)
        else:
            return Result.failed

        source_list = [{
            "url": record["url"],
            "url_thumbnail": record["url_thumbnail"],
            "tweet_url": record["tweet_url"],
        } for record in record_list]

        template: Template = Template(source=self.template)
        html = template.render(
            source_list=source_list,
            column_num=self.column_num,
            pic_width=self.pic_width,
            pointer_path=HtmlWriter.POINTER_PATH,
        )

        save_path.write_text(html, encoding="utf-8")
        return Result.success


if __name__ == "__main__":
    from PictureGathering import FavDBController
    SAMPLE_DB_PATH = Path(__file__).parent / "sample/PG_DB.db"
    db_controller = FavDBController.FavDBController(db_fullpath=SAMPLE_DB_PATH)
    html_writer = HtmlWriter("Fav", db_controller)
    html_writer.write_result_html()
