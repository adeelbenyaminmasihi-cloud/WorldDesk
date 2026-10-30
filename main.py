import os
import re
import time
import json
import random
import asyncio
import subprocess
import urllib.parse
import textwrap
import xml.etree.ElementTree as ET
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# Optional YouTube & Facebook Credentials
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

FB_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
FB_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

USED_TOPICS_FILE = "used_topics.json"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
USED_MEDIA_URLS = set()


def load_used_topics():
    if os.path.exists(USED_TOPICS_FILE):
        try:
            with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_used_topics(used_list):
    try:
        # Keep up to 1000 topics so nothing repeats
        with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(used_list[-1000:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [!] Could not save used topics: {e}")


def is_topic_duplicate(candidate, used_list):
    """Checks exact match or high word overlap so similar topics never repeat."""
    if not candidate:
        return True
    cand_clean = re.sub(r"[^a-z0-9\s]", "", candidate.lower()).strip()
    cand_words = {w for w in cand_clean.split() if len(w) > 3}
    for u in used_list:
        u_clean = re.sub(r"[^a-z0-9\s]", "", u.lower()).strip()
        if cand_clean == u_clean or cand_clean in u_clean or u_clean in cand_clean:
            return True
        u_words = {w for w in u_clean.split() if len(w) > 3}
        if cand_words and u_words:
            overlap = len(cand_words & u_words) / float(min(len(cand_words), len(u_words)))
            if overlap >= 0.7:
                return True
    return False


def fetch_live_world_news_headlines(used_topics):
    """Fetches real-time global headlines from Google News, BBC, and Al Jazeera RSS feeds and filters out used ones."""
    headlines = []
    rss_urls = [
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml"
    ]
    for url in rss_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:15]:
                    title_el = item.find("title")
                    if title_el is not None and title_el.text:
                        clean_title = title_el.text.split(" - ")[0].strip()
                        if len(clean_title) > 22 and clean_title not in headlines:
                            if not is_topic_duplicate(clean_title, used_topics):
                                headlines.append(clean_title)
        except Exception as e:
            print(f"  [!] RSS fetch note: {e}")

    random.shuffle(headlines)
    return headlines[:30]


def clean_and_parse_json(raw_text):
    """Safely extracts and parses JSON even if the AI wraps it in markdown or extra text."""
    if not raw_text:
        return None
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
    raw_text = re.sub(r"\s*```$", "", raw_text.strip())
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw_text = raw_text[start:end + 1]
    try:
        return json.loads(raw_text)
    except Exception:
        # Remove trailing commas before closing braces/brackets if present
        fixed = re.sub(r",\s*([\]}])", r"\1", raw_text)
        return json.loads(fixed)


def build_prompt(live_headlines, used_topics):
    chosen_headline = live_headlines[0] if live_headlines else "Global Geopolitics & Economic Shift"
    return f"""You are an elite international news producer creating a 2-minute (14-scene) video on a MAJOR CURRENT GLOBAL EVENT.

PRIMARY BREAKING NEWS TO COVER TODAY:
"{chosen_headline}"

Other live headlines for context (you may use the primary headline above or pick the most impactful one from this list):
{json.dumps(live_headlines[:12], ensure_ascii=False)}

CRITICAL RULE: You MUST NOT pick any topic already in this used list:
{json.dumps(used_topics[-80:], ensure_ascii=False)}

Return ONLY a raw, valid JSON object with NO markdown formatting and NO code fences, matching this EXACT schema:
{{
  "topic": "Unique specific English headline/topic title (must not match used list)",
  "title": "🌍 Catchy Roman Urdu Title | Global Update",
  "tagline": "Engaging 1-line Roman Urdu hook with emojis",
  "description": "2-3 sentence Roman Urdu summary of the global event and why it matters.",
  "hashtags": "#GlobalAffairs #WorldNews #Geopolitics #UrduNews #CurrentEvents #Viral",
  "category_badge": "SHORT 2-3 WORD ENGLISH BADGE",
  "scenes": [
    {{
      "tts_urdu": "Must be written in REAL URDU SCRIPT (اردو رسم الخط) around 20 to 26 words so TTS speaks naturally for ~8.5 seconds.",
      "caption_part1": "SHORT UPPERCASE ROMAN URDU LINE 1 (MAX 24 CHARS)",
      "caption_part2": "SHORT UPPERCASE ROMAN URDU LINE 2 (MAX 24 CHARS)",
      "search_query_1": "2-3 word English stock photo keyword",
      "search_query_2": "2-3 word English stock photo keyword",
      "video_query": "2 word English stock video keyword (or empty string)"
    }}
  ]
}}
Ensure the `scenes` array has EXACTLY 14 scenes."""


def discover_gemini_models():
    """Returns a prioritized list of working Gemini models for this API key."""
    default_models = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash"
    ]
    if not GEMINI_API_KEY:
        return []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            models = r.json().get("models", [])
            capable = [
                m.get("name", "") for m in models
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "gemini" in m.get("name", "").lower()
                and "tts" not in m.get("name", "").lower()
                and "image" not in m.get("name", "").lower()
            ]
            ordered = [m for m in default_models if m in capable]
            for c in capable:
                if c not in ordered and "flash" in c:
                    ordered.append(c)
            return ordered if ordered else default_models
    except Exception as e:
        print(f"  [!] Gemini model discovery note: {e}")
    return default_models


