from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, set_key, dotenv_values
import asyncio
import json
import os
import re
from pathlib import Path
from typing import List, Dict

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

from scrapers.reddit import search_reddit, get_trending_reddit
from scrapers.hackernews import search_hackernews, get_top_hackernews
from scrapers.trends import get_related_trends, get_trending_topics
from scrapers.youtube import search_youtube, get_trending_youtube
from scrapers.pw_twitter import search_twitter
from scrapers.pw_tiktok import search_tiktok
from scrapers.pw_linkedin import search_linkedin
from scrapers.facebook import search_facebook
from scrapers.pw_instagram import search_instagram
from scrapers.pw_threads import search_threads
from scrapers.news import get_city_news, search_news

app = FastAPI(title="Viral Content Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALL_SOURCES = ["reddit", "hackernews", "trends", "youtube", "twitter", "tiktok", "linkedin", "facebook", "instagram", "threads"]

SCRAPER_MAP = {
    "reddit":     search_reddit,
    "hackernews": search_hackernews,
    "youtube":    search_youtube,
    "twitter":    search_twitter,
    "tiktok":     search_tiktok,
    "linkedin":   search_linkedin,
    "facebook":   search_facebook,
    "instagram":  search_instagram,
    "threads":    search_threads,
}

# ── City map for Brazilian cities ──
# Fields: geo (Google Trends), subreddit, display (pretty name), state (2-letter for news search)
CITY_MAP = {
    "manaus":          {"geo": "BR-AM", "subreddit": "manaus",       "display": "Manaus",          "state": "AM"},
    "sao paulo":       {"geo": "BR-SP", "subreddit": "saopaulo",     "display": "São Paulo",       "state": "SP"},
    "são paulo":       {"geo": "BR-SP", "subreddit": "saopaulo",     "display": "São Paulo",       "state": "SP"},
    "rio de janeiro":  {"geo": "BR-RJ", "subreddit": "riodejaneiro", "display": "Rio de Janeiro",  "state": "RJ"},
    "rio":             {"geo": "BR-RJ", "subreddit": "riodejaneiro", "display": "Rio de Janeiro",  "state": "RJ"},
    "brasilia":        {"geo": "BR-DF", "subreddit": "brasilia",     "display": "Brasília",        "state": "DF"},
    "brasília":        {"geo": "BR-DF", "subreddit": "brasilia",     "display": "Brasília",        "state": "DF"},
    "curitiba":        {"geo": "BR-PR", "subreddit": "curitiba",     "display": "Curitiba",        "state": "PR"},
    "porto alegre":    {"geo": "BR-RS", "subreddit": "portealegre",  "display": "Porto Alegre",    "state": "RS"},
    "salvador":        {"geo": "BR-BA", "subreddit": "salvador",     "display": "Salvador",        "state": "BA"},
    "fortaleza":       {"geo": "BR-CE", "subreddit": "fortaleza",    "display": "Fortaleza",       "state": "CE"},
    "belo horizonte":  {"geo": "BR-MG", "subreddit": "BeloHorizonte","display": "Belo Horizonte",  "state": "MG"},
    "bh":              {"geo": "BR-MG", "subreddit": "BeloHorizonte","display": "Belo Horizonte",  "state": "MG"},
    "recife":          {"geo": "BR-PE", "subreddit": "recife",       "display": "Recife",          "state": "PE"},
    "belem":           {"geo": "BR-PA", "subreddit": "Belem",        "display": "Belém",           "state": "PA"},
    "belém":           {"geo": "BR-PA", "subreddit": "Belem",        "display": "Belém",           "state": "PA"},
    "goiania":         {"geo": "BR-GO", "subreddit": "goiania",      "display": "Goiânia",         "state": "GO"},
    "goiânia":         {"geo": "BR-GO", "subreddit": "goiania",      "display": "Goiânia",         "state": "GO"},
    "florianopolis":   {"geo": "BR-SC", "subreddit": "Floripa",      "display": "Florianópolis",   "state": "SC"},
    "florianópolis":   {"geo": "BR-SC", "subreddit": "Floripa",      "display": "Florianópolis",   "state": "SC"},
    "floripa":         {"geo": "BR-SC", "subreddit": "Floripa",      "display": "Florianópolis",   "state": "SC"},
    "natal":           {"geo": "BR-RN", "subreddit": "natal",        "display": "Natal",           "state": "RN"},
    "maceio":          {"geo": "BR-AL", "subreddit": "maceio",       "display": "Maceió",          "state": "AL"},
    "maceió":          {"geo": "BR-AL", "subreddit": "maceio",       "display": "Maceió",          "state": "AL"},
    "vitoria":         {"geo": "BR-ES", "subreddit": "vitoria",      "display": "Vitória",         "state": "ES"},
    "vitória":         {"geo": "BR-ES", "subreddit": "vitoria",      "display": "Vitória",         "state": "ES"},
    "campo grande":    {"geo": "BR-MS", "subreddit": "campogrande",  "display": "Campo Grande",    "state": "MS"},
    "joao pessoa":     {"geo": "BR-PB", "subreddit": "joaopessoa",   "display": "João Pessoa",     "state": "PB"},
    "joão pessoa":     {"geo": "BR-PB", "subreddit": "joaopessoa",   "display": "João Pessoa",     "state": "PB"},
    "teresina":        {"geo": "BR-PI", "subreddit": "teresina",     "display": "Teresina",        "state": "PI"},
    "porto velho":     {"geo": "BR-RO", "subreddit": "brasil",       "display": "Porto Velho",     "state": "RO"},
    "macapa":          {"geo": "BR-AP", "subreddit": "brasil",       "display": "Macapá",          "state": "AP"},
    "macapá":          {"geo": "BR-AP", "subreddit": "brasil",       "display": "Macapá",          "state": "AP"},
    "boa vista":       {"geo": "BR-RR", "subreddit": "brasil",       "display": "Boa Vista",       "state": "RR"},
    "palmas":          {"geo": "BR-TO", "subreddit": "brasil",       "display": "Palmas",          "state": "TO"},
    "aracaju":         {"geo": "BR-SE", "subreddit": "brasil",       "display": "Aracaju",         "state": "SE"},
    "cuiaba":          {"geo": "BR-MT", "subreddit": "brasil",       "display": "Cuiabá",          "state": "MT"},
    "cuiabá":          {"geo": "BR-MT", "subreddit": "brasil",       "display": "Cuiabá",          "state": "MT"},
    "rio branco":      {"geo": "BR-AC", "subreddit": "brasil",       "display": "Rio Branco",      "state": "AC"},
    "sao luis":        {"geo": "BR-MA", "subreddit": "brasil",       "display": "São Luís",        "state": "MA"},
    "são luís":        {"geo": "BR-MA", "subreddit": "brasil",       "display": "São Luís",        "state": "MA"},
    "campinas":        {"geo": "BR-SP", "subreddit": "campinas",     "display": "Campinas",        "state": "SP"},
    "santos":          {"geo": "BR-SP", "subreddit": "brasil",       "display": "Santos",          "state": "SP"},
    "ribeirao preto":  {"geo": "BR-SP", "subreddit": "brasil",       "display": "Ribeirão Preto",  "state": "SP"},
    "uberlandia":      {"geo": "BR-MG", "subreddit": "brasil",       "display": "Uberlândia",      "state": "MG"},
    "londrina":        {"geo": "BR-PR", "subreddit": "brasil",       "display": "Londrina",        "state": "PR"},
}

_STOPWORDS = {
    'the', 'and', 'for', 'are', 'was', 'with', 'this', 'that', 'from', 'have',
    'uma', 'para', 'que', 'com', 'como', 'mais', 'por', 'não', 'mas', 'seu',
    'sua', 'ser', 'isso', 'esse', 'esta', 'nos', 'nas', 'dos', 'das', 'has',
    'will', 'been', 'they', 'what', 'when', 'than', 'but', 'its', 'como',
    'video', 'vídeo', 'post', 'best', 'most', 'mais', 'top', 'hoje',
}


def _extract_keywords(title: str) -> set:
    words = re.findall(r'\b\w{3,}\b', title.lower())
    return {w for w in words if w not in _STOPWORDS}


def calculate_virality(results: List[Dict]) -> List[Dict]:
    """Score each result by how many different sources mention similar content.

    Uses a shared keyword pool from Google Trends (single-word queries) as a
    signal amplifier: if a Trends keyword appears in another source's title,
    that source gets a virality boost even with just 1 matching word.
    """
    keyword_sets = [_extract_keywords(r.get("title", "")) for r in results]

    # Build a set of all keywords that appear in Google Trends results
    trends_keywords: set = set()
    for i, item in enumerate(results):
        if item["source"] == "Google Trends":
            trends_keywords |= keyword_sets[i]

    for i, item in enumerate(results):
        if not keyword_sets[i]:
            item["virality_count"] = 1
            continue

        matching_sources = {item["source"]}
        for j, other in enumerate(results):
            if i == j or other["source"] == item["source"]:
                continue

            overlap = keyword_sets[i] & keyword_sets[j]
            # Regular cross-source match: 2+ shared keywords
            if len(overlap) >= 2:
                matching_sources.add(other["source"])
            # Trends-boosted match: 1 shared keyword that is also in Trends
            elif len(overlap) >= 1 and overlap & trends_keywords:
                matching_sources.add(other["source"])

        item["virality_count"] = len(matching_sources)

    return results


@app.get("/api/search")
async def search(
    niche: str = Query(..., description="Nicho para buscar"),
    sources: str = Query(",".join(ALL_SOURCES), description="Fontes separadas por vírgula"),
    limit: int = Query(10, ge=1, le=50)
):
    source_list = [s.strip() for s in sources.split(",") if s.strip() in ALL_SOURCES]

    async def run_trends():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_related_trends, niche)

    tasks = {}
    for src in source_list:
        if src == "trends":
            tasks[src] = run_trends()
        elif src in SCRAPER_MAP:
            tasks[src] = SCRAPER_MAP[src](niche, limit)

    results_per_source = await asyncio.gather(*tasks.values(), return_exceptions=True)
    source_keys = list(tasks.keys())

    all_results = []
    config_notices = []

    for key, res in zip(source_keys, results_per_source):
        if isinstance(res, Exception):
            continue
        for item in res:
            if item.get("_config_needed"):
                config_notices.append(item)
            else:
                all_results.append(item)

    all_results = calculate_virality(all_results)
    all_results.sort(key=lambda x: (x.get("virality_count", 1), x["score"]), reverse=True)

    return {
        "niche": niche,
        "total": len(all_results),
        "results": all_results,
        "config_needed": config_notices,
    }


