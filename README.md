# media-gathering

![Coverage reports](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/shift4869/ad61760f15c4a67a5c421cf479e3c7e7/raw/01_MediaGathering.json)

## 概要
ツイッターでfav/RTしたメディア（=画像と動画の総称）含みツイートからメディアを収集し、ローカルに保存するツイッタークローラ。  
主に自分のツイッターアカウントでfav/RTしたツイートを対象とする。


## 特徴（できること）
- fav/RTしたメディア含みツイートからメディアを収集し、ローカルに保存する。  
    - メディア保持数を設定し、古いものから削除していくディレクトリを設定可能。（一定数保持）  
    - メディア保持数を制限せずどんどんと保存していくディレクトリを設定可能。（制限なし、ディスク容量に注意）  
- 収集対象は以下の通り。  
    - fav/RTしたメディア含みツイートに含まれるメディア。  
    - fav/RTしたツイートのRT先、引用RT先がメディア含みツイートだった場合も収集する。  
    - 本文内に特定の画像投稿サイトへのリンクがあった場合、リンク先をたどり一枚絵/漫画形式の作品を全て収集する。（任意）  
        - 対応しているアドレスは次の通り
            ```
            "pixiv pic/manga": "https://www.pixiv.net/artworks/xxxxxxxx",
            "pixiv novel": "https://www.pixiv.net/novel/show.php?id=xxxxxxxx",
            "nijie": "http://nijie.info/view_popup.php?id=xxxxxx",
            "seiga": "https://seiga.nicovideo.jp/seiga/imxxxxxxx",
            ```
- 収集したメディアの情報をDBに蓄積する。  
    - 元ツイートURLなど。  
- 収集したメディアを一覧で見ることができるhtmlを出力する。  
    - 各メディアのオリジナル(:origや高ビットレート動画)とその元ツイートへのリンクを付与する。  
- 処理完了時に各種他媒体に通知ツイートを送る。（任意）  
    - 以下の媒体へ通知の連携が可能。  
        - Discord, Line, Slack,   

※定期的な実行を前提としていますが機能としては同梱していないので「タスクのスケジュール」などOS標準の機能で定期実行してください。  
※windows 11でのみ動作確認をしております。  


## 前提として必要なもの
- Pythonの実行環境(3.11以上)
- twitterのセッション情報
    - ブラウザでログイン済のアカウントについて、以下の値をクッキーから取得
        - ct0 (クッキー中)
        - auth_token (クッキー中)
        - target_screen_name(収集対象の@なしscreen_name)
        - target_id (クッキー中の"twid"の値について、"u%3D{target_id}"で表される数値列)
    - ブラウザ上でのクッキーの確認方法
        - 各ブラウザによって異なるが、概ね `F12を押す→ページ更新→アプリケーションタブ→クッキー` で確認可能
    - 詳しくは「twitter クッキー ct0 auth_token」等で検索


## 使い方
1. このリポジトリをDL
    - 右上の「Clone or download」->「Download ZIP」からDLして解凍
1. config/config_sample.json の中身を自分用に編集してconfig/config.jsonにリネーム
    - twitterのセッション情報を設定する（必須）
    - ローカルの保存先パスを設定する（必須）
    - その他`dummy`や`tests`とついている箇所を自分の環境に合わせて修正する
1. main.pyを実行する（以下は一例）
    - ※手動で実行するならパスが通っている環境で以下でOK
    ```
    python ./src/main.py --type="Fav"
    ```
    - または、以下を記述した.vbsファイルを用意する  
    ```
    Set ws=CreateObject("Wscript.Shell")
    ws.CurrentDirectory = "{解凍したmedia-gatheringへのパス}\media-gathering"
    ws.run "cmd /c """"{python実行ファイルまでのパス}\python.exe"" {解凍したmedia-gatheringへのパス}\media-gathering\src\main.py --type=""Fav""""", vbhide
    ```
    - `--type`を`Fav`でなく`RT`に変更すれば対象がRetweetとなる
    - 作成した.vbsを「タスクのスケジュール」などで実行する
1. 出力されたhtml/配下のhtmlを確認する
1. ローカルの保存先パスにメディアが保存されたことを確認する


## License/Author
[MIT License](https://github.com/shift4869/media-gathering/blob/master/LICENSE)  
Copyright (c) 2018 - 2024 [shift](https://twitter.com/_shift4869)

使用した外部ライブラリのライセンスについては[こちら](https://github.com/shift4869/media-gathering/blob/master/EXTERNAL_LIBRARY.md)  を参照

