-- init_db.sql
-- Supabase (PostgreSQL) テーブル定義
-- Supabase SQL Editor で実行してください

-- センチメントデータテーブル
CREATE TABLE IF NOT EXISTS sentiment_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(4, 3) NOT NULL DEFAULT 0.0,
    close_price DECIMAL(12, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 同一日付・銘柄の重複を防ぐ
    CONSTRAINT unique_date_ticker UNIQUE (date, ticker)
);

-- 検索パフォーマンス向上のためのインデックス
CREATE INDEX IF NOT EXISTS idx_sentiment_ticker ON sentiment_data (ticker);
CREATE INDEX IF NOT EXISTS idx_sentiment_date ON sentiment_data (date DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_ticker_date ON sentiment_data (ticker, date DESC);

-- Row Level Security (RLS) を有効化
-- フロントエンド (anon key) からの読み取りのみ許可
ALTER TABLE sentiment_data ENABLE ROW LEVEL SECURITY;

-- 読み取り専用ポリシー（anon ユーザーはSELECTのみ可能）
DROP POLICY IF EXISTS "Allow public read access" ON sentiment_data;
CREATE POLICY "Allow public read access"
    ON sentiment_data
    FOR SELECT
    TO anon
    USING (true);

-- サービスロール（バックエンド）はフルアクセス
DROP POLICY IF EXISTS "Allow service role full access" ON sentiment_data;
CREATE POLICY "Allow service role full access"
    ON sentiment_data
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
