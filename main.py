import os
import re
import json
import random
import asyncio
import subprocess
import urllib.parse
import textwrap
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
FB_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
FB_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

USED_TOPICS_FILE = "used_topics.json"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

ALL_TOPICS = [
    {
        "topic": "AI ki Duniya Mein Google aur OpenAI ki Jang",
        "tagline": "AI ki race mein kon jeetega? Google ya ChatGPT? 🤖⚔️",
        "description": "Tech giants Google aur OpenAI ke darmiyan AI dominance ke liye sakht muqabla jari hai. Naye AI models aur unka hamari zindagi par asar!",
        "badge": "TECH WARS",
        "hook_visual_1": "artificial intelligence glowing brain",
        "hook_visual_2": "computer code screen",
        "scientist_urdu": "آج کل ٹیکنالوجی کی دنیا میں ایک بہت بڑی جنگ چھڑی ہوئی ہے! گوگل اور اوپن اے آئی کے درمیان نمبر ون بننے کی دوڑ لگی ہے۔",
        "scientist_cap1": "GOOGLE VS OPENAI",
        "scientist_cap2": "AI KI SAB SE BARI JANG!",
        "sci_visual_1": "futuristic city skyline",
        "sci_visual_2": "robot hands typing",
        "fact_urdu": "اوپن اے آئی کا چیٹ جی پی ٹی اور گوگل کا جیمنی، دونوں ماڈلز انسانوں کی طرح سوچنے اور جواب دینے کی صلاحیت رکھتے ہیں۔",
        "fact_cap1": "CHATGPT AUR GEMINI:",
        "fact_cap2": "INSANO KI TARAH SOCHNA!",
        "fact_visual_1": "neural network digital",
        "fact_visual_2": "hologram technology",
        "scam_urdu": "ماہرین کا ماننا ہے کہ آنے والے چند سالوں میں یہ اے آئی سسٹمز دنیا کے کئی بڑے شعبوں میں انسانوں کی جگہ لے لیں گے!",
        "scam_cap1": "KAI SHOBO MEIN",
        "scam_cap2": "INSANO KI JAGA AI LEY GA!",
        "scam_visual_1": "empty office chairs",
        "scam_visual_2": "robot working in factory",
        "loss_visual_1": "stock market crash graph",
        "loss_visual_2": "stressed business man",
        "vid_queries": ["artificial intelligence", "technology", "future"]
    },
    {
        "topic": "Global Warming aur Pighalti Hui Barf: Duniya Ka Mustaqbil",
        "tagline": "Duniya ka temperature barh raha hai! Kya hum tayyar hain? 🌍🔥",
        "description": "Climate change aur global warming ki wajah se glaciers tezi se pighal rahe hain. Samandar ka level barhne se kin shehron ko khatra hai?",
        "badge": "CLIMATE ALERT",
        "hook_visual_1": "melting iceberg glacier",
        "hook_visual_2": "sun bright heat",
        "scientist_urdu": "پچھلے چند سالوں میں زمین کا درجہ حرارت تیزی سے بڑھ رہا ہے جس کی وجہ سے قطبین کی برف پگھل رہی ہے۔",
        "scientist_cap1": "GLOBAL WARMING KA KHATRA:",
        "scientist_cap2": "BARF TEZI SE PIGHAL RAHI HAI!",
        "sci_visual_1": "polar bear small ice",
        "sci_visual_2": "thermometer high temperature",
        "fact_urdu": "سائنسدانوں نے خبردار کیا ہے کہ اگر یہ سلسلہ نہ رکا، تو سمندروں کی سطح بڑھنے سے کئی ساحلی شہر پانی میں ڈوب سکتے ہیں۔",
        "fact_cap1": "SAMANDAR KA LEVEL BARH RAHA HAI",
        "fact_cap2": "SAHILI SHEHAR DOOBNE KA KHATRA!",
        "fact_visual_1": "ocean waves rising",
        "fact_visual_2": "flooded city streets",
        "scam_urdu": "صرف یہی نہیں، بلکہ موسموں کی شدت میں اضافہ ہو رہا ہے۔ کہیں شدید سیلاب تو کہیں خطرناک قحط سالی کا سامنا ہے۔",
        "scam_cap1": "SHADEED MAUSAMI HALAAT:",
        "scam_cap2": "SELAAB AUR QAHT SALI!",
        "scam_visual_1": "dry cracked earth",
        "scam_visual_2": "heavy rain flood",
        "loss_visual_1": "destroyed houses storm",
        "loss_visual_2": "people rescuing in water",
        "vid_queries": ["climate change", "melting glacier", "flood"]
    },
    {
        "topic": "SpaceX aur Mars Mission: Insan Ka Naya Ghar?",
        "tagline": "Elon Musk ka Mars par basti basane ka khawab! 🚀🔴",
        "description": "SpaceX ka Starship rocket insan ko Mars par le jane ke liye tayyar ho raha ہے۔ Kya hum waqai Mars par reh sakenge?",
        "badge": "SPACE MISSION",
        "hook_visual_1": "rocket launch night",
        "hook_visual_2": "planet mars space",
        "scientist_urdu": "ایلون مسک کی کمپنی سپیس ایکس کا خواب ہے کہ وہ انسانوں کو مریخ پر لے جا کر وہاں ایک نئی دنیا بسائے۔",
        "scientist_cap1": "ELON MUSK KA KHAWAB:",
        "scientist_cap2": "MARS PAR INSAANI BASTI!",
        "sci_visual_1": "astronaut on mars",
        "sci_visual_2": "spacecraft traveling orbit",
        "fact_urdu": "ان کا سٹار شپ راکٹ تاریخ کا سب سے طاقتور راکٹ ہے، جو ایک ہی وقت میں درجنوں انسانوں اور سامان کو خلا میں لے جا سکتا ہے۔",
        "fact_cap1": "STARSHIP ROCKET:",
        "fact_cap2": "TAREEKH KA SAB SE BARA ROCKET!",
        "fact_visual_1": "huge rocket engine fire",
        "fact_visual_2": "satellite in space",
        "scam_urdu": "لیکن مریخ کا سفر کوئی آسان کام نہیں۔ وہاں کا ماحول، ریڈی ایشن اور آکسیجن کی کمی سب سے بڑے چیلنجز ہیں۔",
        "scam_cap1": "MARS KA SAFAR AASAAN NAHI:",
        "scam_cap2": "RADIATION AUR OXYGEN KI KAMI!",
        "scam_visual_1": "mars surface red dust",
        "scam_visual_2": "astronaut helmet reflection",
        "loss_visual_1": "broken space equipment",
        "loss_visual_2": "spaceship crashing",
        "vid_queries": ["rocket launch", "mars planet", "astronaut"]
    },
    {
        "topic": "Global Economy Par Inflation Ka Asar aur Mehngai Ka Toofan",
        "tagline": "Duniya bhar mein mehngai q barh rahi hai? Asli waja janiye! 💸📉",
        "description": "Oil prices, wars, aur supply chain issues ki wajah se poori duniya inflation ka shikar hai. Global economy kahan ja rahi hai?",
        "badge": "GLOBAL ECONOMY",
        "hook_visual_1": "inflation graph rising",
        "hook_visual_2": "empty wallet hands",
        "scientist_urdu": "آج کل پوری دنیا کو ایک بہت بڑے معاشی بحران کا سامنا ہے، اور ہر ملک میں مہنگائی تیزی سے بڑھ رہی ہے۔",
        "scientist_cap1": "DUNIYA BHAR MEIN BOHRAAN:",
        "scientist_cap2": "MEHNGAI KA TOOFAN BARKARAR!",
        "sci_visual_1": "stock market numbers red",
        "sci_visual_2": "grocery store prices high",
        "fact_urdu": "تیل کی بڑھتی ہوئی قیمتیں، بین الاقوامی تنازعات اور سپلائی چین کے مسائل اس مہنگائی کی سب سے بڑی وجوہات ہیں۔",
        "fact_cap1": "MEHNGAI KI WAJOHAT:",
        "fact_cap2": "OIL PRICES AUR WARS!",
        "fact_visual_1": "oil barrels stack",
        "fact_visual_2": "cargo ship ocean containers",
        "scam_urdu": "جس کی وجہ سے عام آدمی کی قوت خرید کم ہو گئی ہے اور روزمرہ کی اشیاء کا حصول بھی مشکل ہوتا جا رہا ہے۔",
        "scam_cap1": "AAM AADMI PARESHAN:",
        "scam_cap2": "QUWAT-E-KHAREED KHATAM!",
        "scam_visual_1": "sad poor person",
        "scam_visual_2": "calculating bills expenses",
        "loss_visual_1": "bankrupt sign business",
        "loss_visual_2": "empty grocery cart",
        "vid_queries": ["economy graph", "money inflation", "oil prices"]
    },
    {
        "topic": "Electric Vehicles (EVs) Ka Inqalab aur Future of Transport",
        "tagline": "Petrol gariyon ka daur khatam? EVs ka future kya hai! ⚡🚗",
        "description": "Tesla aur Chinese EV companies ne duniya bhar mein car market ko badal kar rakh diya hai. Kya future sirf battery cars ka hai?",
        "badge": "AUTO REVOLUTION",
        "hook_visual_1": "electric car charging",
        "hook_visual_2": "futuristic highway traffic",
        "scientist_urdu": "پٹرول اور ڈیزل پر چلنے والی گاڑیوں کا دور اب آہستہ آہستہ ختم ہو رہا ہے، اور الیکٹرک گاڑیاں مستقبل کی سواری بن رہی ہیں۔",
        "scientist_cap1": "PETROL GARIYON KA END:",
        "scientist_cap2": "ELECTRIC VEHICLES KA DAUR!",
        "sci_visual_1": "electric car dashboard",
        "sci_visual_2": "battery charging station",
        "fact_urdu": "ٹیسلا اور دیگر چینی کمپنیوں نے جدید بیٹری ٹیکنالوجی کے ذریعے ان گاڑیوں کو سستا اور زیادہ مائلیج والا بنا دیا ہے۔",
        "fact_cap1": "TESLA AUR CHINESE EVs:",
        "fact_cap2": "SASTI AUR ZYADA MILEAGE!",
        "fact_visual_1": "lithium ion battery packs",
        "fact_visual_2": "car assembly line robots",
        "scam_urdu": "آنے والے چند سالوں میں دنیا کے کئی ممالک پٹرول گاڑیوں پر مکمل پابندی لگانے کا منصوبہ بنا رہے ہیں تاکہ آلودگی کو کم کیا جا سکے۔",
        "scam_cap1": "PETROL PAR PABANDI:",
        "scam_cap2": "ALOODGI KHATAM KARNE KA PLAN!",
        "scam_visual_1": "clean city air",
        "scam_visual_2": "green energy wind turbines",
        "loss_visual_1": "abandoned gas station",
        "loss_visual_2": "scrap metal junk cars",
        "vid_queries": ["electric car", "charging station", "future transport"]
    }
]

