"""
run_daily.py - 日次バッチ処理メインスクリプト

毎日1回実行し、前日分のデータを処理する:
  1. 株価データ取得（yfinance）
  2. 前日分の掲示板投稿をスクレイピング
  3. 30件をランダム抽出してGemini APIでセンチメント分析
  4. Supabase に保存
"""

import sys
import os
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.stock_data import get_stock_prices
from src.scraper import scrape_yahoo_finance_board
from src.sentiment import analyze_sentiment, aggregate_daily_sentiment
from src.db import upsert_sentiment_data


# 対象銘柄リスト
TARGET_TICKERS = [
    {"code": "7203.T", "board_code": "7203", "name": "トヨタ自動車"},
]

# センチメント分析に使う投稿のサンプル数
SENTIMENT_SAMPLE_SIZE = 30


def run_daily_analysis():
    """日次分析バッチを実行する"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print("=" * 60)
    print("📊 Stock Sentiment Analyzer - 日次バッチ処理")
    print(f"   対象日: {yesterday}")
    print("=" * 60)

    for ticker_info in TARGET_TICKERS:
        ticker = ticker_info["code"]
        board_code = ticker_info["board_code"]
        name = ticker_info["name"]

        print(f"\n{'─' * 40}")
        print(f"🏢 {name} ({ticker})")
        print(f"{'─' * 40}")

        try:
            # 1. 株価データ取得（直近の株価を取得）
            print("\n📈 Step 1: 株価データ取得中...")
            stock_df = get_stock_prices(ticker, days=7)
            print(f"  → {len(stock_df)} 日分の株価データを取得")

            # 前日の株価を取得
            price_map = dict(zip(stock_df["date"], stock_df["close_price"]))
            close_price = price_map.get(yesterday)
            if close_price is not None:
                print(f"  → {yesterday} の終値: ¥{close_price:,.2f}")
            else:
                print(f"  → {yesterday} は取引日ではありません（休日）")

            # 2. 前日分の掲示板投稿をスクレイピング
            print("\n💬 Step 2: 前日分の掲示板スクレイピング中...")
            posts = scrape_yahoo_finance_board(board_code, target_date=yesterday)
            print(f"  → {len(posts)} 件の投稿を取得")

            if not posts:
                print(f"[WARNING] {yesterday} の投稿がありません。")
                # 株価のみのレコードを保存
                if close_price is not None:
                    records = [{
                        "date": yesterday,
                        "ticker": ticker,
                        "sentiment_score": 0.0,
                        "close_price": float(close_price),
                    }]
                    upsert_sentiment_data(records)
                    print(f"  ✅ 株価データのみ保存")
                continue

            # 3. ランダムサンプリング + センチメント分析
            print(f"\n🤖 Step 3: {SENTIMENT_SAMPLE_SIZE}件をサンプリングしてセンチメント分析中...")
            scored_posts = analyze_sentiment(posts, sample_size=SENTIMENT_SAMPLE_SIZE)
            daily_sentiment = aggregate_daily_sentiment(scored_posts)

            score = daily_sentiment.get(yesterday, 0.0)
            print(f"  → {yesterday} のセンチメントスコア: {score:+.3f}")

            # 4. DB保存
            print("\n💾 Step 4: DB保存中...")
            record = {
                "date": yesterday,
                "ticker": ticker,
                "sentiment_score": score,
                "close_price": float(close_price) if close_price is not None else None,
            }
            upsert_sentiment_data([record])
            print(f"  ✅ 保存完了")

        except Exception as e:
            print(f"\n❌ エラーが発生しました ({ticker}): {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'=' * 60}")
    print("✅ 日次バッチ処理完了")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_daily_analysis()
