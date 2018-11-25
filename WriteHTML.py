# coding: utf-8
import DBControl as DBControl

template = '''<!DOCTYPE html>
<html>
<head>
<title>PictureGathering</title>
</head>
<body>
  <table>
   {table_content}
  </table>
</body>
</html>
'''
th_template = '''<th>
     <div style="position: relative; width: {pic_width}px;" >
      <a href="{url}" target="_blank">
      <img border="0" src="{url}" alt="{url}" width="{pic_width}px">
      </a>
      <a href="{tweet_url}" target="_blank">
      <img src="{pointer_path}" alt="pointer"
       style="opacity: 0.5; position: absolute; right: 10px; bottom: 10px;"  />
      </a>
     </div>
    </th>
'''
POINTER_PATH = './pointer.png'
db_cont = DBControl.DBControlar()


def MakeTHTag(url, tweet_url):
    pic_width = 256
    return th_template.format(pic_width=pic_width,
                              url=url,
                              tweet_url=tweet_url,
                              pointer_path=POINTER_PATH)


def WriteFavHTML(del_url_list):
    db = db_cont.DBFavSelect()
    res = ''

    COLUMN_NUM = 5
    cnt = 0

    for row in reversed(db):
        if cnt == 0:
            res += "<tr>\n"
        res += MakeTHTag(url=row[2], tweet_url=row[5])
        if cnt == COLUMN_NUM - 1:
            res += "</tr>\n"
        cnt = (cnt + 1) % COLUMN_NUM
    if cnt != 0:
        for k in range((COLUMN_NUM) - (cnt)):
            res += "<th></th>\n"
        res += "</tr>\n"

    html = template.format(table_content=res)

    with open("FavPictureGathering.html", "w") as fout:
        fout.write(html)


def WriteRetweetHTML(del_url_list):
    db = db_cont.DBRetweetSelect()
    res = ''

    COLUMN_NUM = 5
    cnt = 0

    for row in reversed(db):
        if cnt == 0:
            res += "<tr>\n"
        res += MakeTHTag(url=row[3], tweet_url=row[6])
        if cnt == COLUMN_NUM - 1:
            res += "</tr>\n"
        cnt = (cnt + 1) % COLUMN_NUM
    if cnt != 0:
        for k in range((COLUMN_NUM) - (cnt)):
            res += "<th></th>\n"
        res += "</tr>\n"

    html = template.format(table_content=res)

    with open("RetweetPictureGathering.html", "w") as fout:
        fout.write(html)


if __name__ == "__main__":
    del_url_list = [
        # "http://pbs.twimg.com/media/example_xxxxxxxxxxx.png:orig",
    ]
    WriteHTML(del_url_list)