def generate_script_via_gemini(live_headlines, used_topics):
    """Tries multiple Gemini models with 8192 maxOutputTokens so JSON never truncates."""
    if not GEMINI_API_KEY:
        print("  [!] GEMINI_API_KEY is empty. Moving to free AI fallback...")
        return None

    models_to_try = discover_gemini_models()
    prompt = build_prompt(live_headlines, used_topics)

    for model_name in models_to_try:
        print(f"🧠 Attempting 2-Minute Script via {model_name}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json"
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code != 200:
                payload["generationConfig"].pop("responseMimeType", None)
                resp = requests.post(url, json=payload, timeout=60)

            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    script_data = clean_and_parse_json(raw_text)
                    if script_data and script_data.get("topic") and len(script_data.get("scenes", [])) >= 10:
                        if not is_topic_duplicate(script_data["topic"], used_topics):
                            print(f"  [✓] Gemini generated fresh script: {script_data['topic']}")
                            return script_data
                        else:
                            print(f"  [!] Gemini picked a duplicate topic ({script_data['topic']}), retrying...")
            else:
                print(f"  [!] {model_name} HTTP {resp.status_code}: {resp.text[:160]}")
        except Exception as e:
            print(f"  [!] {model_name} exception: {e}")
        time.sleep(2)

    return None


def generate_script_via_pollinations(live_headlines, used_topics):
    """Zero-API-key free AI fallback using Pollinations OpenAI endpoint + live RSS news."""
    print("🌐 Attempting Free AI Script Generation via Pollinations OpenAI API...")
    prompt = build_prompt(live_headlines, used_topics)

    for attempt in range(2):
        try:
            resp = requests.post(
                "https://text.pollinations.ai/openai",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "openai",
                    "messages": [
                        {"role": "system", "content": "You are an expert Urdu news scriptwriter. Output strictly valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.8,
                    "seed": random.randint(1, 999999)
                },
                timeout=75
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                script_data = clean_and_parse_json(raw_text)
                if script_data and script_data.get("topic") and len(script_data.get("scenes", [])) >= 10:
                    if not is_topic_duplicate(script_data["topic"], used_topics):
                        print(f"  [✓] Pollinations AI generated fresh script: {script_data['topic']}")
                        return script_data
        except Exception as e:
            print(f"  [!] Pollinations AI attempt {attempt + 1} note: {e}")
        time.sleep(2)

    return None


def build_dynamic_live_news_fallback(live_headlines, used_topics):
    """If all AI APIs are unreachable, dynamically converts a fresh unused RSS headline into a unique script."""
    fresh_headline = None
    for h in live_headlines:
        if not is_topic_duplicate(h, used_topics):
            fresh_headline = h
            break
    if not fresh_headline:
        fresh_headline = f"Global Geopolitical & Economic Shift Update {int(time.time())}"

    words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", "", fresh_headline).split() if len(w) > 3]
    kw1 = " ".join(words[:2]) if len(words) >= 2 else "world news"
    kw2 = " ".join(words[2:4]) if len(words) >= 4 else "global geopolitics"
    short_upper = " ".join(words[:3]).upper()[:22] if words else "BREAKING WORLD NEWS"

    print(f"📰 Building Dynamic Live-Headline Script for: {fresh_headline}")
    return {
        "topic": fresh_headline,
        "title": f"🌍 {fresh_headline[:65]} | Global Update",
        "tagline": f"Breaking Global Update: {fresh_headline} 🌍⚡",
        "description": f"Alami media mein is waqt ki badi khabar: {fresh_headline}. Janiye is waqiye ka duniya aur global economy par mukammal asar.",
        "hashtags": "#GlobalAffairs #WorldNews #BreakingNews #Geopolitics #UrduNews #GlobalUpdate",
        "category_badge": "BREAKING NEWS",
        "scenes": [
            {
                "tts_urdu": "عالمی میڈیا اور بین الاقوامی خبروں میں اس وقت ایک انتہائی اہم پیشرفت سامنے آ رہی ہے جس نے پوری دنیا کی توجہ اپنی طرف کھینچ لی ہے!",
                "caption_part1": "INTERNATIONAL BREAKING:",
                "caption_part2": short_upper,
                "search_query_1": kw1,
                "search_query_2": kw2,
                "video_query": kw1
            },
            {
                "tts_urdu": "اس نئے عالمی واقعے کے بعد بڑی طاقتوں کے درمیان سفارتی اور معاشی سطح پر ہنگامی رابطے اور اجلاس شروع ہو چکے ہیں۔",
                "caption_part1": "ALAMI TAQATON MEIN",
                "caption_part2": "HANGAMI DIPLOMACY SHURU!",
                "search_query_1": f"{kw1} summit",
                "search_query_2": "diplomatic meeting flags",
                "video_query": ""
            },
            {
                "tts_urdu": "ماہرین کے مطابق یہ معاملہ صرف ایک ملک تک محدود نہیں رہے گا بلکہ اس کے اثرات پورے خطے اور عالمی سپلائی چین پر مرتب ہوں گے۔",
                "caption_part1": "POORE KHITTE AUR",
                "caption_part2": "GLOBAL TRADE PAR ASAR!",
                "search_query_1": kw2,
                "search_query_2": "global trade network",
                "video_query": ""
            },
            {
                "tts_urdu": "بین الاقوامی خبر رساں اداروں کی تازہ ترین رپورٹس بتاتی ہیں کہ آنے والے چند دن اس بحران اور پالیسی کے حوالے سے انتہائی فیصلہ کن ثابت ہوں گے۔",
                "caption_part1": "TAZA TAREEN REPORTS:",
                "caption_part2": "FAISLA KUN MARHALA!",
                "search_query_1": "breaking news broadcast",
                "search_query_2": kw1,
                "video_query": "world news"
            },
            {
                "tts_urdu": "عالمی منڈیوں، سٹاک ایکسچینج اور توانائی کی قیمتوں میں بھی اس خبر کے بعد واضح ہلچل اور اتار چڑھاؤ دیکھا جا رہا ہے۔",
                "caption_part1": "GLOBAL MARKETS MEIN",
                "caption_part2": "TEZ UTAAR CHARHAO!",
                "search_query_1": "stock market trading screen",
                "search_query_2": "financial graph analysis",
                "video_query": ""
            },
            {
                "tts_urdu": "سیاسی اور دفاعی تجزیہ کاروں کا ماننا ہے کہ بڑی طاقتیں اب اپنے مفادات کے تحفظ کے لیے نئی حکمت عملی تیار کر رہی ہیں۔",
                "caption_part1": "DEFENSE AUR POLITICS:",
                "caption_part2": "NAYI STRATEGY TAYYAR!",
                "search_query_1": kw2,
                "search_query_2": "geopolitics map strategy",
                "video_query": kw2
            },
            {
                "tts_urdu": "جب بھی عالمی سطح پر ایسی بڑی تبدیلی آتی ہے تو ترقی پذیر ممالک کی معیشت اور عام شہریوں کی روزمرہ زندگی پر اس کا سیدھا اثر پڑتا ہے۔",
                "caption_part1": "DEVELOPING COUNTRIES:",
                "caption_part2": "AAM AADMI PAR ASAR!",
                "search_query_1": "busy city street people",
                "search_query_2": "economy inflation shopping",
                "video_query": ""
            },
            {
                "tts_urdu": "اقوام متحدہ اور دیگر عالمی اداروں میں بھی اس موضوع پر گہری تشویش اور مختلف ممالک کے درمیان سخت بیانات کا سلسلہ جاری ہے۔",
                "caption_part1": "UNITED NATIONS AUR",
                "caption_part2": "ALAMI IDARON KA MOQAF!",
                "search_query_1": "united nations assembly",
                "search_query_2": "press conference podium",
                "video_query": ""
            },
            {
                "tts_urdu": "جدید ٹیکنالوجی، معلومات کی جنگ اور معاشی پابندیوں کے اس دور میں ہر ملک اپنی پوزیشن مضبوط کرنے کی کوشش کر رہا ہے۔",
                "caption_part1": "TECH AUR ECONOMY:",
                "caption_part2": "HAR MULK KI NAYI DOUR!",
                "search_query_1": "modern technology server",
                "search_query_2": "central bank building",
                "video_query": "technology"
            },
            {
                "tts_urdu": "اعداد و شمار واضح کرتے ہیں کہ پچھلے چند ہفتوں کے واقعات نے عالمی سیاست کا رخ ایک نئی سمت میں موڑ دیا ہے۔",
                "caption_part1": "ALAMI SIYASAT KA RUKH:",
                "caption_part2": "NAYI SIMT MEIN SAFAR!",
                "search_query_1": "data analytics screen",
                "search_query_2": kw1,
                "video_query": ""
            },
            {
                "tts_urdu": "آنے والے ہفتوں میں ہونے والے بین الاقوامی مذاکرات اور فیصلے طے کریں گے کہ یہ معاملہ امن کی طرف جاتا ہے یا مزید کشیدگی کی طرف۔",
                "caption_part1": "AANE WALE HAFTE:",
                "caption_part2": "AMAN YA MAZEED KASHIDGI?",
                "search_query_1": "world leaders handshake",
                "search_query_2": kw2,
                "video_query": ""
            },
            {
                "tts_urdu": "پاکستان اور خطے کے دیگر ممالک کے لیے بھی ضروری ہے کہ وہ ان عالمی حالات پر گہری نظر رکھیں اور بروقت معاشی و سفارتی اقدامات کریں۔",
                "caption_part1": "KHITTE KE MUMALIK:",
                "caption_part2": "BARWAQT FAISLON KI ZAROORAT!",
                "search_query_1": "modern city skyline",
                "search_query_2": "government parliament building",
                "video_query": ""
            },
            {
                "tts_urdu": "تاریخ گواہ ہے کہ جو قومیں عالمی تبدیلیوں کو وقت پر سمجھ لیتی ہیں وہی ہر بحران سے محفوظ رہ کر آگے بڑھتی ہیں۔",
                "caption_part1": "TAREEKH KA SABQ:",
                "caption_part2": "WAQT PAR SAMajhna LAZMI!",
                "search_query_1": "earth from space glowing",
                "search_query_2": "futuristic city highway",
                "video_query": ""
            },
            {
                "tts_urdu": "دنیا بھر کی تازہ ترین خبروں، جیو پولیٹکس اور گلوبل افیئرز کا روزانہ مستند تجزیہ دیکھنے کے لیے ہمارے چینل کو ابھی فالو اور سبسکرائب کریں!",
                "caption_part1": "DAILY GLOBAL UPDATES:",
                "caption_part2": "ABHI SUBSCRIBE KAREIN!",
                "search_query_1": "smartphone notification news",
                "search_query_2": "television news studio",
                "video_query": ""
            }
        ]
    }


def generate_script_data():
    used = load_used_topics()
    live_headlines = fetch_live_world_news_headlines(used)
    print(f"📡 Fetched {len(live_headlines)} fresh unused global news headlines.")

    # Tier 1: Live Gemini API + RSS Headlines
    ai_script = generate_script_via_gemini(live_headlines, used)
    if ai_script:
        used.append(ai_script["topic"])
        save_used_topics(used)
        return ai_script

    # Tier 2: Free Pollinations OpenAI API + RSS Headlines (Zero API key required)
    poll_script = generate_script_via_pollinations(live_headlines, used)
    if poll_script:
        used.append(poll_script["topic"])
        save_used_topics(used)
        return poll_script

    # Tier 3: Dynamic Live-Headline Script Builder (Never resets `used` or repeats static topics)
    dyn_script = build_dynamic_live_news_fallback(live_headlines, used)
    used.append(dyn_script["topic"])
    save_used_topics(used)
    return dyn_script


def fetch_contextual_stock_video(query, filename):
    """Fetches HD Stock Video using Official PIXABAY_API_KEY first, then Mixkit fallback."""
    if not query:
        return None

    if PIXABAY_API_KEY:
        try:
            encoded = urllib.parse.quote(query.strip())
            p_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={encoded}&safesearch=true&per_page=15"
            r = requests.get(p_url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                hits = r.json().get("hits", [])
                for hit in hits:
                    videos = hit.get("videos", {})
                    vid_url = (
                        videos.get("medium", {}).get("url")
                        or videos.get("small", {}).get("url")
                        or videos.get("large", {}).get("url")
                    )
                    if vid_url and vid_url not in USED_MEDIA_URLS:
                        USED_MEDIA_URLS.add(vid_url)
                        vr = requests.get(vid_url, headers=HEADERS, timeout=30)
                        if vr.status_code == 200 and len(vr.content) > 50000:
                            with open(filename, "wb") as f:
                                f.write(vr.content)
                            print(f"  [✓] Pixabay Stock Video downloaded for '{query}'")
                            return filename
        except Exception as e:
            print(f"  [!] Pixabay video skip ({query}): {e}")

    slug = urllib.parse.quote(query.lower().strip())
    search_url = f"https://mixkit.co/free-stock-video/{slug}/"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=18)
        if resp.status_code == 200:
            pattern = r'https://assets\.mixkit\.co/videos/[^\s"\'<>]+\.mp4'
            mp4_urls = re.findall(pattern, resp.text)
            fresh_urls = [u for u in mp4_urls if u not in USED_MEDIA_URLS]
            if fresh_urls:
                chosen_url = fresh_urls[0]
                USED_MEDIA_URLS.add(chosen_url)
                vid_resp = requests.get(chosen_url, headers=HEADERS, timeout=25)
                if vid_resp.status_code == 200 and len(vid_resp.content) > 50000:
                    with open(filename, "wb") as f:
                        f.write(vid_resp.content)
                    print(f"  [✓] Mixkit Stock Video downloaded for '{query}'")
                    return filename
    except Exception:
        pass
    return None


def verify_and_grade_image(filepath):
    try:
        with Image.open(filepath) as im:
            im = im.convert("RGB")
            w, h = im.size
            if w < 220 or h < 220:
                return False
            im = ImageEnhance.Contrast(im).enhance(1.14)
            im = ImageEnhance.Color(im).enhance(1.18)
            im.save(filepath, "JPEG", quality=93)
        return True
    except Exception:
        return False


def fetch_exact_scene_photo(query, filename):
    """Fetches HD Stock Photo using Official PIXABAY_API_KEY first, then Bing HD fallback."""
    if PIXABAY_API_KEY:
        try:
            encoded = urllib.parse.quote(query.strip())
            p_url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={encoded}&image_type=photo&safesearch=true&per_page=15"
            r = requests.get(p_url, headers=HEADERS, timeout=18)
            if r.status_code == 200:
                hits = r.json().get("hits", [])
                for hit in hits:
                    img_url = hit.get("largeImageURL") or hit.get("webformatURL")
                    if img_url and img_url not in USED_MEDIA_URLS:
                        USED_MEDIA_URLS.add(img_url)
                        img_r = requests.get(img_url, headers=HEADERS, timeout=15)
                        if img_r.status_code == 200 and len(img_r.content) > 15000:
                            with open(filename, "wb") as f:
                                f.write(img_r.content)
                            if verify_and_grade_image(filename):
                                print(f"  [✓] Pixabay HD Photo downloaded for '{query}'")
                                return filename
        except Exception as e:
            print(f"  [!] Pixabay photo skip ({query}): {e}")

    try:
        encoded = urllib.parse.quote(f"{query} realistic photo")
        b_url = f"https://www.bing.com/images/async?q={encoded}&first=1&count=15&adlt=off&qft=+filterui:imagesize-large"
        r = requests.get(b_url, headers=HEADERS, timeout=18)
        if r.status_code == 200:
            urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&quot;', r.text)
            fresh = [u for u in urls if u not in USED_MEDIA_URLS]
            for img_url in fresh[:5]:
                try:
                    USED_MEDIA_URLS.add(img_url)
                    img_r = requests.get(img_url, headers=HEADERS, timeout=12)
                    if img_r.status_code == 200 and len(img_r.content) > 18000:
                        with open(filename, "wb") as f:
                            f.write(img_r.content)
                        if verify_and_grade_image(filename):
                            print(f"  [✓] Bing HD Photo downloaded for '{query}'")
                            return filename
                except Exception:
                    continue
    except Exception:
        pass

    img = Image.new("RGB", (1080, 1920), (22, 28, 42))
    img.save(filename, "JPEG", quality=92)
    return filename


def create_burned_hud_overlay(caption_text, badge_text, scene_idx, total_scenes, part_num):
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(280):
        alpha = int(170 * (1 - y / 280))
        draw.line([(0, y), (1080, y)], fill=(0, 0, 0, alpha))
    for y in range(1180, 1920):
        alpha = int(220 * ((y - 1180) / 740))
        draw.line([(0, y), (1080, y)], fill=(0, 0, 0, alpha))

    try:
        badge_font = ImageFont.truetype(FONT_BOLD, 38)
        cap_font = ImageFont.truetype(FONT_BOLD, 64)
    except Exception:
        badge_font = ImageFont.load_default()
        cap_font = ImageFont.load_default()

    bw, bh = 640, 82
    bx, by = (1080 - bw) // 2, 95
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=41, fill=(220, 30, 30, 250), outline=(255, 255, 255, 240), width=4)
    b_text = str(badge_text or "GLOBAL AFFAIRS").upper()[:24]
    b_bbox = draw.textbbox((0, 0), b_text, font=badge_font)
    b_tw, b_th = b_bbox[2] - b_bbox[0], b_bbox[3] - b_bbox[1]
    draw.text((bx + (bw - b_tw) // 2, by + (bh - b_th) // 2 - 4), b_text, font=badge_font, fill=(255, 255, 255, 255))

    lines = textwrap.wrap(str(caption_text or "GLOBAL UPDATE!").upper(), width=15)
    if not lines:
        lines = ["GLOBAL UPDATE!"]

    line_height = 92
    total_text_h = len(lines) * line_height
    box_y1 = 1360 - (total_text_h // 2)
    box_y2 = box_y1 + total_text_h + 44

    draw.rounded_rectangle([55, box_y1, 1025, box_y2], radius=28, fill=(10, 12, 18, 230), outline=(255, 215, 0, 220), width=4)

    for i, line in enumerate(lines):
        t_bbox = draw.textbbox((0, 0), line, font=cap_font)
        tw = t_bbox[2] - t_bbox[0]
        tx = (1080 - tw) // 2
        ty = box_y1 + 20 + (i * line_height)

        if part_num == 1:
            fill_col = (255, 230, 0, 255) if i == 0 else (255, 255, 255, 255)
        else:
            fill_col = (0, 255, 150, 255) if i == 0 else (255, 230, 0, 255)

        for dx, dy in [(-4, -4), (4, -4), (-4, 4), (4, 4), (0, 5)]:
            draw.text((tx + dx, ty + dy), line, font=cap_font, fill=(0, 0, 0, 255))
        draw.text((tx, ty), line, font=cap_font, fill=fill_col)

    progress_fraction = (scene_idx + (0.5 if part_num == 1 else 1.0)) / max(total_scenes, 1)
    prog_w = int(980 * progress_fraction)
    draw.rounded_rectangle([50, 1835, 1030, 1855], radius=10, fill=(255, 255, 255, 75))
    draw.rounded_rectangle([50, 1835, 50 + max(prog_w, 25), 1855], radius=10, fill=(255, 215, 0, 255))

    out_png = f"hud_{scene_idx}_p{part_num}.png"
    overlay.save(out_png)
    return out_png


async def synthesize_scene_voice(urdu_text, index):
    raw_audio = f"raw_voice_{index}.mp3"
    mastered_audio = f"voice_{index}.m4a"

    communicate = edge_tts.Communicate(urdu_text, voice="ur-PK-AsadNeural", rate="+8%", pitch="-2Hz")
    await communicate.save(raw_audio)

    af_chain = (
        "silenceremove=start_periods=1:start_silence=0.04:start_threshold=-45dB,"
        "highpass=f=75,"
        "bass=g=4:f=110,"
        "treble=g=3:f=4500,"
        "acompressor=threshold=-16dB:ratio=3:attack=5:release=60:makeup=3dB,"
        "apad=pad_dur=0.18"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_audio,
        "-af", af_chain,
        "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
        mastered_audio
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return mastered_audio


def get_audio_duration(audio_path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]).decode().strip()
    return max(float(out), 3.0)


def prepare_visual_subclip(media_path, is_video, overlay_path, duration, sub_idx, out_clip):
    if is_video:
        vf = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,eq=contrast=1.08:saturation=1.15[bg];"
            "[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-t", str(duration), "-i", media_path,
            "-loop", "1", "-t", str(duration), "-i", overlay_path,
            "-filter_complex", vf,
            "-map", "[v]", "-r", "24", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            out_clip
        ]
    else:
        direction = 1 if sub_idx % 2 == 0 else -1
        vf = (
            f"[0:v]scale=1240:2200:force_original_aspect_ratio=increase,crop=1240:2200,"
            f"crop=1080:1920:'(in_w-out_w)/2+({direction}*55)*sin(t*1.1)':'(in_h-out_h)/2+70*cos(t*0.8)'[bg];"
            f"[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration), "-i", media_path,
            "-loop", "1", "-t", str(duration), "-i", overlay_path,
            "-filter_complex", vf,
            "-map", "[v]", "-r", "24", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            out_clip
        ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        safe_vf = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
            "[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
        )
        safe_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration), "-i", media_path,
            "-loop", "1", "-t", str(duration), "-i", overlay_path,
            "-filter_complex", safe_vf,
            "-map", "[v]", "-r", "24", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            out_clip
        ]
        subprocess.run(safe_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_two_cut_scene(scene, idx, total_scenes, badge):
    audio_path = asyncio.run(synthesize_scene_voice(scene["tts_urdu"], idx))
    total_dur = get_audio_duration(audio_path)
    half_dur = round(total_dur / 2.0, 2)
    rem_dur = round(total_dur - half_dur, 2)

    q1 = scene.get("search_query_1", "world news")
    q2 = scene.get("search_query_2", "global economy")
    v_q = scene.get("video_query", "")

    vid_file = fetch_contextual_stock_video(v_q, f"stock_vid_{idx}.mp4") if v_q else None
    if vid_file:
        media1, is_vid1 = vid_file, True
    else:
        media1 = fetch_exact_scene_photo(q1, f"photo_{idx}_1.jpg")
        is_vid1 = False

    media2 = fetch_exact_scene_photo(q2, f"photo_{idx}_2.jpg")

    ov1 = create_burned_hud_overlay(scene.get("caption_part1", "GLOBAL NEWS"), badge, idx, total_scenes, 1)
    ov2 = create_burned_hud_overlay(scene.get("caption_part2", "WORLD UPDATE"), badge, idx, total_scenes, 2)

    sub1 = f"sub_{idx}_1.mp4"
    sub2 = f"sub_{idx}_2.mp4"
    prepare_visual_subclip(media1, is_vid1, ov1, half_dur, 0, sub1)
    prepare_visual_subclip(media2, False, ov2, rem_dur, 1, sub2)

    list_file = f"scene_list_{idx}.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        f.write(f"file '{sub1}'\nfile '{sub2}'\n")

    scene_out = f"scene_final_{idx}.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "copy", "-shortest",
        scene_out
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return scene_out


def build_full_video(script_data):
    scenes = script_data["scenes"]
    badge = script_data.get("category_badge", "GLOBAL AFFAIRS")
    scene_files = []

    for idx, scene in enumerate(scenes):
        print(f"🎬 Scene {idx+1}/{len(scenes)}: '{scene.get('caption_part1')} | {scene.get('caption_part2')}'")
        s_file = render_two_cut_scene(scene, idx, len(scenes), badge)
        scene_files.append(s_file)

    with open("master_concat.txt", "w", encoding="utf-8") as f:
        for sf in scene_files:
            f.write(f"file '{sf}'\n")

    raw_output = "raw_reel.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "master_concat.txt",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-maxrate", "2500k", "-bufsize", "5000k",
        "-c:a", "aac", "-b:a", "192k",
        raw_output
    ], check=True)

    print("🎵 Mixing Cinematic Background Music...")
    final_output = "final_reel.mp4"
    bgm_url = "https://actions.google.com/sounds/v1/ambiences/cyberpunk_drone.ogg"
    try:
        bgm_resp = requests.get(bgm_url, headers=HEADERS, timeout=20)
        if bgm_resp.status_code == 200:
            with open("bgm.ogg", "wb") as f:
                f.write(bgm_resp.content)
            mix_cmd = [
                "ffmpeg", "-y",
                "-i", raw_output,
                "-stream_loop", "-1", "-i", "bgm.ogg",
                "-filter_complex", "[1:a]volume=0.09[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                final_output
            ]
            subprocess.run(mix_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return final_output
    except Exception as e:
        print(f"BGM mixing skip: {e}")

    subprocess.run(["cp", raw_output, final_output], check=False)
    return final_output


def upload_to_youtube(video_path, script_data):
    """Uploads video to YouTube using pure requests (OAuth2 + Resumable Upload API)."""
    if not (YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN):
        print("ℹ️ YouTube OAuth secrets not set; skipping YouTube auto-upload.")
        return False, "YT Secrets not set"

    print("🚀 Uploading 2-Minute Video to YouTube...")
    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": YOUTUBE_CLIENT_ID,
                "client_secret": YOUTUBE_CLIENT_SECRET,
                "refresh_token": YOUTUBE_REFRESH_TOKEN,
                "grant_type": "refresh_token"
            },
            timeout=30
        )
        if token_resp.status_code != 200:
            return False, f"YT Token Error: {token_resp.text[:120]}"

        access_token = token_resp.json().get("access_token")
        file_size = os.path.getsize(video_path)

        title = script_data.get("title", "Global Current Affairs Update")[:95]
        description = (
            f"{script_data.get('tagline', '')}\n\n"
            f"{script_data.get('description', '')}\n\n"
            f"{script_data.get('hashtags', '#GlobalAffairs #WorldNews')}"
        )
        tags = [t.strip("#") for t in script_data.get("hashtags", "").split() if t.startswith("#")]

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags[:15],
                "categoryId": "25"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        init_resp = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(file_size),
                "X-Upload-Content-Type": "video/mp4"
            },
            json=body,
            timeout=30
        )
        if init_resp.status_code != 200 or "Location" not in init_resp.headers:
            return False, f"YT Init Error: {init_resp.text[:120]}"

        upload_url = init_resp.headers["Location"]
        with open(video_path, "rb") as vf:
            put_resp = requests.put(
                upload_url,
                headers={
                    "Content-Length": str(file_size),
                    "Content-Type": "video/mp4"
                },
                data=vf,
                timeout=360
            )
        if put_resp.status_code in (200, 201):
            vid_id = put_resp.json().get("id", "")
            return True, f"https://youtu.be/{vid_id}"
        return False, f"YT Upload Error: {put_resp.text[:120]}"
    except Exception as e:
        print(f"YouTube Upload Exception: {e}")
        return False, str(e)[:120]


