# japanese-lecture-translator（一次翻訳完全自動化）

ぜひ自由に共同で編集しましょう！
コード綺麗にする、新しい機能を追加する、など、大歓迎です！
特に追加して欲しい機能は以下”これからできるようにしたいこと”に書いてあります
作業中は🚧（作業中）、✅（チェック）　をつけてください。

- 一次翻訳完全自動化
  - 必要なもの
    - 日本語版linkかDocs内directory
    - OpenAI API key
    - google API
  - 今できること
    ✅ Script翻訳 in txt
    ✅ Notebook翻訳
    ✅ 実行時にDocsにある最新promptを随時反映
    ✅ （chunk毎に翻訳しているので、質が落ちる心配なし）
  - これからできるようにしたいこと
    - regexでリンクからgoogle slide, notebook, scriptのIDを取得できるようにする（今はhttps://colab.research.google.com/drive/1wPAkQ3DgqpJzQ6hCL60yuvbZby_r4Aa8?usp=drive_link　みたいなのから1wPAkQ3DgqpJzQ6hCL60yuvbZby_r4Aa8　の部分を手動で取ってきてハードコーディングしているので）
    - APIに送る前に、和英対応表（https://docs.google.com/spreadsheets/d/1Jq87j4FvlDyt4wHHyGGCKmLVkWAxeJxSaiW0KulqKO8/edit?gid=0#gid=0）を使ってregexで直接翻訳してしまう
    - Google docをtxtに直さず直接翻訳（私の環境だと何故か日本語を認識しなくなってしまうので....)
    - 全ファイルの自動アップロード
    - 和英対応表を随時、自動でpromptに反映
    - スケジュール自動作成
    - 画像自動翻訳
