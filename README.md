# PictureGathering


## 概要
ツイッターでfav/RTしたメディア（=画像と動画の総称）含みツイートからメディアを収集し、
ローカルに保存するツイッタークローラ。  
主に自分のツイッターアカウントでfav/RTしたツイートを対象とする。


## 特徴（できること）
- fav/RTしたメディア含みツイートからメディアを収集し、ローカルに保存する。  
    - メディア保持数を設定し、古いものから削除していくディレクトリを設定可能（一定数保持）  
    - メディア保持数を制限せずどんどんと保存していくディレクトリを設定可能（制限なし、ディスク容量に注意）  
- 収集したメディアの情報をDBに蓄積する。  
    - 元ツイートURLなど  
- 収集したメディアを一覧で見ることができるhtmlを出力する。  
    - 各メディアのオリジナル(:origや高ビットレート動画)とその元ツイートへのリンクを付与する。  
- image magickによる縮小加工が可能（任意）  
- 処理完了時に通知ツイートを送る（任意）  
    - 前日以前の通知ツイートは自動的に削除されます。  

※定期的な実行を前提としてますが機能としては同梱していないので「タスクのスケジュール」などOS標準の機能で定期実行してください。  
※windows 10でのみ動作確認をしております。  


## 前提として必要なもの
- Pythonの実行環境
- twitterアカウントのAPIトークン
    - TwitterAPIを使用するためのAPIトークン。以下の4つのキーが必要
        - コンシューマーキー (Consumer Key)
        - コンシューマーシークレット (Consumer Secret)
        - アクセストークン (Access Token)
        - アクセストークンシークレット (Access Token Secret)
    - もちろん自分のtwitterアカウントも必要
        - 加えて上記4つのキーを取得するためにDeveloper登録が必要なのでそのための電話番号の登録が必要
    - 詳しくは「twitter API トークン」で検索
- 画像加工のためのimage magick
    - ローカル保存時にimage magickで縮小処理をかけられます。
        - 具体的には以下のコマンドを実行して60%の画質に変換しています。
        - "{img_magick_path} -quality 60 {save_file_fullpath} {save_file_fullpath}"
    - 利用する場合はmagickコマンドが通るようにする必要があります。
    - 詳しくは「image magick」で検索


## 使い方
1. このリポジトリをDL
    - 右上の「Clone or download」->「Download ZIP」からDLして解凍
1. config/config_example.iniの中身を自分用に編集してconfig/config.iniにリネーム。
    - ローカルの保存先パスを設定する。（必須）
    - 自分のtwitterアカウントのAPIトークンを設定する（必須）。  
    - image magickをインストールしておく（任意）。  
1. PictureGathering.pyを実行する。
1. 出力されたhtmlを確認する。
1. ローカルの保存先パスにメディアが保存されたことを確認する。


## License/Author
[MIT License](https://github.com/shift4869/PictureGathering/blob/master/LICENSE)  
Copyright (c) 2018 [shift](https://twitter.com/_shift4869)

