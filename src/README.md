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
- `.txt` テキストファイルとGoogle Docsの翻訳を行います。
- Google Docsの内容を直接読み込んで翻訳します。
- 翻訳されたファイルは `TRANSLATED_FOLDER` に保存されます。



#実行方法　(translate_txt.py)
#セットアップガイド

## セットアップ手順

### 1. 必要になるサービス等

- Python 3.8以上
- Google Cloud Project
- OpenAI API アカウント
- Google Drive のフォルダと翻訳したいテキストファイル

### 2. Google Cloud設定 

#### Step 1: Google Cloud Project作成
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成

#### Step 2: APIを有効化
1. **Google Drive API** を有効化:
   - https://console.developers.google.com/apis/api/drive.googleapis.com/overview

#### Step 3: サービスアカウント作成
1. Google Cloud Console → IAM と管理 → サービスアカウント
2. サービスアカウントを作成をクリック
4. 作成後、アカウントをクリックして「キー」タブへ
5. 「キーを追加」→「新しいキーを作成」→「JSON」
6. ダウンロードしたJSONファイルをプロジェクトのルートディレクトリに配置

### 3. Google Drive設定 

#### Step 1: フォルダを準備
1. Google Drive で翻訳したい`.txt`ファイルが入ったフォルダを用意
2. 翻訳プロンプトが書かれたGoogle Docを用意

#### Step 2: サービスアカウントと共有
**重要**: 以下のメールアドレスとフォルダを共有する必要があります:
```
YOUR_SERVICE_ACCOUNT_EMAIL@YOUR_PROJECT.iam.gserviceaccount.com
```
（サービスアカウントのJSONファイルの`client_email`フィールドで確認できます）

1. 翻訳したいファイルが入ったフォルダを右クリック → 「共有」
2. サービスアカウントのメールアドレスを追加
3. 権限を「編集者」に設定（ファイル削除が必要な場合）
4. 翻訳プロンプトのGoogle Docも同様に共有

#### Step 3: フォルダIDとドキュメントIDを取得
1. **フォルダID**: Google DriveでフォルダのURLから取得
   ```
   https://drive.google.com/drive/folders/EXAMPLEID
   ```
   → `EXAMPLEID` がフォルダID

2. **ドキュメントID**: Google DocのURLから取得
   ```
   https://docs.google.com/document/d/DOCUMENT_ID/edit
   ```
   → `DOCUMENT_ID` がドキュメントID

### 4. 環境変数設定 / Environment Variables

プロジェクトのルートディレクトリに`.env.example`があるが`.env`に改名する

```env
# Google Drive Settings
GOOGLE_KEY_FILE=your-service-account-key.json
GOOGLE_FOLDER_ID=your_folder_id_here
GOOGLE_PROMPT_DOC_ID=your_prompt_document_id_here

# OpenAI Settings
OPENAI_API_KEY=your_openai_api_key_here

# カスタムフォルダパス (現在はローカルで保存される設定になっている)
DESTINATION_FOLDER=./GCI_copy_downloads　
TRANSLATED_FOLDER=./GCI_copy_translated
```

### 5. Python環境設定

```bash
# 1. 仮想環境作成（プロジェクトルートで実行）
python -m venv .venv

# 2. 仮想環境をアクティベート
# mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 3. 依存関係をインストール
pip install -r requirements.txt
```

### 6. 実行方法

```bash
# テキストファイル翻訳
python src/translate_txt.py

# Jupyter Notebook翻訳
python src/translate_ipynb.py

# 画像翻訳
python src/translate_image.py
```

### 7.　エラーが起きる場合

####  "Found 0 .txt files in the folder" エラー
**原因**: フォルダにアクセスできない、またはファイルが見つからない

**解決方法**:
1. フォルダIDが正しいかGoogle DriveのURLで確認
2. サービスアカウントとフォルダが共有されているか確認
3. フォルダに実際に`.txt`ファイルがあるか確認

####  "Google Drive API has not been used" エラー
**原因**: Google Drive APIが有効化されていない

**解決方法**:
1. Google Cloud Console でGoogle Drive APIを有効化
2. 数分待ってから再実行

#### 🔍 "File not found" エラー
**原因**: フォルダID不正、または権限不足

**解決方法**:
1. Google DriveのURLからフォルダIDを再確認
2. サービスアカウントとフォルダを共有

---