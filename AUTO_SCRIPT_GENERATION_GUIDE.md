# Jupyterノートブックから教育スクリプト自動生成ツール

## 概要

`auto_script_generation_from_ipynb.py`は、Jupyterノートブック（.ipynb）ファイルから、動画講義用の流暢な教育スクリプトを自動生成するツールです。このツールは、技術的な内容を自然な教育ナラティブに変換し、学生が理解しやすい形式で提供します。

## 主な特徴

- 📚 **スマートなコンテンツ抽出**: 大きな埋め込み画像やデータを自動的に処理
- 🔄 **自然な流れ**: セクション区切りのない、継続的なナラティブを生成
- 🎯 **適応的な説明深度**: 簡単な概念は簡潔に、複雑な概念は詳細に説明
- ☁️ **Google Drive統合**: Google ColabやDriveから直接ノートブックをダウンロード
- ⚡ **レート制限対応**: API制限を尊重した安全な処理

## インストール

### 必要な依存関係

```bash
pip install -r requirements.txt
```

オプション：より正確なトークンカウントのために：
```bash
pip install tiktoken
```

### 環境変数の設定

```bash
export OPENAI_API_KEY="your-api-key-here"
export GOOGLE_KEY_FILE="path/to/google_key.json"  # Google Drive用（オプション）
```

## 使用方法

### 基本的な使用法

ローカルのJupyterノートブックファイルを処理する場合：

```bash
python src/auto_script_generation_from_ipynb.py notebook.ipynb
```

### Google Colab/Driveから直接処理

Google ColabのURLを使用：
```bash
python src/auto_script_generation_from_ipynb.py --drive-url "https://colab.research.google.com/drive/FILE_ID"
```

Google DriveのファイルIDを使用：
```bash
python src/auto_script_generation_from_ipynb.py --drive-file-id "FILE_ID"
```

### 詳細オプション

```bash
python src/auto_script_generation_from_ipynb.py notebook.ipynb \
    --model gpt-4o-mini \              # 使用するOpenAIモデル
    --temperature 0.7 \                # 生成の温度（0.0-1.0）
    --output-dir data/scripts \        # 出力ディレクトリ
    --max-chunk-tokens 1500 \          # チャンクあたりの最大トークン数
    --rpm-limit 20 \                   # 分あたりのリクエスト制限
    --tpm-limit 40000                  # 分あたりのトークン制限
```

## ワークフロー

### 1. コンテンツ抽出
- ノートブックからマークダウンとコードセルを抽出
- 大きな埋め込み画像（base64など）を自動的に検出して置換
- コードブロックとその出力を保持

### 2. スマートチャンキング
- 自然な区切り（ヘッダー、段落）でテキストを分割
- トークン制限を考慮した最適なチャンクサイズ
- コンテキストの連続性を維持

### 3. 教育スクリプト生成
- 各チャンクに対してAIが教育ナラティブを生成
- 前のコンテキストを考慮した自然な遷移
- 内容の複雑さに応じた説明の深さを自動調整

### 4. 最終統合
- すべてのチャンクを滑らかに結合
- 一貫した教育的な流れを確保
- 読み上げに適した形式で出力

## 出力例

入力ファイル: `Classification_Level_1.ipynb`
出力ファイル: `Classification_Level_1_teaching_script.txt`

出力内容の例：
```
今日は分類問題に対する教師あり学習のワークフローについて深く掘り下げていきます。
このコースでは、決定木モデルを主要なツールとして使用し、ワークフローの各ステップ、
つまりデータの理解、処理、モデルの構築、そして評価について詳しく説明します...
```

## 実践的な使用例

### 例1: 基本的な分類問題のノートブック
```bash
python src/auto_script_generation_from_ipynb.py "data/downloads/Copy of Exercise: Classification Level 1.ipynb" --model gpt-4o-mini
```

### 例2: Google Colabからの直接処理
```bash
python src/auto_script_generation_from_ipynb.py \
    --drive-url "https://colab.research.google.com/drive/1XaSKGbxaqUb3pTZg5RSbbpsr4152Gspa" \
    --model gpt-4o-mini \
    --max-chunk-tokens 1000
```

## トラブルシューティング

### 大きなノートブックの処理
ノートブックに大きな画像やデータが含まれている場合：
- ツールは自動的にこれらを検出して置換
- `--max-chunk-tokens`を調整して小さなチャンクを使用

### レート制限エラー
API制限に達した場合：
- `--rpm-limit`と`--tpm-limit`を低い値に設定
- より小さなチャンクサイズを使用

### Google Drive認証エラー
- `GOOGLE_KEY_FILE`環境変数が正しく設定されているか確認
- サービスアカウントキーファイルの権限を確認

## ベストプラクティス

1. **モデル選択**
   - 高品質な出力: `gpt-4`
   - バランスの取れた選択: `gpt-4o-mini`（速度とコストの観点から推奨）

2. **チャンクサイズ**
   - デフォルト（1500トークン）は多くの場合で最適
   - 複雑な内容の場合は小さめに設定

3. **出力の確認**
   - 生成されたスクリプトを必ず確認
   - 必要に応じて手動で微調整

## 制限事項

- 非常に大きなノートブック（>1MB）の場合、処理時間が長くなる可能性
- 複雑な数式や図表の説明は限定的
- 言語は主に英語（入力が日本語の場合は日本語で出力可能）

## サポート

問題や質問がある場合は、GitHubのイシューページで報告してください。