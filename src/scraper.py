"""
scraper.py - Yahoo!ファイナンス掲示板スクレイピングモジュール

毎日1回、前日分の投稿を掲示板から取得する。
投稿番号ベースのナビゲーションで前日の投稿を網羅的に取得する。
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re


# セッション設定
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 投稿レート推定値（1日あたりの投稿数）
_ESTIMATED_POSTS_PER_DAY = 300


def _parse_posts_from_page(html: str) -> list[dict]:
    """フォーラムページのHTMLから投稿を抽出する。"""
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    articles = soup.find_all(
        "article",
        class_=lambda c: c and any(
            "_BbsItem_" in cls for cls in (c if isinstance(c, list) else [c])
        ),
    )

    for article in articles:
        try:
            # 日時の取得
            date_elem = article.find(
                lambda tag: tag.get("class")
                and any(
                    "postDate" in c and "Block" not in c
                    for c in tag.get("class", [])
                )
            )

            posted_at = ""
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                date_match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_text)
                if date_match:
                    posted_at = (
                        f"{date_match.group(1)}-"
                        f"{date_match.group(2).zfill(2)}-"
                        f"{date_match.group(3).zfill(2)}"
                    )

            if not posted_at:
                continue  # 日付が取れない投稿はスキップ

            # 本文の取得
            body_elem = article.find(
                lambda tag: tag.get("class")
                and any("__body" in c for c in tag.get("class", []))
            )
            if not body_elem:
                continue

            body = body_elem.get_text(strip=True)
            body = re.sub(r">>?\d+", "", body)
            body = body.strip()

            if not body or len(body) < 5:
                continue

            posts.append({
                "body": body[:500],
                "posted_at": posted_at,
            })

        except Exception as e:
            print(f"[WARNING] 投稿パース中にエラー: {e}")
            continue

    return posts


def _get_latest_post_number(html: str) -> int | None:
    """フォーラムページのHTMLから最新の投稿番号を取得する。"""
    soup = BeautifulSoup(html, "html.parser")

    comment_no_elems = soup.find_all(
        lambda tag: tag.get("class")
        and any("commentNo" in c for c in tag.get("class", []))
    )

    max_no = 0
    for elem in comment_no_elems:
        text = elem.get_text(strip=True)
        match = re.search(r"No\.(\d+)", text)
        if match:
            num = int(match.group(1))
            if num > max_no:
                max_no = num

    return max_no if max_no > 0 else None


def scrape_yahoo_finance_board(
    stock_code: str,
    target_date: str | None = None,
) -> list[dict]:
    """
    Yahoo!ファイナンス掲示板から指定日の投稿を取得する。

    投稿番号ベースのナビゲーションで対象日の投稿範囲を探索し、
    全投稿を取得する。

    Args:
        stock_code: 銘柄コード（例: "7203" または "7203.T"）
        target_date: 取得対象の日付 (YYYY-MM-DD)。
                     None の場合は前日を対象とする。

    Returns:
        list[dict]: 各投稿の 'body' と 'posted_at' を含む辞書のリスト
    """
    code = stock_code.replace(".T", "")
    base_url = f"https://finance.yahoo.co.jp/quote/{code}.T/forum"

    # 対象日付の決定
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"[INFO] 対象日: {target_date}")

    # Step 1: 最新ページを取得して最新投稿番号を把握
    print(f"[INFO] 掲示板をスクレイピング中: {base_url}")
    try:
        response = requests.get(base_url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] フォーラムページの取得に失敗: {e}")
        return []

    latest_posts = _parse_posts_from_page(response.text)
    latest_no = _get_latest_post_number(response.text)

    if not latest_no:
        print("[WARNING] 最新投稿番号を検出できませんでした")
        return [p for p in latest_posts if p["posted_at"] == target_date]

    print(f"  → 最新投稿: No.{latest_no}")

    # 最新ページから対象日の投稿を収集
    target_posts = [p for p in latest_posts if p["posted_at"] == target_date]

    # Step 2: 投稿番号で前日の投稿範囲を推定し、サンプリング
    # 1日の推定投稿数をもとに前日の範囲を計算
    today = datetime.now().strftime("%Y-%m-%d")
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    days_back = (today_dt - target_dt).days

    # 対象日の投稿番号の推定範囲
    range_end = latest_no - (_ESTIMATED_POSTS_PER_DAY * (days_back - 1))
    range_start = latest_no - (_ESTIMATED_POSTS_PER_DAY * (days_back + 1))
    range_start = max(1, range_start)

    total_range = range_end - range_start
    if total_range <= 0:
        print("[WARNING] 推定範囲が不正です")
        return _deduplicate(target_posts)

    # 等間隔で20ポイントをサンプリング（1リクエスト=1件前後なので多めに）
    num_samples = min(30, max(10, total_range // 50))
    step = total_range // num_samples

    print(f"[INFO] 投稿番号 {range_start}〜{range_end} の範囲をサンプリング ({num_samples} ポイント)")

    found_dates = set()
    for i in range(num_samples):
        post_no = range_start + (step * i)
        url = f"{base_url}/{post_no}"

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            page_posts = _parse_posts_from_page(resp.text)

            for p in page_posts:
                found_dates.add(p["posted_at"])
                if p["posted_at"] == target_date:
                    target_posts.append(p)

        except requests.RequestException:
            pass

        time.sleep(0.5)

    result = _deduplicate(target_posts)
    print(f"  → {target_date} の投稿: {len(result)} 件取得")
    return result


def _deduplicate(posts: list[dict]) -> list[dict]:
    """投稿の重複を排除する"""
    seen = set()
    unique = []
    for post in posts:
        key = post["body"][:100]
        if key not in seen:
            seen.add(key)
            unique.append(post)
    return unique


if __name__ == "__main__":
    posts = scrape_yahoo_finance_board("7203")
    print(f"\n取得件数: {len(posts)}")
    for i, post in enumerate(posts[:5], 1):
        print(f"\n--- 投稿 {i} ---")
        print(f"日時: {post['posted_at']}")
        print(f"本文: {post['body'][:100]}...")