def pick_unused_topic():
    used = []
    if os.path.exists(USED_TOPICS_FILE):
        try:
            with open(USED_TOPICS_FILE, "r") as f:
                used = json.load(f)
        except Exception:
            used = []

    available = [t for t in ALL_TOPICS if t["topic"] not in used]
    if not available:
        used = []
        available = ALL_TOPICS

    chosen = random.choice(available)
    used.append(chosen["topic"])
    with open(USED_TOPICS_FILE, "w") as f:
        json.dump(used, f, indent=2)
    return chosen

def generate_script_data():
    chosen = pick_unused_topic()
    topic = chosen["topic"]
    badge = chosen["badge"]
    print(f"🔥 Building Scene-Matched Script for: {topic}")

    return {
        "title": f"🌍 {topic} | Global Update",
        "tagline": chosen["tagline"],
        "description": chosen["description"],
        "hashtags": "#GlobalEvents #NewsUpdate #WorldNews #Trending #LatestFacts #Knowledge #ViralReels",
        "category_badge": badge,
        "scenes": [
            {
                "tts_urdu": "کیا آپ کو معلوم ہے کہ اس وقت دنیا میں کون سی سب سے بڑی تبدیلی آ رہی ہے؟ جو ہماری آنے والی زندگیوں کو مکمل طور پر بدل کر رکھ دے گی؟",
                "caption_part1": "DUNIYA KI SAB SE BARI",
                "caption_part2": "TABDEELI KYA HAI?!",
                "search_query_1": chosen["hook_visual_1"],
                "search_query_2": chosen["hook_visual_2"],
                "video_query": chosen["vid_queries"][0]
            },
            {
                "tts_urdu": chosen["scientist_urdu"],
                "caption_part1": chosen["scientist_cap1"],
                "caption_part2": chosen["scientist_cap2"],
                "search_query_1": chosen["sci_visual_1"],
                "search_query_2": chosen["sci_visual_2"],
                "video_query": ""
            },
            {
                "tts_urdu": chosen["fact_urdu"],
                "caption_part1": chosen["fact_cap1"],
                "caption_part2": chosen["fact_cap2"],
                "search_query_1": chosen["fact_visual_1"],
                "search_query_2": chosen["fact_visual_2"],
                "video_query": chosen["vid_queries"][1]
            },
            {
                "tts_urdu": "ماہرین اور گلوبل لیڈرز اس بات پر متفق ہیں کہ اگر ہم نے وقت کے ساتھ خود کو نہ بدلا تو اس کے بہت بھیانک نتائج ہو سکتے ہیں۔",
                "caption_part1": "EXPERTS KI WARNING:",
                "caption_part2": "WAQT KE SATH BADLO!",
                "search_query_1": "global leaders meeting conference",
                "search_query_2": "world globe hands",
                "video_query": ""
            },
            {
                "tts_urdu": chosen["scam_urdu"],
                "caption_part1": chosen["scam_cap1"],
                "caption_part2": chosen["scam_cap2"],
                "search_query_1": chosen["scam_visual_1"],
                "search_query_2": chosen["scam_visual_2"],
                "video_query": chosen["vid_queries"][2]
            },
            {
                "tts_urdu": "دنیا بھر کی حکومتیں اور بڑی کمپنیاں اب اس مسئلے سے نمٹنے کے لیے اربوں ڈالرز کی سرمایہ کاری کر رہی ہیں تاکہ ایک نیا نظام بنایا جا سکے۔",
                "caption_part1": "ARBON DOLLARS KI INVESTMENT:",
                "caption_part2": "NAYA NIZAM BANANE KI TAYYARI!",
                "search_query_1": "business meeting graph pointing",
                "search_query_2": "global trading network",
                "video_query": ""
            },
            {
                "tts_urdu": "لیکن اس ساری دوڑ میں نقصان صرف عام آدمی کا ہو رہا ہے، جو پہلے ہی روزمرہ کے مسائل میں گھرا ہوا ہے۔",
                "caption_part1": "NUQSAN SIRF AAM AADMI KA:",
                "caption_part2": "JO PEHLE HI PARESHAN HAI!",
                "search_query_1": chosen["loss_visual_1"],
                "search_query_2": "crowded city people walking",
                "video_query": ""
            },
            {
                "tts_urdu": "حالات اتنی تیزی سے بدل رہے ہیں کہ اگلے دس سالوں میں دنیا وہ نہیں رہے گی جسے ہم آج جانتے ہیں۔ ایک بالکل نیا کلچر اور نظام ہمارے سامنے ہوگا۔",
                "caption_part1": "AGLE 10 SAAL MEIN",
                "caption_part2": "DUNIYA BILKUL BADAL JAYEGI!",
                "search_query_1": chosen["loss_visual_2"],
                "search_query_2": "futuristic digital technology interface",
                "video_query": ""
            },
            {
                "tts_urdu": "چاہے وہ معیشت ہو، ٹیکنالوجی یا پھر ہمارا ماحول، ان گلوبل ایونٹس کا براہ راست اثر ہم سب کی زندگیوں پر پڑنا لازمی ہے۔",
                "caption_part1": "TECHNOLOGY HO YA ECONOMY",
                "caption_part2": "ASAR HUM PAR LAZMI HAI!",
                "search_query_1": "world map connection lines",
                "search_query_2": chosen["hook_visual_1"],
                "video_query": "global connection"
            },
            {
                "tts_urdu": "دنیا کے ان اہم حالات اور واقعات سے باخبر رہنے کے لیے اور روزانہ کچھ نیا سیکھنے کے لیے، ہمارے پیج کو ابھی فالو کریں!",
                "caption_part1": "DAILY GLOBAL UPDATES KE LIYE:",
                "caption_part2": "ABHI FOLLOW KAREIN! 🌍",
                "search_query_1": "smartphone social media likes",
                "search_query_2": "news media broadcast technology",
                "video_query": ""
            }
        ]
    }

