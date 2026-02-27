from pytrends.request import TrendReq
from typing import List, Dict


def get_trending_hot(period: str = "today") -> List[Dict]:
    """Return trending keywords for a time period (for the 'Mais Pesquisados' section).

    Returns list of {"keyword": str, "position": int, "source": str}
    """
    try:
        pytrends = TrendReq(hl="pt-BR", tz=360)

        if period in ("hours", "today"):
            # Real-time trending searches in Brazil
            trending = pytrends.trending_searches(pn="brazil")
            topics = trending[0].tolist()[:30]
            return [{"keyword": t, "position": i + 1, "source": "Google Trends"} for i, t in enumerate(topics)]

        # week / month: use related queries for broad Brazilian topic
        timeframe = "now 7-d" if period == "week" else "today 1-m"
        pytrends.build_payload(["brasil"], timeframe=timeframe, geo="BR")
        related = pytrends.related_queries()

        topics = []
        if "brasil" in related:
            top_df = related["brasil"].get("top")
            if top_df is not None and not top_df.empty:
                for _, row in top_df.head(25).iterrows():
                    topics.append({"keyword": row["query"], "position": len(topics) + 1, "source": "Google Trends"})

        # Fallback: real-time if related queries empty
        if not topics:
            trending = pytrends.trending_searches(pn="brazil")
            topics = [{"keyword": t, "position": i + 1, "source": "Google Trends"} for i, t in enumerate(trending[0].tolist()[:25])]

        return topics
    except Exception:
        return []


def get_related_trends(niche: str, geo: str = "") -> List[Dict]:
    try:
        pytrends = TrendReq(hl="pt-BR", tz=360)
        pytrends.build_payload([niche], timeframe="now 7-d", geo=geo)
        related = pytrends.related_queries()
        results = []
        if niche in related:
            top = related[niche].get("top")
            if top is not None and not top.empty:
                for _, row in top.head(10).iterrows():
                    results.append({
                        "source": "Google Trends",
                        "title": row["query"],
                        "url": f"https://trends.google.com/trends/explore?q={row['query'].replace(' ', '+')}&geo={geo}",
                        "score": int(row["value"]),
                        "comments": 0,
                        "subreddit": "",
                        "thumbnail": "",
                    })
        return results
    except Exception:
        return []


def get_trending_topics(geo: str = "") -> List[Dict]:
    """Get currently trending topics (no niche needed)."""
    results = []
    try:
        pytrends = TrendReq(hl="pt-BR", tz=360)
        # Map geo code to pytrends country name
        if geo.startswith("BR"):
            country = "brazil"
        elif not geo:
            country = "united_states"
        else:
            country = geo.lower()

        trending = pytrends.trending_searches(pn=country)
        for i, topic in enumerate(trending[0].tolist()[:15]):
            results.append({
                "source": "Google Trends",
                "title": topic,
                "url": f"https://trends.google.com/trends/explore?q={topic.replace(' ', '+')}&geo={geo}",
                "score": 100 - i * 5,
                "comments": 0,
                "subreddit": "",
                "thumbnail": "",
            })
    except Exception:
        pass
    return results[:15]
