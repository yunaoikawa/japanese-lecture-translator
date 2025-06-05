# ファイル構成

### `myclasses.py`
- 補助的なクラスやユーティリティ関数を定義。
 セットアップ方法
  1.Run  `pip install -r requirements.txt`
  2.Rename `.env.example` to `.env` and update the API keys to your own. 
  3.Place Google Service Account JSON key file as specified in .env file (e.g. Inside project root).

### `remove_overlap.py`
- 例えばLevel0-Level1間で全く同じ部分をダブルで翻訳しなくていいように提案された機能
- 未完成
- 実装の優先順位は低い

### `translate_image.py`
- 画像内の日本語を英語に翻訳するのが目標。
- OpenAIのAPIでは難しそうだったので、一旦キーワードをPython上のduck-duck-goで検索し、結果をダウンロードするという機能に落ち着いた。
- 今後主に渡部さんに大幅に変更して行ってほしい。

### `translate_ipynb.py`
- Jupyter Notebook（`.ipynb`）ファイル内のコメントやマークダウンセルを翻訳。
- 開発メモやレポートの多言語対応に便利です。

### `translate_txt.py`
- `.txt` テキストファイルの翻訳を行います。
- なぜか私の環境だとgoogle docs上の日本語を読み込めないので、現状、Google drive APIを使ってgoogle docs→txt fileに変換してからここで翻訳している。一発でgoogle docsを読み込む→翻訳　までしてくれるように改変してほしい。