USED_MEDIA_URLS = set()

def fetch_contextual_stock_video(query, filename):
    """Fetches HD Stock Video using Official PIXABAY_API_KEY first, then Mixkit fallback."""
    if not query:
        return None

    # 1. Official Pixabay Video API
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

    # 2. Mixkit Fallback
    slug = urllib.parse.quote(query.lower().strip())
    search_url = f"https://mixkit.co/free-stock-video/{slug}/"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=18)
        if resp.status_code == 200:
            mp4_urls = re.findall(r'https://assets\.mixkit\.co/videos/[^\s"'<>]+\.mp4', resp.text)
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

def fetch_exact_scene_photo(query, filename):
    """Fetches HD Stock Photo using Official PIXABAY_API_KEY first, then Bing HD fallback."""
    # 1. Official Pixabay Image API
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

    # 2. Bing HD Search Fallback
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

    bw, bh = 620, 82
    bx, by = (1080 - bw) // 2, 95
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=41, fill=(220, 30, 30, 250), outline=(255, 255, 255, 240), width=4)
    b_text = badge_text.upper()
    b_bbox = draw.textbbox((0, 0), b_text, font=badge_font)
    b_tw, b_th = b_bbox[2] - b_bbox[0], b_bbox[3] - b_bbox[1]
    draw.text((bx + (bw - b_tw) // 2, by + (bh - b_th) // 2 - 4), b_text, font=badge_font, fill=(255, 255, 255, 255))

    lines = textwrap.wrap(caption_text.upper(), width=15)
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

    progress_fraction = (scene_idx + (0.5 if part_num == 1 else 1.0)) / total_scenes
    prog_w = int(980 * progress_fraction)
    draw.rounded_rectangle([50, 1835, 1030, 1855], radius=10, fill=(255, 255, 255, 75))
    draw.rounded_rectangle([50, 1835, 50 + max(prog_w, 25), 1855], radius=10, fill=(255, 215, 0, 255))

    out_png = f"hud_{scene_idx}_p{part_num}.png"
    overlay.save(out_png)
    return out_png

async def synthesize_scene_voice(urdu_text, index):
    raw_audio = f"raw_voice_{index}.mp3"
    mastered_audio = f"voice_{index}.m4a"

    communicate = edge_tts.Communicate(urdu_text, voice="ur-PK-AsadNeural", rate="+14%", pitch="-2Hz")
    await communicate.save(raw_audio)

    af_chain = (
        "silenceremove=start_periods=1:start_silence=0.04:start_threshold=-45dB,"
        "highpass=f=75,"
        "bass=g=4:f=110,"
        "treble=g=3:f=4500,"
        "acompressor=threshold=-16dB:ratio=3:attack=5:release=60:makeup=3dB,"
        "apad=pad_dur=0.14"
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            out_clip
        ]
        subprocess.run(safe_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def render_two_cut_scene(scene, idx, total_scenes, badge):
    audio_path = asyncio.run(synthesize_scene_voice(scene["tts_urdu"], idx))
    total_dur = get_audio_duration(audio_path)
    half_dur = round(total_dur / 2.0, 2)
    rem_dur = round(total_dur - half_dur, 2)

    q1 = scene["search_query_1"]
    q2 = scene["search_query_2"]
    v_q = scene.get("video_query", "")

    vid_file = fetch_contextual_stock_video(v_q, f"stock_vid_{idx}.mp4") if v_q else None
    if vid_file:
        media1, is_vid1 = vid_file, True
    else:
        media1 = fetch_exact_scene_photo(q1, f"photo_{idx}_1.jpg")
        is_vid1 = False

    media2 = fetch_exact_scene_photo(q2, f"photo_{idx}_2.jpg")

    ov1 = create_burned_hud_overlay(scene["caption_part1"], badge, idx, total_scenes, 1)
    ov2 = create_burned_hud_overlay(scene["caption_part2"], badge, idx, total_scenes, 2)

    sub1 = f"sub_{idx}_1.mp4"
    sub2 = f"sub_{idx}_2.mp4"
    prepare_visual_subclip(media1, is_vid1, ov1, half_dur, 0, sub1)
    prepare_visual_subclip(media2, False, ov2, rem_dur, 1, sub2)

    list_file = f"scene_list_{idx}.txt"
    with open(list_file, "w") as f:
        f.write(f"file '{sub1}'
file '{sub2}'
")

    scene_out = f"scene_final_{idx}.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "copy", "-shortest",
        scene_out
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return scene_out

def build_full_video(script_data):
    scenes = script_data["scenes"]
    badge = script_data.get("category_badge", "GLOBAL NEWS")
    scene_files = []

    for idx, scene in enumerate(scenes):
        print(f"🎬 Scene {idx+1}/{len(scenes)}: '{scene['caption_part1']} | {scene['caption_part2']}'")
        s_file = render_two_cut_scene(scene, idx, len(scenes), badge)
        scene_files.append(s_file)

    with open("master_concat.txt", "w") as f:
        for sf in scene_files:
            f.write(f"file '{sf}'
")

    raw_output = "raw_reel.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "master_concat.txt",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
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
                        print(f"  [✓] Matched Facebook Page: {p.get('name')} ({p.get('id')})")
                        return p.get("id"), p.get("access_token", token)
                first_page = pages[0]
                print(f"  [✓] Using Default Facebook Page: {first_page.get('name')} ({first_page.get('id')})")
                return first_page.get("id"), first_page.get("access_token", token)
    except Exception as e:
        print(f"  [!] FB account check note: {e}")

    return page_id, token

def upload_to_facebook(video_path, script_data):
    if not FB_ACCESS_TOKEN or not FB_PAGE_ID:
        print("⚠️ Facebook credentials missing in environment variables.")
        return False, "FB Secrets missing"

    page_id, page_token = resolve_fb_page_credentials()
    print(f"🚀 Uploading Video to Facebook Page ID: {page_id}...")
    url = f"https://graph-video.facebook.com/v20.0/{page_id}/videos"

    title = script_data.get("title", "Global Update!")
    tagline = script_data.get("tagline", "Duniya bhar ki taza tareen maloomat!")
    description = script_data.get("description", "Daily news aur global affairs ke liye follow karein!")
    hashtags = script_data.get("hashtags", "#GlobalNews #WorldUpdate")

    full_post_description = (
        f"{title}

"
        f"⚡ {tagline}

"
        f"📌 {description}

"
        f"👉 Humare page ko follow karein!

"
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
            print("Facebook API Status:", resp.status_code, resp.text)
            if resp.status_code == 200 and "id" in resp.json():
                vid_id = resp.json()["id"]
                return True, f"Published on FB! (Video ID: {vid_id})"
            err_msg = resp.json().get("error", {}).get("message", resp.text[:140])
            return False, f"FB Error: {err_msg}"
    except Exception as e:
        print(f"Facebook Upload Exception: {e}")
        return False, str(e)[:120]

def send_to_telegram(video_path, script_data, fb_ok, fb_msg):
    print("📲 Uploading Reel & Status Report to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    fb_status_line = f"✅ Facebook Auto-Post: {fb_msg}" if fb_ok else f"⚠️ Facebook Auto-Post: {fb_msg}"

    caption = (
        f"🔥 {script_data.get('title')}

"
        f"⚡ Tagline:
{script_data.get('tagline')}

"
        f"📝 Description:
{script_data.get('description')}

"
        f"🏷️ Viral Tags:
{script_data.get('hashtags')}

"
        f"{fb_status_line}"
    )

    caption = caption[:1000]

    with open(video_path, "rb") as vf:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"video": vf},
            timeout=180
        )
        print("Telegram Upload Status:", resp.status_code, resp.text)

    if resp.status_code != 200:
        print("Retrying Telegram video upload without caption...")
        with open(video_path, "rb") as vf:
            requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={"video": vf},
                timeout=180
            )

if __name__ == "__main__":
    data = generate_script_data()
    print("Video Title:", data.get("title"))
    final_vid = build_full_video(data)
    fb_success, fb_info = upload_to_facebook(final_vid, data)
    send_to_telegram(final_vid, data, fb_success, fb_info)