@app.get("/api/trending")
async def trending(
    scope: str = Query("mundo", description="mundo | pais | cidade"),
    city: str = Query("", description="City name for 'cidade' scope"),
    limit: int = Query(15, ge=5, le=50),
):
    geo = ""
    reddit_subs = ["all", "popular", "worldnews"]
    yt_region = "US"
    include_hn = True
    city_display_name = ""
    city_state = ""
    is_city = False

    if scope == "pais":
        geo = "BR"
        reddit_subs = ["brasil", "brdev", "futebol", "investimentos", "huestation"]
        yt_region = "BR"
        include_hn = False

    elif scope == "cidade":
        city_key = city.lower().strip()
        city_info = CITY_MAP.get(city_key, {})
        geo = city_info.get("geo", "BR")
        sub = city_info.get("subreddit", "brasil")
        city_display_name = city_info.get("display", city.title())
        city_state = city_info.get("state", "BR")
        reddit_subs = [sub, "brasil"]
        yt_region = "BR"
        include_hn = False
        is_city = True

    # Run all trending sources in parallel
    async def run_trends_topic():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_trending_topics, geo)

    gather_tasks = [
        run_trends_topic(),
        get_trending_reddit(reddit_subs, limit),
        get_trending_youtube(yt_region, limit, city=city_display_name if is_city else ""),
    ]
    if include_hn:
        gather_tasks.append(get_top_hackernews(limit))
    if is_city and city_display_name:
        gather_tasks.append(get_city_news(city_display_name, city_state, limit))
    elif scope == "pais":
        gather_tasks.append(search_news("Brasil notícias", limit))

    results_list = await asyncio.gather(*gather_tasks, return_exceptions=True)

    all_results = []
    for res in results_list:
        if isinstance(res, Exception):
            continue
        all_results.extend(res)

    all_results = calculate_virality(all_results)
    all_results.sort(key=lambda x: (x.get("virality_count", 1), x["score"]), reverse=True)

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for r in all_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique.append(r)

    return {
        "scope": scope,
        "city": city_display_name or (city.title() if city else ""),
        "geo": geo,
        "total": len(unique),
        "results": unique,
    }


