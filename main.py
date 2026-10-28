import os
import re
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

# Built-in 2-Minute Global Current Affairs Topics (14 scenes each = ~120 seconds)
FALLBACK_GLOBAL_TOPICS = [
    {
        "topic": "US vs China Semiconductor Chip War and Global Tech Dominance",
        "tagline": "America aur China ki Chip War duniya ki economy ko kaise badal rahi hai? 🌍💻",
        "description": "Taiwan ki TSMC chips, America ki pabandiyan aur China ka naya AI tech plan! Janiye kaise ek choti si silicon chip poori duniya ki superpower race ka faisla kar rahi hai.",
        "badge": "TECH GEOPOLITICS",
        "hook_visual_1": "computer microchip processor",
        "hook_visual_2": "usa china flags",
        "context_urdu": "آج کی جدید دنیا میں تیل سے زیادہ قیمتی چیز سلیکون چپس بن چکی ہیں، جن کے بغیر کوئی سمارٹ فون، کمپیوٹر، اے آئی سسٹم یا جدید جنگی طیارہ چل ہی نہیں سکتا۔",
        "context_cap1": "TEEL SE ZYADA QEEMTI:",
        "context_cap2": "SILICON MICROCHIPS!",
        "ctx_visual_1": "semiconductor wafer lab",
        "ctx_visual_2": "fighter jet cockpit",
        "event_urdu": "امریکہ نے چین کی بڑھتی ہوئی ٹیکنالوجی اور ملٹری طاقت کو روکنے کے لیے جدید ترین اے آئی چپس اور لیتھوگرافی مشینوں کی ایکسپورٹ پر سخت ترین پابندیاں عائد کر دی ہیں۔",
        "event_cap1": "AMERICA KI SAKHT PABANDI",
        "event_cap2": "CHINA KI TECH PAR ROK!",
        "evt_visual_1": "white house washington",
        "evt_visual_2": "shipping containers port",
        "impact_urdu": "اس جنگ کا سب سے بڑا مرکز تائیوان ہے، جہاں دنیا کی نوے فیصد ایڈوانس چپس بنانے والی کمپنی ٹی ایس ایم سی موجود ہے، جس کی وجہ سے پورے خطے میں کشیدگی بڑھ گئی ہے۔",
        "impact_cap1": "TAIWAN KI TSMC FACTORY:",
        "impact_cap2": "90% ADVANCED CHIPS KA GHAR!",
        "imp_visual_1": "modern electronics factory",
        "imp_visual_2": "naval warship ocean",
        "response_urdu": "جواب میں چین نے بھی اربوں ڈالرز کا فنڈ جاری کیا ہے اور چپس بنانے میں استعمال ہونے والی نایاب دھاتوں یعنی گیلئم اور جرمینئم کی ایکسپورٹ پر شرائط لگا دی ہیں۔",
        "response_cap1": "CHINA KA JAWABI WAR:",
        "response_cap2": "RARE EARTH METALS PAR ROK!",
        "res_visual_1": "mining industry minerals",
        "res_visual_2": "chinese yuan money",
        "future_urdu": "ماہرین کا کہنا ہے کہ اس چپ وار کی وجہ سے آنے والے سالوں میں موبائل فونز، لیپ ٹاپس اور گاڑیوں کی قیمتوں میں بڑا اضافہ ہو سکتا ہے اور ٹیکنالوجی دو حصوں میں بٹ جائے گی۔",
        "future_cap1": "GLOBAL SUPPLY CHAIN:",
        "future_cap2": "TECH KI DUNIYA DO HISSON MEIN!",
        "fut_visual_1": "smartphone motherboard repair",
        "fut_visual_2": "stock market trading screen",
        "vid_queries": ["microchip", "technology", "factory", "global network"]
    },
    {
        "topic": "BRICS Expansion and De-Dollarization Challenge to US Dollar",
        "tagline": "Kya BRICS countries American Dollar ki badshahat khatam karne wali hain? 💵🌍",
        "description": "China, Russia, Saudi Arabia aur BRICS ممالک apni local currencies aur gold mein trade kyun barha rahe hain? Global economy aur Dollar ke mustaqbil ka mukammal tajziya.",
        "badge": "GLOBAL ECONOMY",
        "hook_visual_1": "us dollar bills gold",
        "hook_visual_2": "world leaders summit",
        "context_urdu": "پچھلے اسی سالوں سے امریکی ڈالر پوری دنیا کی تجارت اور بینکاری کا بے تاج بادشاہ رہا ہے، جہاں تیل سے لے کر سونے تک ہر چیز ڈالر میں خریدی جاتی تھی۔",
        "context_cap1": "80 SAAL SE DUNYA PAR",
        "context_cap2": "AMERICAN DOLLAR KA RAAJ!",
        "ctx_visual_1": "federal reserve bank",
        "ctx_visual_2": "gold bars vault",
        "event_urdu": "مگر اب برکس تنظیم میں نئے ممالک کی شمولیت کے بعد چین، روس اور دیگر بڑی معیشتوں نے ڈالر کے بجائے اپنی مقامی کرنسیوں میں تجارت کا آغاز کر دیا ہے۔",
        "event_cap1": "BRICS COUNTRIES KA FAISLA:",
        "event_cap2": "LOCAL CURRENCY MEIN TRADE!",
        "evt_visual_1": "international conference flags",
        "evt_visual_2": "cargo ship containers",
        "impact_urdu": "اس تبدیلی کی سب سے بڑی وجہ مغربی پابندیاں اور امریکہ کا بڑھتا ہوا قرضہ ہے، جس نے دنیا کے مرکزی بینکوں کو ڈالر کے بجائے دھڑا دھڑ سونا خریدنے پر مجبور کر دیا ہے۔",
        "impact_cap1": "CENTRAL BANKS KA RUKH:",
        "impact_cap2": "DOLLAR CHORO, SONA KHARIDO!",
        "imp_visual_1": "gold bullion coins",
        "imp_visual_2": "financial chart decline",
        "response_urdu": "برکس ممالک اب ایک نئے ڈیجیٹل پیمنٹ سسٹم پر بھی کام کر رہے ہیں تاکہ بین الاقوامی لین دین کے لیے سوئفٹ سسٹم پر انحصار ختم کیا جا سکے۔",
        "response_cap1": "SWIFT SYSTEM KA MUTABADIL:",
        "response_cap2": "NAYA DIGITAL PAYMENT SYSTEM!",
        "res_visual_1": "digital blockchain network",
        "res_visual_2": "banking server room",
        "future_urdu": "معاشی ماہرین کے مطابق ڈالر فوری طور پر ختم تو نہیں ہوگا، لیکن دنیا اب ایک ملٹی پولر کرنسی سسٹم کی طرف بڑھ رہی ہے جہاں طاقت صرف ایک ملک کے پاس نہیں رہے گی۔",
        "future_cap1": "MULTI-POLAR WORLD ORDER:",
        "future_cap2": "GLOBAL ECONOMY KA NAYA DAUR!",
        "fut_visual_1": "world map glowing connections",
        "fut_visual_2": "currency exchange board",
        "vid_queries": ["money", "gold", "shipping", "finance"]
    },
    {
        "topic": "Red Sea Shipping Crisis and Global Oil Supply Chain Disruption",
        "tagline": "Red Sea aur Suez Canal ke bohran se poori duniya mein mehngai kyun barh rahi hai? 🚢⛽",
        "description": "Samandari raston par hamton ki wajah se cargo ships ko Africa ke gird lamba chakkar kyun lagana par raha hai? Global trade aur oil prices par iska asar.",
        "badge": "TRADE CRISIS",
        "hook_visual_1": "cargo ship ocean storm",
        "hook_visual_2": "oil tanker ship",
        "context_urdu": "بحیرہ احمر اور نہر سوئز دنیا کی تجارت کی سب سے اہم شہ رگ ہیں، جہاں سے ہر سال دنیا کے بارہ فیصد سے زائد سامان اور تیل کے جہاز گزرتے ہیں۔",
        "context_cap1": "RED SEA AUR SUEZ CANAL:",
        "context_cap2": "GLOBAL TRADE KI SHAH-RAG!",
        "ctx_visual_1": "suez canal ship",
        "ctx_visual_2": "port crane containers",
        "event_urdu": "مشرق وسطیٰ کی کشیدگی اور بحری جہازوں پر ہونے والے ڈرون اور میزائل حملوں نے دنیا کی سب سے بڑی شپنگ کمپنیوں کو اس راستے سے گزرنے سے روک دیا ہے۔",
        "event_cap1": "SAMANDAR MEIN KHATRA:",
        "event_cap2": "SHIPPING COMPANIES RUK GAYIN!",
        "evt_visual_1": "military navy ship",
        "evt_visual_2": "radar screen navigation",
        "impact_urdu": "اب یورپ اور ایشیا کے درمیان چلنے والے جہازوں کو افریقہ کے گرد چکر لگا کر جانا پڑتا ہے، جس سے سفر میں دس سے چودہ دن کا اضافہ اور لاکھوں ڈالر کا اضافی ایندھن خرچ ہو رہا ہے۔",
        "impact_cap1": "AFRICA KE GIRD LAMBA SAFAR:",
        "impact_cap2": "14 DIN AUR LAKHON DOLLAR EXTRA!",
        "imp_visual_1": "world map shipping route",
        "imp_visual_2": "fuel pump gauge",
        "response_urdu": "کنٹینرز کے کرائے اور انشورنس کی قیمتیں تین گنا تک بڑھ چکی ہیں، جس کا سیدھا بوجھ امپورٹڈ سامان، الیکٹرانکس اور خوراک کی قیمتوں پر پڑ رہا ہے۔",
        "response_cap1": "SHIPPING COST 3 GUNA ZYADA:",
        "response_cap2": "HAR CHEEZ MEHNGI HONE LAGI!",
        "res_visual_1": "supermarket shelves shopping",
        "res_visual_2": "calculator bills money",
        "future_urdu": "جب تک سمندری راستوں میں مکمل امن قائم نہیں ہوتا، عالمی سپلائی چین متاثر رہے گی اور دنیا بھر کے صارفین کو مہنگائی کا سامنا کرنا پڑے گا۔",
        "future_cap1": "SAMANDARI RASTON KI JANG:",
        "future_cap2": "GLOBAL MEHNGAI KA BOHRAN!",
        "fut_visual_1": "industrial harbor sunset",
        "fut_visual_2": "global logistics network",
        "vid_queries": ["cargo ship", "ocean", "port", "economy"]
    },
    {
        "topic": "Artificial Intelligence Regulation and Global Job Market Transformation",
        "tagline": "AI Revolution: Agle 5 saal mein kaunsi jobs khatam aur kaunsi nayi banengi? 🤖⚡",
        "description": "Autonomous AI agents, robotics aur global governments ke naye AI laws! Janiye kaise Artificial Intelligence duniya ke har mulk ki economy ko badal rahi hai.",
        "badge": "AI REVOLUTION",
        "hook_visual_1": "humanoid robot artificial intelligence",
        "hook_visual_2": "modern office computers",
        "context_urdu": "مصنوعی ذہانت یعنی اے آئی اب صرف چیٹ بوٹس تک محدود نہیں رہی، بلکہ اب ایسے خودکار اے آئی ایجنٹس آ چکے ہیں جو پورا سافٹ ویئر، ویڈیو اور بزنس آپریشن خود چلا سکتے ہیں۔",
        "context_cap1": "CHATBOTS SE AAGE KI DUNIYA:",
        "context_cap2": "AUTONOMOUS AI AGENTS!",
        "ctx_visual_1": "futuristic data center",
        "ctx_visual_2": "programmer coding screen",
        "event_urdu": "آئی ایم ایف اور ورلڈ اکنامک فورم کی تازہ رپورٹ کے مطابق دنیا بھر میں چالیس فیصد ملازمتیں اے آئی کی وجہ سے براہ راست متاثر ہونے جا رہی ہیں۔",
        "event_cap1": "IMF KI BARI REPORT:",
        "event_cap2": "40% GLOBAL JOBS PAR ASAR!",
        "evt_visual_1": "business analytics chart",
        "evt_visual_2": "corporate building glass",
        "impact_urdu": "کسٹمر سپورٹ، ڈیٹا انٹری، بیسک کوڈنگ اور گرافک ڈیزائن کے شعبوں میں بڑی کمپنیاں اب انسانوں کے بجائے اے آئی سسٹمز کو تیزی سے اپنا رہی ہیں۔",
        "impact_cap1": "COMPANIES KA NAYA RUKH:",
        "impact_cap2": "AUTOMATION SE COST CUTTING!",
        "imp_visual_1": "empty office desks",
        "imp_visual_2": "robotic arm factory",
        "response_urdu": "دوسری طرف یورپی یونین اور دیگر ممالک نے اے آئی کے خطرات، ڈیپ فیکس اور سائبر حملوں کو روکنے کے لیے تاریخ کے پہلے سخت اے آئی قوانین نافذ کر دیے ہیں۔",
        "response_cap1": "DEEPFAKES AUR CYBER KHATRA:",
        "response_cap2": "DUNIYA MEIN NAYE AI QAWANEEN!",
        "res_visual_1": "cyber security lock digital",
        "res_visual_2": "parliament building europe",
        "future_urdu": "ماہرین کا ماننا ہے کہ اے آئی انسانوں کی جگہ نہیں لے گی، بلکہ جو انسان اے آئی کا استعمال جانتا ہوگا وہ ان لوگوں کی جگہ لے لے گا جو پرانے طریقے پر چل رہے ہیں۔",
        "future_cap1": "FUTURE SURVIVAL RULE:",
        "future_cap2": "AI SEEKHO AUR AAGE BARHO!",
        "fut_visual_1": "person using futuristic tablet",
        "fut_visual_2": "glowing brain neural network",
        "vid_queries": ["artificial intelligence", "robot", "coding", "cybersecurity"]
    },
    {
        "topic": "Global Climate Crisis Extreme Weather and Clean Energy Transition",
        "tagline": "Record garmi, selaab aur badalta mausam: Duniya ka mustaqbil kya hai? 🌡️🌊",
        "description": "Global warming ki wajah se duniya bhar mein extreme weather events kyun barh rahe hain? Green energy aur solar revolution ki taza tareen soorat-e-haal.",
        "badge": "CLIMATE CRISIS",
        "hook_visual_1": "extreme weather storm clouds",
        "hook_visual_2": "melting glacier ice",
        "context_urdu": "سائنسدانوں نے تصدیق کی ہے کہ حالیہ برس انسانی تاریخ کے گرم ترین سال ثابت ہوئے ہیں، جہاں زمین اور سمندروں کا درجہ حرارت خطرناک حدوں کو چھو رہا ہے۔",
        "context_cap1": "TAREEKH KE GARAM TAREEN SAAL:",
        "context_cap2": "ZAMEEN KA TEMPERATURE HIGH!",
        "ctx_visual_1": "scorching sun desert",
        "ctx_visual_2": "earth from space glowing",
        "event_urdu": "اس ماحولیاتی تبدیلی کی وجہ سے کہیں صحراؤں میں اچانک طوفانی بارشیں اور سیلاب آ رہے ہیں، تو کہیں جنگلات میں لگنے والی آگ پورے شہروں کو لپیٹ میں لے رہی ہے۔",
        "event_cap1": "AJEEB MAUSAMI TABDEELI:",
        "event_cap2": "SEHRA MEIN BARISH AUR JANGAL MEIN AAG!",
        "evt_visual_1": "wildfire forest smoke",
        "evt_visual_2": "flooded city cars",
        "impact_urdu": "موسمیاتی آفات کی وجہ سے ہر سال عالمی معیشت کو سینکڑوں ارب ڈالرز کا نقصان ہو رہا ہے اور فصلوں کی پیداوار متاثر ہونے سے خوراک کی قیمتیں بڑھ رہی ہیں۔",
        "impact_cap1": "FASLON AUR ECONOMY KO NUQSAN:",
        "impact_cap2": "FOOD SECURITY KA BOHRAN!",
        "imp_visual_1": "dry agricultural field",
        "imp_visual_2": "wheat grain harvest",
        "response_urdu": "اس بحران سے نمٹنے کے لیے اب پوری دنیا میں سولر انرجی، ونڈ پاور اور الیکٹرک گاڑیوں پر ریکارڈ رفتار سے سرمایہ کاری کی جا رہی ہے۔",
        "response_cap1": "GREEN ENERGY INQALAB:",
        "response_cap2": "SOLAR AUR WIND POWER KI DOUR!",
        "res_visual_1": "solar panels farm",
        "res_visual_2": "wind turbines ocean",
        "future_urdu": "اگلے دس سال انسانیت کے لیے انتہائی اہم ہیں، کیونکہ کاربن کے اخراج کو کم کیے بغیر ہم آنے والی نسلوں کو ایک محفوظ زمین نہیں دے سکتے۔",
        "future_cap1": "AGLE 10 SAAL KA FAISLA:",
        "future_cap2": "ZAMEEN KO BACHANE KI JANG!",
        "fut_visual_1": "green forest nature sunlight",
        "fut_visual_2": "clean futuristic city",
        "vid_queries": ["climate change", "storm", "solar energy", "nature"]
    },
    {
        "topic": "New Space Race Moon Base Projects and Mars Colonization",
        "tagline": "America, China aur SpaceX ki nayi Space Race: Chand par qabza kiska hoga? 🚀🌕",
        "description": "Chand ke South Pole par barf aur minerals ki talash! NASA Artemis, China aur SpaceX Starship ke darmiyan khala mein nayi superpower jang.",
        "badge": "SPACE RACE 2.0",
        "hook_visual_1": "rocket launch flames",
        "hook_visual_2": "moon surface crater",
        "context_urdu": "انسان ایک بار پھر چاند اور مریخ کی طرف لوٹ رہا ہے، لیکن اس بار مقصد صرف جھنڈا لگانا نہیں بلکہ وہاں مستقل خلائی اڈے اور کارخانے بنانا ہے۔",
        "context_cap1": "CHAND PAR WAPSI:",
        "context_cap2": "MUSTAQIL SPACE BASE KA PLAN!",
        "ctx_visual_1": "astronaut walking moon",
        "ctx_visual_2": "space station orbit",
        "event_urdu": "امریکہ کے آرٹیمس پروگرام، چین کے خلائی مشنز اور سپیس ایکس کے سٹار شپ راکٹ کے درمیان چاند کے جنوبی قطب پر پہنچنے کی سخت دوڑ لگی ہوئی ہے۔",
        "event_cap1": "NASA, CHINA AUR SPACEX:",
        "event_cap2": "MOON SOUTH POLE KI RACE!",
        "evt_visual_1": "heavy rocket launchpad",
        "evt_visual_2": "mission control room",
        "impact_urdu": "چاند کے سدرن پول پر جمی ہوئی برف موجود ہے، جس سے نہ صرف خلا بازوں کے لیے پانی اور آکسیجن بنائی جا سکتی ہے بلکہ راکٹ کا فیول بھی تیار ہو سکتا ہے۔",
        "impact_cap1": "CHAND PAR BARF KHAZANA:",
        "impact_cap2": "OXYGEN AUR ROCKET FUEL BANEGA!",
        "imp_visual_1": "ice crystals microscopic",
        "imp_visual_2": "spaceship refueling space",
        "response_urdu": "اس کے علاوہ چاند کی مٹی میں ہیلیم تھری نامی نایاب عنصر موجود ہے، جو مستقبل میں زمین کی توانائی کی تمام ضروریات پوری کرنے کی صلاحیت رکھتا ہے۔",
        "response_cap1": "HELIUM-3 KA KHAZANA:",
        "response_cap2": "FUTURE ENERGY KA ASLI RAAZ!",
        "res_visual_1": "nuclear fusion reactor",
        "res_visual_2": "planet earth night lights",
        "future_urdu": "جو ملک چاند پر پہلے اپنا بیس قائم کرے گا، وہی مریخ کے سفر اور خلائی معیشت پر اگلی صدی تک حکمرانی کرے گا۔",
        "future_cap1": "SPACE ECONOMY KI JANG:",
        "future_cap2": "AGLI SADI KA SUPERPOWER KON?",
        "fut_visual_1": "planet mars red landscape",
        "fut_visual_2": "futuristic space colony",
        "vid_queries": ["rocket launch", "astronaut", "space", "moon"]
    }
]


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
        with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(used_list[-200:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [!] Could not save used topics: {e}")


def fetch_live_world_news_headlines():
    """Fetches real-time global current affairs headlines from Google News RSS."""
    headlines = []
    rss_urls = [
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
    ]
    for url in rss_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:10]:
                    title_el = item.find("title")
                    if title_el is not None and title_el.text:
                        clean_title = title_el.text.split(" - ")[0].strip()
                        if len(clean_title) > 20 and clean_title not in headlines:
                            headlines.append(clean_title)
        except Exception as e:
            print(f"  [!] RSS fetch note: {e}")
    return headlines[:25]


def discover_gemini_model():
    """Dynamically finds a working Gemini model via REST API so 404 errors never happen."""
    if not GEMINI_API_KEY:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            models = r.json().get("models", [])
            capable = []
            for m in models:
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "")
                if "generateContent" in methods and "gemini" in name.lower():
                    capable.append(name)
            preferred_order = [
                "models/gemini-2.5-flash",
                "models/gemini-2.0-flash",
                "models/gemini-1.5-flash-latest",
                "models/gemini-1.5-flash",
                "models/gemini-2.5-pro",
                "models/gemini-1.5-pro-latest"
            ]
            for pref in preferred_order:
                if pref in capable:
                    return pref
            for c in capable:
                if "flash" in c and "tts" not in c and "image" not in c:
                    return c
            if capable:
                return capable[0]
    except Exception as e:
        print(f"  [!] Gemini model discovery note: {e}")
    return "models/gemini-2.0-flash"


