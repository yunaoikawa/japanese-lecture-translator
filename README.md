# japanese-lecture-translator（一次翻訳完全自動化）

ぜひ自由に共同で編集しましょう！
コード綺麗にする、新しい機能を追加する、など、大歓迎です！
特に追加して欲しい機能は以下”これからできるようにしたいこと”に書いてあります

- 一次翻訳完全自動化
  - 必要なもの
    - 日本語版linkかDocs内directory
    - OpenAI API key
    - google API
  - 今できること
    - Script翻訳 in txt
    - Notebook翻訳
    - 実行時にDocsにある最新promptを随時反映
    - （chunk毎に翻訳しているので、質が落ちる心配なし）
  - これからできるようにしたいこと
    - regexでリンクからdocument ID取得
    - regexで①、②などを直す
    - Google docをtxtに直さず直接翻訳（私の環境だと何故か日本語を認識しなくなってしまうので....)
    - Slide翻訳
    - 全ファイルの自動アップロード
    - 和英対応表を随時、自動でpromptに反映
    - スケジュール自動作成
    - 画像自動翻訳