@app.get("/api/sources")
async def list_sources():
    configured = []
    needs_config = []
    for src in ALL_SOURCES:
        if src in ["reddit", "hackernews", "trends", "youtube"]:
            configured.append(src)
        else:
            needs_config.append(src)
    return {"configured": configured, "needs_config": needs_config}


ALLOWED_KEYS = {
    # API keys legadas
    "TWITTER_BEARER_TOKEN",
    "TIKTOK_CLIENT_KEY",
    "TIKTOK_CLIENT_SECRET",
    "LINKEDIN_ACCESS_TOKEN",
    "FACEBOOK_ACCESS_TOKEN",
    "YOUTUBE_API_KEY",
    "GOOGLE_API_KEY",
    # Credenciais Playwright
    "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
    "TIKTOK_EMAIL", "TIKTOK_PASSWORD",
    "TWITTER_EMAIL", "TWITTER_PASSWORD",
    "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
    "THREADS_EMAIL", "THREADS_PASSWORD",
}


@app.post("/api/analyze")
async def analyze(request: Request):
    data = await request.json()
    results = data.get("results", [])[:15]
    niche = data.get("niche", "")

    loop = asyncio.get_event_loop()

    from deep_translator import GoogleTranslator

    def translate_all():
        translator = GoogleTranslator(source="auto", target="pt")
        out = []
        for i, r in enumerate(results):
            title = r.get("title", "")
            try:
                translated = translator.translate(title[:450]) or title
            except Exception:
                translated = title
            out.append({"index": i, "text": translated})
        return out

    translations = await loop.run_in_executor(None, translate_all)

    posts_text = "\n".join([
        f'{i+1}. {t["text"][:150]}'
        for i, t in enumerate(translations[:10])
    ])

    prompt = (
        f'Você é um estrategista de conteúdo digital especialista em marketing viral. '
        f'Com base nesses posts virais sobre "{niche}", analise e responda APENAS com JSON válido, sem markdown:\n'
        f'{{"resumo":"1 frase resumindo a tendência atual do nicho",'
        f'"ideas":["escreva a ideia 1 aqui (1-2 frases completas)","escreva a ideia 2 aqui (1-2 frases completas)","escreva a ideia 3 aqui (1-2 frases completas)"],'
        f'"hashtags":["#tag1","#tag2","#tag3","#tag4","#tag5"],'
        f'"formato":"Reels|Carrossel|Thread|Post|Live",'
        f'"titulo":"Um título viral chamativo para um post sobre este nicho"}}\n\n'
        f'Posts:\n{posts_text}'
    )

    ideas = []
    resumo = ""
    hashtags = []
    formato = ""
    titulo = ""

    def _parse_ai_response(text: str) -> dict:
        text = text.strip()
        # Remove markdown code fences if present
        if "```" in text:
            text = text.split("```")[1] if "```" in text else text
            if text.startswith("json"):
                text = text[4:]
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        return {}

    # 1. Tenta Ollama local (qwen2.5-coder:7b)
    try:
        import ollama as _ollama

        def call_ollama():
            response = _ollama.chat(
                model="qwen2.5-coder:7b",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.message.content

        text = await loop.run_in_executor(None, call_ollama)
        parsed = _parse_ai_response(text)
        ideas    = parsed.get("ideas", [])
        resumo   = parsed.get("resumo", "")
        hashtags = parsed.get("hashtags", [])
        formato  = parsed.get("formato", "")
        titulo   = parsed.get("titulo", "")
    except Exception:
        ideas = []

    # 2. Fallback: Gemini
    if not ideas:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if api_key:
            try:
                from google import genai

                def call_gemini():
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                    )
                    return response.text

                text = await loop.run_in_executor(None, call_gemini)
                parsed = _parse_ai_response(text)
                ideas    = parsed.get("ideas", [])
                resumo   = parsed.get("resumo", "")
                hashtags = parsed.get("hashtags", [])
                formato  = parsed.get("formato", "")
                titulo   = parsed.get("titulo", "")
            except Exception:
                ideas = []

    # 3. Fallback final: templates
    if not ideas:
        top = [t["text"] for t in translations[:5]]
        templates = [
            f'Vídeo curto mostrando "{top[0][:70]}" — explique em 60 segundos com exemplos práticos.' if len(top) > 0 else "",
            f'Carrossel com 5 dicas baseado em "{top[1][:70]}" — inclua dados reais e chamada para ação.' if len(top) > 1 else "",
            f'Thread ou post de opinião sobre "{top[2][:70]}" — compartilhe sua visão e provoque debate.' if len(top) > 2 else "",
        ]
        ideas = [t for t in templates if t]

    return {
        "translations": translations,
        "ideas": ideas,
        "resumo": resumo,
        "hashtags": hashtags,
        "formato": formato,
        "titulo": titulo,
    }


@app.get("/api/config/get")
async def config_get():
    values = dotenv_values(ENV_PATH)
    return {k: v for k, v in values.items() if k in ALLOWED_KEYS and v}


@app.post("/api/config/save")
async def config_save(request: Request):
    data = await request.json()
    for key, value in data.items():
        if key not in ALLOWED_KEYS:
            raise HTTPException(status_code=400, detail=f"Chave inválida: {key}")
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value
    return {"status": "ok", "saved": list(data.keys())}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