def build_fourteen_scenes_from_template(chosen):
    """Expands a topic template into a full 14-scene (~2 minute) broadcast script."""
    v_queries = chosen.get("vid_queries", ["world news", "technology", "economy", "global"])
    while len(v_queries) < 4:
        v_queries.append("world news")

    return {
        "topic": chosen["topic"],
        "title": f"🌍 {chosen['topic']} | Global Current Affairs",
        "tagline": chosen["tagline"],
        "description": chosen["description"],
        "hashtags": "#GlobalAffairs #WorldNews #CurrentEvents #Geopolitics #UrduNews #GlobalUpdate #TrendingNews #ViralVideo",
        "category_badge": chosen.get("badge", "GLOBAL AFFAIRS"),
        "scenes": [
            {
                "tts_urdu": "اس وقت پوری دنیا میں ایک ایسا بڑا عالمی واقعہ رونما ہو رہا ہے جس کا براہ راست اثر آنے والے دنوں میں ہر ملک کی معیشت اور ہماری روزمرہ زندگی پر پڑنے والا ہے!",
                "caption_part1": "DUNIYA MEIN BARI HALCHAL:",
                "caption_part2": "HAR MULK PAR HOGA ASAR!",
                "search_query_1": chosen["hook_visual_1"],
                "search_query_2": chosen["hook_visual_2"],
                "video_query": v_queries[0]
            },
            {
                "tts_urdu": chosen["context_urdu"],
                "caption_part1": chosen["context_cap1"],
                "caption_part2": chosen["context_cap2"],
                "search_query_1": chosen["ctx_visual_1"],
                "search_query_2": chosen["ctx_visual_2"],
                "video_query": ""
            },
            {
                "tts_urdu": "عالمی طاقتوں کے درمیان وسائل، ٹیکنالوجی اور تجارتی راستوں پر کنٹرول حاصل کرنے کی یہ دوڑ اب ایک نئے اور انتہائی فیصلہ کن مرحلے میں داخل ہو چکی ہے۔",
                "caption_part1": "SUPERPOWERS KI NAYI DOUR:",
                "caption_part2": "FAISLA KUN MARHALA SHURU!",
                "search_query_1": "world map geopolitics",
                "search_query_2": "united nations assembly",
                "video_query": ""
            },
            {
                "tts_urdu": chosen["event_urdu"],
                "caption_part1": chosen["event_cap1"],
                "caption_part2": chosen["event_cap2"],
                "search_query_1": chosen["evt_visual_1"],
                "search_query_2": chosen["evt_visual_2"],
                "video_query": v_queries[1]
            },
            {
                "tts_urdu": "بین الاقوامی میڈیا اور دفاعی تجزیہ کاروں کے مطابق اس فیصلے نے عالمی منڈیوں اور سفارتی تعلقات میں ایک نیا بھونچال پیدا کر دیا ہے۔",
                "caption_part1": "INTERNATIONAL MEDIA REPORT:",
                "caption_part2": "ALAMI MANDIYON MEIN HALCHAL!",
                "search_query_1": "breaking news studio broadcast",
                "search_query_2": "stock exchange trading floor",
                "video_query": ""
            },
            {
                "tts_urdu": chosen["impact_urdu"],
                "caption_part1": chosen["impact_cap1"],
                "caption_part2": chosen["impact_cap2"],
                "search_query_1": chosen["imp_visual_1"],
                "search_query_2": chosen["imp_visual_2"],
                "video_query": v_queries[2]
            },
            {
                "tts_urdu": "جب بھی بڑی طاقتوں کے درمیان ایسی کشیدگی یا پالیسی کی تبدیلی آتی ہے تو اس کی سب سے بڑی قیمت ترقی پذیر ممالک اور عام شہریوں کو چکانی پڑتی ہے۔",
                "caption_part1": "BARI TAQATON KA TAKRAO:",
                "caption_part2": "AAM AADMI PAR SEEDHA BOJH!",
                "search_query_1": "crowded city street people",
                "search_query_2": "global inflation chart",
                "video_query": ""
            },
            {
                "tts_urdu": chosen["response_urdu"],
                "caption_part1": chosen["response_cap1"],
                "caption_part2": chosen["response_cap2"],
                "search_query_1": chosen["res_visual_1"],
                "search_query_2": chosen["res_visual_2"],
                "video_query": ""
            },
            {
                "tts_urdu": "دنیا بھر کے مرکزی بینک، ملٹی نیشنل کمپنیاں اور حکومتیں اب ہنگامی بنیادوں پر اپنی معاشی اور دفاعی حکمت عملی کو تبدیل کر رہی ہیں۔",
                "caption_part1": "GOVERNMENTS AUR BANKS:",
                "caption_part2": "EMERGENCY POLICY SHIFT!",
                "search_query_1": "central bank building",
                "search_query_2": "executives boardroom meeting",
                "video_query": v_queries[3]
            },
            {
                "tts_urdu": "اعداد و شمار بتاتے ہیں کہ پچھلے چند مہینوں کے دوران اس شعبے میں اربوں ڈالرز کی سرمایہ کاری کا رخ بدلا ہے جو مستقبل کے نئے عالمی نظام کا اشارہ ہے۔",
                "caption_part1": "ARBON DOLLARS KI SHIFT:",
                "caption_part2": "NAYE ALAMI NIZAM KA ISHARA!",
                "search_query_1": "financial data screen graphs",
                "search_query_2": "international trade cargo",
                "video_query": ""
            },
            {
                "tts_urdu": chosen["future_urdu"],
                "caption_part1": chosen["future_cap1"],
                "caption_part2": chosen["future_cap2"],
                "search_query_1": chosen["fut_visual_1"],
                "search_query_2": chosen["fut_visual_2"],
                "video_query": ""
            },
            {
                "tts_urdu": "پاکستان اور خطے کے دیگر ممالک کے لیے بھی یہ وقت انتہائی اہم ہے کہ وہ ان عالمی تبدیلیوں کو سمجھیں اور جدید ٹیکنالوجی اور معیشت میں اپنی جگہ بنائیں۔",
                "caption_part1": "PAKISTAN AUR KHITTE KE LIYE:",
                "caption_part2": "WAQT KE SATH BADALNA LAZMI!",
                "search_query_1": "modern city skyline dusk",
                "search_query_2": "young professionals working laptops",
                "video_query": ""
            },
            {
                "tts_urdu": "تاریخ گواہ ہے کہ جو قومیں عالمی حالات اور ٹیکنالوجی کے بدلتے طوفان کو وقت سے پہلے بھانپ لیتی ہیں، وہی مستقبل کی دوڑ میں آگے نکلتی ہیں۔",
                "caption_part1": "TAREEKH KA SABQ:",
                "caption_part2": "JO SAMJHEGA WOHI AAGE JAYEGA!",
                "search_query_1": "globe network connections",
                "search_query_2": "futuristic highway lights",
                "video_query": ""
            },
            {
                "tts_urdu": "دنیا کے ان اہم ترین حالات، جیو پولیٹکس اور گلوبل افیئرز کا روزانہ آسان زبان میں تجزیہ دیکھنے کے لیے ہمارے چینل کو ابھی سبسکرائب اور فالو کر لیں!",
                "caption_part1": "DAILY GLOBAL AFFAIRS KE LIYE:",
                "caption_part2": "ABHI SUBSCRIBE AUR FOLLOW KAREIN!",
                "search_query_1": "smartphone social media notification",
                "search_query_2": "world news studio",
                "video_query": ""
            }
        ]
    }


