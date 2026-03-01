"""
stock_data.py - yfinance を使った株価データ取得モジュール
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_stock_prices(ticker: str, days: int = 90) -> pd.DataFrame:
    """
    指定された銘柄の過去N日分の終値を取得する。

    Args:
        ticker: 銘柄コード（例: "7203.T"）
        days: 取得する日数（デフォルト: 90）

    Returns:
        pd.DataFrame: 'date' と 'close_price' カラムを持つDataFrame
    """
    end_date = datetime.now() + timedelta(days=1)  # yfinanceはend_dateをexclusiveで扱うため翌日を指定
    start_date = datetime.now() - timedelta(days=days)

    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date.strftime("%Y-%m-%d"),
                         end=end_date.strftime("%Y-%m-%d"))

    if hist.empty:
        print(f"[WARNING] {ticker} のデータが取得できませんでした。")
        return pd.DataFrame(columns=["date", "close_price"])

    df = hist[["Close"]].reset_index()
    df.columns = ["date", "close_price"]
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["close_price"] = df["close_price"].round(2)

    return df


if __name__ == "__main__":
    # テスト実行
    df = get_stock_prices("7203.T", days=10)
    print(df)
    print(f"\n取得件数: {len(df)}件")
