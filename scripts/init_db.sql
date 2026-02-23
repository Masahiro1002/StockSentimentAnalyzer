-- init_db.sql
-- Supabase (PostgreSQL) テーブル定義
-- Supabase SQL Editor で実行してください

-- センチメントデータテーブル
CREATE TABLE IF NOT EXISTS sentiment_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(4, 3),
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

-- ============================================
-- 銘柄マスタテーブル
-- ============================================
CREATE TABLE IF NOT EXISTS tickers (
    code TEXT PRIMARY KEY,           -- yfinance ティッカーコード (例: '7011.T', 'USDJPY=X')
    board_code TEXT NOT NULL,        -- Yahoo!ファイナンス掲示板コード
    name TEXT NOT NULL,              -- 銘柄名
    active BOOLEAN DEFAULT true     -- 分析対象フラグ
);

-- 初期データ
INSERT INTO tickers (code, board_code, name) VALUES
    ('7011.T', '7011.T', '三菱重工業'),
    ('8316.T', '8316.T', '三井住友FG'),
    ('3003.T', '3003.T', 'ヒューリック'),
    ('1326.T', '1326.T', 'SPDRゴールド'),
    ('USDJPY=X', 'USDJPY=X', '米ドル/円')
ON CONFLICT (code) DO NOTHING;

-- RLS
ALTER TABLE tickers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read tickers" ON tickers;
CREATE POLICY "Allow public read tickers"
    ON tickers
    FOR SELECT
    TO anon
    USING (true);

DROP POLICY IF EXISTS "Allow service role full access on tickers" ON tickers;
CREATE POLICY "Allow service role full access on tickers"
    ON tickers
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================
-- ニュースデータテーブル
-- ============================================
CREATE TABLE IF NOT EXISTS news_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    sentiment_score DECIMAL(4, 3),
    source_name TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_news UNIQUE (date, ticker, headline)
);

CREATE INDEX IF NOT EXISTS idx_news_ticker_date ON news_data (ticker, date DESC);

-- RLS
ALTER TABLE news_data ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read news" ON news_data;
CREATE POLICY "Allow public read news"
    ON news_data
    FOR SELECT
    TO anon
    USING (true);

DROP POLICY IF EXISTS "Allow service role full access on news" ON news_data;
CREATE POLICY "Allow service role full access on news"
    ON news_data
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
