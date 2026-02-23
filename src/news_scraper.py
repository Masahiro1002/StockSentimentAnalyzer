"""
news_scraper.py - Yahoo!ファイナンス ニュースページ スクレイピングモジュール

銘柄のニュースページからヘッドラインを取得し、前日分をフィルタリングする。
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def scrape_yahoo_finance_news(
    ticker: str,
    target_date: str | None = None,
) -> list[dict]:
    """
    Yahoo!ファイナンスのニュースページから指定日のニュースを取得する。

    Args:
        ticker: 銘柄コード（例: "7011.T", "USDJPY=X"）
        target_date: 取得対象の日付 (YYYY-MM-DD)。None の場合は前日。

    Returns:
        list[dict]: 各ニュースの headline, date, source_name, source_url を含む辞書リスト
    """
    url = f"https://finance.yahoo.co.jp/quote/{ticker}/news"

    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    target_month = target_dt.month
    target_day = target_dt.day

    print(f"[INFO] ニュースページを取得中: {url}")

    try:
        response = requests.get(url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] ニュースページの取得に失敗: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    news_items = []

    # ニュースリンクを全取得
    links = soup.find_all("a", href=re.compile(r"/news/detail/"))

    for link in links:
        try:
            headline = link.get_text(strip=True)
            href = link.get("href", "")

            if not headline or len(headline) < 5:
                continue

            # ソース名と日付を除去してクリーンなヘッドラインにする
            # ヘッドラインの末尾に "2/22株探ニュース" のような形式で日付とソースが付く
            date_source_match = re.search(
                r"(\d{1,2})/(\d{1,2})([\w・\u3000-\u9fff]+)$", headline
            )

            source_name = ""
            news_month = None
            news_day = None

            if date_source_match:
                news_month = int(date_source_match.group(1))
                news_day = int(date_source_match.group(2))
                source_name = date_source_match.group(3)
                # ヘッドラインから日付+ソースを除去
                headline = headline[:date_source_match.start()].strip()

            if not headline:
                continue

            # 対象日付のニュースのみフィルタ
            if news_month is not None and news_day is not None:
                if news_month != target_month or news_day != target_day:
                    continue
            else:
                continue  # 日付が取れないニュースはスキップ

            # URL を組み立て
            source_url = href
            if not source_url.startswith("http"):
                source_url = f"https://finance.yahoo.co.jp{href}"

            news_items.append({
                "headline": headline,
                "date": target_date,
                "source_name": source_name,
                "source_url": source_url,
            })

        except Exception as e:
            print(f"[WARNING] ニュースパース中にエラー: {e}")
            continue

    # 重複を除去（同じヘッドラインが複数出現する場合）
    seen = set()
    unique_news = []
    for item in news_items:
        if item["headline"] not in seen:
            seen.add(item["headline"])
            unique_news.append(item)

    print(f"  → {target_date} のニュース: {len(unique_news)} 件取得")
    return unique_news


if __name__ == "__main__":
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    news = scrape_yahoo_finance_news("7011.T", target_date=yesterday)
    print(f"\n取得件数: {len(news)}")
    for i, item in enumerate(news[:5], 1):
        print(f"\n--- ニュース {i} ---")
        print(f"日付: {item['date']}")
        print(f"見出し: {item['headline']}")
        print(f"ソース: {item['source_name']}")
        print(f"URL: {item['source_url']}")
