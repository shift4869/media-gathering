# coding: utf-8

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
POINTER_PATH = "./pointer.png"
FAV_HTML_PATH = "./html/FavPictureGathering.html"
RETWEET_HTML_PATH = "./html/RetweetPictureGathering.html"
COLUMN_NUM = 6


def MakeTHTag(url, url_thumbnail, tweet_url):
    pic_width = 256
    return th_template.format(pic_width=pic_width,
                              url=url,
                              url_thumbnail=url_thumbnail,
                              tweet_url=tweet_url,
                              pointer_path=POINTER_PATH)


def WriteResultHTML(op_type, db_controller, limit=300):
    save_path = ""
    db = db_controller.Select(limit)
    if op_type == "Fav":
        save_path = FAV_HTML_PATH
    elif op_type == "RT":
        save_path = RETWEET_HTML_PATH
    else:
        return -1

    res = ""
    cnt = 0

    for row in db:
        if cnt == 0:
            res += "<tr>\n"
        res += MakeTHTag(url=row["url"], url_thumbnail=row["url_thumbnail"], tweet_url=row["tweet_url"])
        if cnt == COLUMN_NUM - 1:
            res += "</tr>\n"
        cnt = (cnt + 1) % COLUMN_NUM
    if cnt != 0:
        for k in range((COLUMN_NUM) - (cnt)):
            res += "<th></th>\n"
        res += "</tr>\n"

    html = template.format(table_content=res)

    with open(save_path, "w") as fout:
        fout.write(html)
    
    return 0


if __name__ == "__main__":
    from PictureGathering import FavDBController
    db_controller = FavDBController.FavDBController()
    WriteResultHTML("Fav", db_controller)
