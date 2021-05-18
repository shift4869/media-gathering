※以下内容は多分に要約を含むため、参考程度に  
※利用されている外部ライブラリの作成者- 管理者様へ：  
　ライセンスの解釈について問題がある場合はお手数ですがご連絡をお願いいたします。  

---

## 主なライセンス形態

- 2条項BSD
	- 以下は許可される
		- Commercial use（商用利用）
		- Modification（改変）
		- Distribution（配布）
		- Private use （個人利用）
	- 以下は禁止される
		- Liability（賠償責任要求）
		- Warranty （保証要求）
	- 以下の記述が必須
		- License and copyright notice（ライセンスと著作権表示）
- BSD、3条項BSD、修正BSD
	- 2条項BSDの事項に加え、以下を追加
		- 書面による特別の許可なしに、組織-著作権者の名前と貢献者の名前を使わない。

- MIT License
	- （2条項BSDとほぼ同じ）
	- 以下は許可される
		- Commercial use（商用利用）
		- Modification（改変）
		- Distribution（配布）
		- Private use （個人利用）
	- 以下は禁止される
		- Liability（賠償責任要求）
		- Warranty （保証要求）
	- 以下の記述が必須
		- License and copyright notice（ライセンスと著作権表示）

- Apache License 2.0
	- 以下は許可される
		- Commercial use（商用利用）
		- Modification（改変）
		- Distribution（配布）
		- Patent use（特許利用）
		- Private use （個人利用）
	- 以下は禁止される
		- Trademark use（商標の使用）
		- Liability（賠償責任要求）
		- Warranty （保証要求）
	- 以下の記述が必須
		- License and copyright notice（ライセンスと著作権表示）
		- State changes （改変した場合はその旨を表示する）

- ライセンス無し（The Unlicense）
	- 以下は許可される
		- Private use （個人利用）
		- Commercial use（商用利用）
		- Modification（改変）
		- Distribution（配布）
	- 以下は禁止される
		- Liability（賠償責任要求）
		- Warranty （保証要求）

- ISC License
	- 2条項BSDとMITとほぼ同じ
	- 古い言語には対応しないという明記のみ追加

- PSF License
	- Pythonプロジェクトの配布用ライセンス。
	- GPLとは異なり、PSFはコピーレフトのライセンスではない。
	- そのため、コードをオープンソースにせずに元のソースコードの変更をすることが許されている。

- HPND License
	- HPND=Historical Permission Notice and Disclaimer（歴史的な許可告知と断り書き）
	- 以下は許可される
		- 使用、コピー、修正、頒布
	- 以下は禁止される
		- 書面による事前の許可を得ずに著作権所有者の名前を広告や宣伝に使用すること
		- 保証要求、賠償責任要求
	- 以下の記述が必須
		- 著作権表示をすべてのコピーに含めること

---

## 外部ライブラリのライセンス表記

@waylan / beautifulsoup beautifulsoup4 4.9.3  
スクレイピングに使用。  
Beautiful Soup is made available under the MIT license:  
MIT License  

@pyca pyca / cryptography 3.2.1  
CIのためのファイル暗号化-復号に使用。  
LICENSE（※訳）  
このソフトウェアは、以下のLICENSE.APACHE または LICENSE.BSDの*いずれか*のライセンスの条件の下で利用可能です。  
暗号技術への貢献はこれらのライセンスの*両方の*条件のもとで使用されます。

OSのランダムエンジンで使われているコードはCPythonから派生したもので、  
ライセンスはPSFライセンス契約の条件の下で利用されます。

- LICENSE.APACHE
	- Apache License 2.0
- LICENSE.BSD
	- 修正BSDライセンス
- LICENSE.PSF
	- PSF License

@carpedm20 / emoji 1.2.0  
パスに使えない絵文字を検出するために使用。  
BSD

@spulec spulec / freezegun 1.0.0  
単体テストの時刻を固定するために使用。  
Apache License 2.0

@googleapis googleapis / google-api-python-client 1.12.8  
GoogleDriveにアップロードするために使用。  
Apache License 2.0

@calvinchengx calvinchengx / python-mock mock 4.0.2  
単体テストのモック機能利用のために使用。  
BSD 2-Clause "Simplified" License  
=2条項BSD

@python-pillow / Pillow Pillow 8.1.2  
外部リンク先のgif保存時に使用。
HPND License

@upbit upbit / pixivpy 3.5.10  
PixivAPIを利用するために使用。  
The Unlicense

@protocolbuffers protocolbuffers / protobuf 3.14.0  
GoogleAPIの前提。  
Copyright 2008 Google Inc.  
BSD（※要約）

@psf psf / requests 2.24.0  
各種外部通信に使用。  
Apache License 2.0

@requests requests / requests-oauthlib 1.3.0  
oauth認証処理に使用。  
ISC License

@satoshi03 satoshi03 / slack-python-webhook slackweb 1.0.5  
SlackAPIを利用するために使用。  
ライセンス記載なし（The UnlicenseとPSFライセンス？）

@sqlalchemy sqlalchemy / sqlalchemy 1.3.20  
DB操作を楽にするために使用。  
MIT License

※今後使用した外部ライブラリが増えた場合は追記する

---

## 本ライブラリのライセンス表記について

利用させていただいている外部ライブラリについて、主にApache License 2.0とMIT License - BSD Licenseに集約できる。  
特許利用や商用利用は見越していない、かつApache License 2.0ライセンスのライブラリの改変も行っていないため、  
本ライブラリはMIT Licenseとする。  
（意味合い的にはISC Licenseだが知名度との兼ね合いでMITを採用）

### MIT License

許可・禁止事項は前述しているが、文章で要約しておく。  
本ライブラリは個人利用、商用利用、改変、再配布いずれも可とする。  
ただし、以下の著作権表示、ライセンス表示が必要となる。

- 著作権表示
    - 「Copyright (c) 2018 [shift](https://twitter.com/_shift4869) (https://twitter.com/_shift4869)」と記載する。
        - （同じ意味ならばどんな表記でも良い。）
- ライセンス表示
    - [MIT License](https://github.com/shift4869/PictureGathering/blob/master/LICENSE)  であるということを記載する。
        - MIT License全文 or MIT License全文へのリンクを記載

また、本ライブラリを利用したことで生じた不利益については一切保障しない。
（以下MIT License和訳一部抜粋）

    （本ライブラリは）何らの保証もなく提供されます。
    ここでいう保証とは、商品性、特定の目的への適合性、および権利非侵害についての保証も含みますが、それに限定されるものではありません。 
    作者または著作権者は、契約行為、不法行為、またはそれ以外であろうと、ソフトウェアに起因または関連し、あるいはソフトウェアの使用またはその他の扱いによって生じる一切の請求、損害、その他の義務について何らの責任も負わないものとします。 

  

以上（情報更新され次第追記）

2021/05/18 [shift](https://twitter.com/_shift4869)