def resolve_fb_page_credentials():
    page_id = FB_PAGE_ID
    token = FB_ACCESS_TOKEN

    m = re.search(r'(\d{8,})', page_id)
    if m:
        page_id = m.group(1)

    try:
        r = requests.get(
            "https://graph.facebook.com/v20.0/me/accounts",
            params={"access_token": token},
            timeout=15
        )
        if r.status_code == 200:
            pages = r.json().get("data", [])
            if pages:
                for p in pages:
                    if p.get("id") == page_id or p.get("name", "").lower() in page_id.lower():
                        return p.get("id"), p.get("access_token", token)
                first_page = pages[0]
                return first_page.get("id"), first_page.get("access_token", token)
    except Exception:
        pass

    return page_id, token


def upload_to_facebook(video_path, script_data):
    if not FB_ACCESS_TOKEN or not FB_PAGE_ID:
        return False, "FB Secrets not set"

    page_id, page_token = resolve_fb_page_credentials()
    print(f"🚀 Uploading Video to Facebook Page ID: {page_id}...")
    url = f"https://graph-video.facebook.com/v20.0/{page_id}/videos"

    title = script_data.get("title", "Global Current Affairs!")
    tagline = script_data.get("tagline", "Duniya bhar ki taza tareen maloomat!")
    description = script_data.get("description", "Daily global affairs ke liye follow karein!")
    hashtags = script_data.get("hashtags", "#GlobalNews #WorldUpdate")

    full_post_description = (
        f"{title}\n\n"
        f"⚡ {tagline}\n\n"
        f"📌 {description}\n\n"
        f"{hashtags}"
    )

    try:
        with open(video_path, "rb") as vf:
            payload = {
                "access_token": page_token,
                "title": title,
                "description": full_post_description
            }
            files = {"source": vf}
            resp = requests.post(url, data=payload, files=files, timeout=240)
            if resp.status_code == 200 and "id" in resp.json():
                vid_id = resp.json()["id"]
                return True, f"Published on FB (ID: {vid_id})"
            err_msg = resp.json().get("error", {}).get("message", resp.text[:120])
            return False, f"FB Error: {err_msg}"
    except Exception as e:
        return False, str(e)[:120]


