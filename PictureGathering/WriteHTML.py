# coding: utf-8
from PictureGathering import DBControlar

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
      <img border="0" src="{url_thumbnail}" alt="{url}" width="{pic_width}px">
      </a>
      <a href="{tweet_url}" target="_blank">
      <img src="{pointer_path}" alt="pointer"
       style="opacity: 0.5; position: absolute; right: 10px; bottom: 10px;"  />
      </a>
     </div>
    </th>
'''
POINTER_PATH = './pointer.png'
FAV_HTML_PATH = './html/FavPictureGathering.html'
RETWEET_HTML_PATH = './html/RetweetPictureGathering.html'
db_cont = DBControlar.DBControlar()


def MakeTHTag(url, url_thumbnail, tweet_url):
    pic_width = 256
    return th_template.format(pic_width=pic_width,
                              url=url,
                              url_thumbnail=url_thumbnail,
                              tweet_url=tweet_url,
                              pointer_path=POINTER_PATH)


def WriteResultHTML(op_type, del_url_list):
    if op_type == "Fav":
        WriteFavHTML(del_url_list)
    elif op_type == "RT":
        WriteRetweetHTML(del_url_list)


def WriteFavHTML(del_url_list):
    db = db_cont.DBFavSelect()
    res = ''

    COLUMN_NUM = 5
    cnt = 0

    for row in db:
        if cnt == 0:
            res += "<tr>\n"
        res += MakeTHTag(url=row[3], url_thumbnail=row[4], tweet_url=row[6])
        if cnt == COLUMN_NUM - 1:
            res += "</tr>\n"
        cnt = (cnt + 1) % COLUMN_NUM
    if cnt != 0:
        for k in range((COLUMN_NUM) - (cnt)):
            res += "<th></th>\n"
        res += "</tr>\n"

    html = template.format(table_content=res)

    with open(FAV_HTML_PATH, "w") as fout:
        fout.write(html)


def WriteRetweetHTML(del_url_list):
    db = db_cont.DBRetweetSelect()
    res = ''

    COLUMN_NUM = 5
    cnt = 0

    for row in db:
        if cnt == 0:
            res += "<tr>\n"
        res += MakeTHTag(url=row[3], url_thumbnail=row[4], tweet_url=row[6])
        if cnt == COLUMN_NUM - 1:
            res += "</tr>\n"
        cnt = (cnt + 1) % COLUMN_NUM
    if cnt != 0:
        for k in range((COLUMN_NUM) - (cnt)):
            res += "<th></th>\n"
        res += "</tr>\n"

    html = template.format(table_content=res)

    with open(RETWEET_HTML_PATH, "w") as fout:
        fout.write(html)


if __name__ == "__main__":
    del_url_list = [
        # "http://pbs.twimg.com/media/example_xxxxxxxxxxx.png:orig",
    ]
    WriteResultHTML("Fav", del_url_list)
