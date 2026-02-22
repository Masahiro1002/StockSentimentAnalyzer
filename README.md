# 📊 Stock Sentiment Analyzer

Yahoo!ファイナンス掲示板のセンチメントと株価を連動して可視化するWebアプリケーション。

## 技術スタック

| レイヤー | ツール |
|---|---|
| バックエンド | Python 3.10+ |
| AI分析 | Gemini 1.5 Flash (Free Tier) |
| 株価取得 | yfinance |
| スクレイピング | BeautifulSoup |
| DB | Supabase (PostgreSQL Free Tier) |
| 自動化 | GitHub Actions |
| フロントエンド | HTML/CSS/JS + Chart.js |
| ホスティング | GitHub Pages |

## セットアップ

### 1. 外部サービスの準備

1. **Supabase** — [supabase.com](https://supabase.com) でプロジェクトを作成
2. **Gemini API** — [Google AI Studio](https://aistudio.google.com/) でAPIキーを発行
3. `.env.example` をコピーして `.env` を作成し、各キーを設定

### 2. DBテーブル作成

Supabase SQL Editor で `scripts/init_db.sql` を実行してください。

### 3. Python環境

```bash
pip install -r requirements.txt
```

### 4. バッチ実行（手動テスト）

```bash
python scripts/run_daily.py
```

### 5. フロントエンド

`docs/index.html` をブラウザで開き、Supabase URL と Anon Key を入力してください。

## GitHub Actions 自動化

リポジトリにプッシュ後、以下の Secrets を設定してください：

- `SUPABASE_URL`
- `SUPABASE_KEY` (service_role key)
- `GEMINI_API_KEY`

毎日 JST 16:00 (平日) に自動実行されます。

## GitHub Pages デプロイ

1. リポジトリ Settings → Pages
2. Source: `Deploy from a branch`
3. Branch: `main` / `/docs`

## ディレクトリ構成

```
├── src/               # Pythonバックエンド
│   ├── stock_data.py  # 株価取得
│   ├── scraper.py     # 掲示板スクレイピング
│   ├── sentiment.py   # Gemini センチメント分析
│   └── db.py          # Supabase CRUD
├── scripts/
│   ├── run_daily.py   # 日次バッチ
│   └── init_db.sql    # テーブル定義
├── docs/              # フロントエンド (GitHub Pages)
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .github/workflows/
    └── daily_analysis.yml
```

## 注意事項

⚠️ Yahoo!ファイナンス掲示板のスクレイピングは利用規約に抵触する可能性があります。個人利用・学習目的での利用を推奨します。