def send_to_telegram(video_path, script_data, yt_ok, yt_msg, fb_ok, fb_msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not set; skipping Telegram delivery.")
        return

    print("📲 Uploading 2-Minute Video & Report to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"

    status_lines = []
    if YOUTUBE_REFRESH_TOKEN:
        status_lines.append(f"✅ YouTube: {yt_msg}" if yt_ok else f"⚠️ YouTube: {yt_msg}")
    if FB_ACCESS_TOKEN:
        status_lines.append(f"✅ Facebook: {fb_msg}" if fb_ok else f"⚠️ Facebook: {fb_msg}")
    status_block = "\n".join(status_lines) if status_lines else "✅ Video Rendered Successfully!"

    caption = (
        f"🔥 {script_data.get('title')}\n\n"
        f"⚡ {script_data.get('tagline')}\n\n"
        f"📝 {script_data.get('description')}\n\n"
        f"🏷️ {script_data.get('hashtags')}\n\n"
        f"{status_block}"
    )[:1000]

    with open(video_path, "rb") as vf:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"video": vf},
            timeout=240
        )
        print("Telegram Upload Status:", resp.status_code)

    if resp.status_code != 200:
        print("Retrying Telegram video upload without caption...")
        with open(video_path, "rb") as vf:
            requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={"video": vf},
                timeout=240
            )


if __name__ == "__main__":
    data = generate_script_data()
    print("Video Title:", data.get("title"))
    final_vid = build_full_video(data)
    yt_success, yt_info = upload_to_youtube(final_vid, data)
    fb_success, fb_info = upload_to_facebook(final_vid, data)
    send_to_telegram(final_vid, data, yt_success, yt_info, fb_success, fb_info)