def generate_script_via_gemini(used_topics):
    """Uses Gemini REST API + Live Google News RSS to generate a fresh 14-scene (2-minute) script."""
    if not GEMINI_API_KEY:
        return None

    model_name = discover_gemini_model()
    if not model_name:
        return None

    live_headlines = fetch_live_world_news_headlines()
    print(f"🧠 Generating 2-Minute Global Affairs Script via {model_name}...")

    prompt = f"""You are an elite international news producer creating a 2-minute (14-scene) video on a MAJOR CURRENT GLOBAL EVENT.
Today's live global news headlines for inspiration:
{json.dumps(live_headlines, ensure_ascii=False)}

CRITICAL RULE: Do NOT pick any topic already in this used list:
{json.dumps(used_topics[-60:], ensure_ascii=False)}

Pick ONE major ongoing global affair (geopolitics, global economy, tech war, energy crisis, space race, climate event, or international trade).
Return ONLY a raw, valid JSON object with NO markdown formatting and NO code fences, matching this EXACT schema:
{{
  "topic": "Unique concise English topic title",
  "title": "🌍 Catchy Roman Urdu Title | Global Update",
  "tagline": "Engaging 1-line Roman Urdu hook with emojis",
  "description": "2-3 sentence Roman Urdu summary of the global event and why it matters.",
  "hashtags": "#GlobalAffairs #WorldNews #Geopolitics #UrduNews #CurrentEvents #Viral",
  "category_badge": "SHORT 2-3 WORD ENGLISH BADGE (e.g. GLOBAL CRISIS)",
  "scenes": [
    {{
      "tts_urdu": "Must be written in REAL URDU SCRIPT (اردو رسم الخط) around 22 to 28 words so TTS speaks naturally for ~8.5 seconds.",
      "caption_part1": "SHORT UPPERCASE ROMAN URDU LINE 1 (MAX 24 CHARS)",
      "caption_part2": "SHORT UPPERCASE ROMAN URDU LINE 2 (MAX 24 CHARS)",
      "search_query_1": "2-3 word English stock photo keyword",
      "search_query_2": "2-3 word English stock photo keyword",
      "video_query": "2 word English stock video keyword (or empty string)"
    }}
  ]
}}
Ensure the `scenes` array has EXACTLY 14 scenes so the total video duration is 2 minutes (~120 seconds)."""

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.75,
            "responseMimeType": "application/json"
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=45)
        if resp.status_code != 200:
            del payload["generationConfig"]["responseMimeType"]
            resp = requests.post(url, json=payload, timeout=45)

        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                script_data = json.loads(raw_text.strip())
                scenes = script_data.get("scenes", [])
                if script_data.get("topic") and len(scenes) >= 10:
                    print(f"  [✓] Gemini generated 2-min script ({len(scenes)} scenes): {script_data['topic']}")
                    return script_data
        else:
            print(f"  [!] Gemini API status {resp.status_code}: {resp.text[:160]}")
    except Exception as e:
        print(f"  [!] Gemini generation fallback note: {e}")

    return None


def generate_script_data():
    used = load_used_topics()

    # 1. Try live Gemini + Google News RSS generation first
    ai_script = generate_script_via_gemini(used)
    if ai_script:
        used.append(ai_script["topic"])
        save_used_topics(used)
        return ai_script

    # 2. Bulletproof fallback to built-in 14-scene (2-minute) Global Current Affairs scripts
    available = [t for t in FALLBACK_GLOBAL_TOPICS if t["topic"] not in used]
    if not available:
        used = []
        available = FALLBACK_GLOBAL_TOPICS

    chosen = random.choice(available)
    used.append(chosen["topic"])
    save_used_topics(used)
    print(f"🔥 Building 2-Minute (14-Scene) Global Affairs Script for: {chosen['topic']}")
    return build_fourteen_scenes_from_template(chosen)


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
