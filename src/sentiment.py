"""
sentiment.py - Gemini API を使ったセンチメント分析モジュール
"""

import os
import json
import time
import re
import random
from collections import defaultdict
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Gemini クライアント（モジュールレベルで初期化）
_client = None


def _get_gemini_client():
    """Gemini クライアントを初期化して返す"""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません。.env ファイルを確認してください。")

    _client = genai.Client(api_key=api_key)
    return _client


def analyze_sentiment(posts: list[dict], sample_size: int = 30) -> list[dict]:
    """
    Gemini 2.5 Flash で投稿のセンチメントを分析する。

    投稿数が sample_size を超える場合、ランダムに sample_size 件を
    抽出して分析する（Gemini 無料枠のトークン制限対策）。

    Args:
        posts: 各投稿の 'body' と 'posted_at' を含む辞書のリスト
        sample_size: 分析する最大投稿数（デフォルト: 30）

    Returns:
        list[dict]: 各投稿に 'sentiment_score' を追加した辞書のリスト
                    スコアは -1.0（ネガティブ）～ 1.0（ポジティブ）
    """
    if not posts:
        return []

    # sample_size を超える場合はランダムサンプリング
    if len(posts) > sample_size:
        print(f"[INFO] {len(posts)} 件から {sample_size} 件をランダム抽出")
        posts = random.sample(posts, sample_size)

    client = _get_gemini_client()

    # バッチサイズ（全投稿を1回のリクエストにまとめる）
    batch_size = 50
    max_retries = 3
    retry_base_delay = 60  # デフォルトのリトライ待機秒数
    scored_posts = []

    for i in range(0, len(posts), batch_size):
        batch = posts[i:i + batch_size]

        # プロンプト構築
        posts_text = ""
        for j, post in enumerate(batch):
            posts_text += f"[投稿{j + 1}] {post['body'][:300]}\n\n"

        prompt = f"""以下は株式投資に関する掲示板の投稿です。
各投稿のセンチメント（感情）を分析し、以下の形式でJSON配列として返してください。

スコアの基準:
- 1.0: 非常にポジティブ（強い買い推奨、好決算への期待など）
- 0.5: ややポジティブ
- 0.0: 中立
- -0.5: ややネガティブ
- -1.0: 非常にネガティブ（強い売り推奨、業績悪化への懸念など）

投稿:
{posts_text}

以下のJSON形式で回答してください。余計なテキストは不要です:
[{{"index": 1, "score": 0.5}}, {{"index": 2, "score": -0.3}}, ...]
"""

        batch_num = i // batch_size + 1
        success = False

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                response_text = response.text.strip()

                # JSONを抽出（コードブロック内の場合にも対応）
                json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
                if json_match:
                    scores = json.loads(json_match.group())
                else:
                    print(f"[WARNING] バッチ {batch_num}: JSON解析に失敗、デフォルト値を使用")
                    scores = [{"index": j + 1, "score": 0.0} for j in range(len(batch))]

                # スコアを投稿に付与
                for j, post in enumerate(batch):
                    score = 0.0
                    for s in scores:
                        if s.get("index") == j + 1:
                            score = max(-1.0, min(1.0, float(s.get("score", 0.0))))
                            break

                    scored_posts.append({
                        **post,
                        "sentiment_score": round(score, 2)
                    })

                success = True
                break  # 成功したらリトライループを抜ける

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg and attempt < max_retries - 1:
                    # retry_delay を抽出（見つからなければデフォルト値を使用）
                    delay_match = re.search(r"retry in ([\d.]+)s", error_msg)
                    delay = float(delay_match.group(1)) if delay_match else retry_base_delay
                    print(f"[RETRY] バッチ {batch_num}: レート制限到達、{delay:.0f}秒後にリトライ ({attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"[ERROR] Gemini API呼び出しエラー (バッチ {batch_num}): {e}")
                    break

        # 全リトライ失敗時はスコア0.0をデフォルトで付与
        if not success:
            for post in batch:
                scored_posts.append({
                    **post,
                    "sentiment_score": 0.0
                })

        # バッチ間のスリープ（レート制限を予防）
        if i + batch_size < len(posts):
            time.sleep(5)

    return scored_posts


def aggregate_daily_sentiment(scored_posts: list[dict]) -> dict[str, float]:
    """
    スコア付き投稿を日別に平均化する。

    Args:
        scored_posts: 'posted_at' と 'sentiment_score' を含む辞書のリスト

    Returns:
        dict[str, float]: {日付: 平均スコア} の辞書
    """
    daily_scores = defaultdict(list)

    for post in scored_posts:
        date = post.get("posted_at", "")
        score = post.get("sentiment_score", 0.0)
        if date:
            daily_scores[date].append(score)

    return {
        date: round(sum(scores) / len(scores), 3)
        for date, scores in sorted(daily_scores.items())
    }


def analyze_news_sentiment(news_items: list[dict]) -> list[dict]:
    """
    Gemini でニュースヘッドラインの要約 + センチメント分析を一括実行する。

    Args:
        news_items: 各ニュースの 'headline' を含む辞書のリスト

    Returns:
        list[dict]: 各ニュースに 'summary' と 'sentiment_score' を追加した辞書のリスト
    """
    if not news_items:
        return []

    client = _get_gemini_client()
    max_retries = 3
    retry_base_delay = 60

    # ヘッドライン一覧をプロンプトに組み込む
    headlines_text = ""
    for i, item in enumerate(news_items):
        headlines_text += f"[ニュース{i + 1}] {item['headline']}\n"

    prompt = f"""以下は株式・金融に関するニュースのヘッドラインです。
各ニュースについて、以下の2つを分析してください:
1. ヘッドラインの内容を1行で要約（最大50文字）
2. 投資家から見たセンチメントスコア

スコアの基準:
- 1.0: 非常にポジティブ（好決算、株価上昇要因など）
- 0.5: ややポジティブ
- 0.0: 中立（テクニカル指標、市場概況など）
- -0.5: ややネガティブ
- -1.0: 非常にネガティブ（業績悪化、リスク要因など）

ニュース:
{headlines_text}

以下のJSON形式で回答してください。余計なテキストは不要です:
[{{"index": 1, "summary": "要約テキスト", "score": 0.5}}, ...]
"""

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            response_text = response.text.strip()

            # JSON 抽出
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group())
            else:
                print("[WARNING] ニュース分析: JSON解析に失敗、デフォルト値を使用")
                results = [{"index": i + 1, "summary": item["headline"][:50], "score": 0.0}
                           for i, item in enumerate(news_items)]

            # 結果をニュースアイテムに付与
            scored_news = []
            for i, item in enumerate(news_items):
                summary = item["headline"][:50]
                score = 0.0
                for r in results:
                    if r.get("index") == i + 1:
                        summary = r.get("summary", summary)
                        score = max(-1.0, min(1.0, float(r.get("score", 0.0))))
                        break

                scored_news.append({
                    **item,
                    "summary": summary,
                    "sentiment_score": round(score, 3),
                })

            return scored_news

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and attempt < max_retries - 1:
                delay_match = re.search(r"retry in ([\d.]+)s", error_msg)
                delay = float(delay_match.group(1)) if delay_match else retry_base_delay
                print(f"[RETRY] ニュース分析: レート制限到達、{delay:.0f}秒後にリトライ ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"[ERROR] ニュース分析エラー: {e}")
                break

    # 全リトライ失敗時
    return [{**item, "summary": item["headline"][:50], "sentiment_score": 0.0}
            for item in news_items]


if __name__ == "__main__":
    # テスト実行（ダミーデータ）
    test_posts = [
        {"body": "トヨタの決算が好調で株価上昇が期待できる！買い増ししたい。", "posted_at": "2024-01-15"},
        {"body": "最近の円安で業績が心配。売りかもしれない。", "posted_at": "2024-01-15"},
        {"body": "EV戦略がうまくいくか不透明。様子見。", "posted_at": "2024-01-16"},
    ]

    print("=== センチメント分析テスト ===")
    scored = analyze_sentiment(test_posts)
    for post in scored:
        print(f"日時: {post['posted_at']} | スコア: {post['sentiment_score']:+.2f} | {post['body'][:50]}...")

    print("\n=== 日別集計 ===")
    daily = aggregate_daily_sentiment(scored)
    for date, score in daily.items():
        print(f"{date}: {score:+.3f}")
