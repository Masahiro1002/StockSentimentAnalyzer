"""
db.py - Supabase データベース操作モジュール
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


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
