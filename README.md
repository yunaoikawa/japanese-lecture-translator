# japanese-lecture-translator（一次翻訳完全自動化）

ぜひ自由に共同で編集しましょう！
コード綺麗にする、新しい機能を追加する、など、大歓迎です！

特に追加して欲しい機能は以下”これからできるようにしたいこと”に書いてあります（自由に追加してください）。

作業中は🚧（作業中）、完了したら✅（チェック）　をつけてください。

Collaborator権限を付与されていない方はslackでOIKAWA Yunaにgithubのemailを教えてください。

質問やコメントは[Issues](https://github.com/yunaoikawa/japanese-lecture-translator/issues)にお願いします！


- 必要なもの
  - 日本語版linkかDocs内directory
  - OpenAI API key
  - google API
- 今できること
  - ✅ Script翻訳 in txt
  - ✅ Notebook翻訳
  - ✅ 実行時にDocsにある最新promptを随時反映
  - ✅ （chunk毎に翻訳しているので、質が落ちる心配なし）
- これからできるようにしたいこと
  1.  regexでリンクからgoogle slide, notebook, scriptのIDを取得できるようにする（今は`https://colab.research.google.com/drive/1wPAkQ3DgqpJzQ6hCLAAA_r4Aa8?usp=drive_link`　みたいなのから1wPAkQ3DgqpJzQ6hCL60yuvbAAA_r4Aa8　の部分を手動で取ってきてハードコーディングしているので）
  2.  APIに送る前に、和英対応表 （https://docs.google.com/spreadsheets/d/1Jq87j4FvlDyt4wHHyGGCKmLVkWAxeJxSaiW0KulqKO8/edit?gid=0#gid=0） を使ってregexで直接翻訳してしまう。（”データ”vs”データセット”とかあるので、先に文字数順でソートしてからが良さそう）
  3.  Google docをtxtに直さず直接翻訳（私の環境だと何故か日本語を認識しなくなってしまうので....)
  4.  全ファイルの自動アップロード
  5.  和英対応表を随時、自動でpromptに反映
  6.  スケジュール自動作成
  7.  画像自動翻訳
  8.  config.pyを作ることで各種API keyなどをmyclasses.pyから切り離す
  9.  練習問題は別のプログラム・プロンプトを作る
