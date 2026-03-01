"""
db.py - Supabase データベース操作モジュール
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def fetch_tickers() -> list[dict]:
    """
    アクティブな銘柄リストをDBから取得する。

    Returns:
        list[dict]: 各銘柄の code, board_code, name を含む辞書リスト
    """
    client = get_supabase_client()
    result = client.table("tickers") \
        .select("code, board_code, name") \
        .eq("active", True) \
        .execute()
    return result.data


def get_supabase_client() -> Client:
    """Supabase クライアントを初期化して返す"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY が設定されていません。"
            ".env ファイルまたは環境変数を確認してください。"
        )

    return create_client(url, key)


def upsert_sentiment_data(records: list[dict]) -> dict:
    """
    センチメントデータをDBにUPSERTする。
    (date, ticker) の組み合わせが重複する場合は更新する。

    Args:
        records: 各レコードは以下のキーを含む辞書:
            - date: str (YYYY-MM-DD)
            - ticker: str (例: "7203.T")
            - sentiment_score: float (-1.0 ~ 1.0)
            - close_price: float

    Returns:
        dict: Supabase APIレスポンス
    """
    client = get_supabase_client()

    # 各レコードに created_at を追加
    for record in records:
        record["created_at"] = datetime.utcnow().isoformat()

    result = client.table("sentiment_data").upsert(
        records,
        on_conflict="date,ticker"
    ).execute()

    print(f"[INFO] {len(records)} 件のレコードをUPSERTしました。")
    return result


def insert_stock_prices(records: list[dict]) -> dict:
    """
    株価データをDBにUPSERTする。close_price のみを持つレコードを渡すことで、
    既存のセンチメントスコアを上書きせずに株価だけ更新できる。

    Args:
        records: 各レコードは以下のキーを含む辞書:
            - date: str (YYYY-MM-DD)
            - ticker: str (例: "7203.T")
            - close_price: float

    Returns:
        dict: Supabase APIレスポンス
    """
    if not records:
        return None

    client = get_supabase_client()

    # created_at を追加
    for record in records:
        record["created_at"] = datetime.utcnow().isoformat()

    # close_price を常に更新する（sentiment_score を含まないレコードを渡すため既存スコアは保護される）
    result = client.table("sentiment_data").upsert(
        records,
        on_conflict="date,ticker"
    ).execute()

    print(f"[INFO] {len(records)} 件の株価レコードをUPSERTしました。")
    return result


def fetch_sentiment_data(ticker: str, days: int = 90) -> list[dict]:
    """
    指定された銘柄のセンチメントデータをDBから取得する。

    Args:
        ticker: 銘柄コード（例: "7203.T"）
        days: 取得する日数（デフォルト: 90）

    Returns:
        list[dict]: 各レコードの辞書リスト
    """
    client = get_supabase_client()

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    result = client.table("sentiment_data") \
        .select("date, ticker, sentiment_score, close_price") \
        .eq("ticker", ticker) \
        .gte("date", start_date) \
        .order("date", desc=False) \
        .execute()

    return result.data


def upsert_news_data(records: list[dict]) -> dict:
    """
    ニュースデータをDBにUPSERTする。

    Args:
        records: 各レコードは以下のキーを含む辞書:
            - date: str (YYYY-MM-DD)
            - ticker: str
            - headline: str
            - summary: str
            - sentiment_score: float
            - source_name: str
            - source_url: str
    """
    if not records:
        return None

    client = get_supabase_client()

    for record in records:
        record["created_at"] = datetime.utcnow().isoformat()

    result = client.table("news_data").upsert(
        records,
        on_conflict="date,ticker,headline"
    ).execute()

    print(f"[INFO] {len(records)} 件のニュースレコードを保存しました。")
    return result


def fetch_news_data(ticker: str, date: str) -> list[dict]:
    """
    指定日のニュースデータをDBから取得する。

    Args:
        ticker: 銘柄コード
        date: 日付 (YYYY-MM-DD)

    Returns:
        list[dict]: ニュースレコードのリスト
    """
    client = get_supabase_client()

    result = client.table("news_data") \
        .select("date, ticker, headline, summary, sentiment_score, source_name, source_url") \
        .eq("ticker", ticker) \
        .eq("date", date) \
        .order("sentiment_score", desc=True) \
        .execute()

    return result.data


def fetch_news_sentiment_daily(ticker: str, days: int = 90) -> list[dict]:
    """
    指定期間のニュースセンチメント日別平均を取得する。

    Args:
        ticker: 銘柄コード
        days: 取得する日数

    Returns:
        list[dict]: {date, avg_score} のリスト
    """
    client = get_supabase_client()

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    result = client.table("news_data") \
        .select("date, sentiment_score") \
        .eq("ticker", ticker) \
        .gte("date", start_date) \
        .order("date", desc=False) \
        .execute()

    # 日別に平均化
    from collections import defaultdict
    daily = defaultdict(list)
    for row in result.data:
        if row["sentiment_score"] is not None:
            daily[row["date"]].append(row["sentiment_score"])

    return [
        {"date": date, "news_sentiment": round(sum(scores) / len(scores), 3)}
        for date, scores in sorted(daily.items())
    ]


if __name__ == "__main__":
    # テスト: データ取得
    print("=== DB接続テスト ===")
    try:
        data = fetch_sentiment_data("7203.T", days=30)
        print(f"取得件数: {len(data)}件")
        for row in data[:5]:
            print(row)
    except Exception as e:
        print(f"エラー: {e}")
