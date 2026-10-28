import os
import json
import random
import asyncio
import subprocess
import urllib.parse
import textwrap
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import google.generativeai as genai
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# YouTube API Credentials
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

USED_TOPICS_FILE = "used_topics.json"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
USED_MEDIA_URLS = set()

def get_gemini_script():
    used_topics = []
    if os.path.exists(USED_TOPICS_FILE):
        try:
            with open(USED_TOPICS_FILE, "r") as f:
                used_topics = json.load(f)
        except Exception:
            pass

    print("🧠 Contacting Gemini AI for a New Global Event Script...")
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Auto-Detect Available Model to prevent 404 Errors
    selected_model_name = 'gemini-1.5-flash' # Default fallback
    try:
        available_models = genai.list_models()
        for m in available_models:
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini-1.5-flash' in m.name:
                    selected_model_name = m.name
                    break
                elif 'gemini-pro' in m.name or 'gemini-1.5-pro' in m.name:
                    selected_model_name = m.name
    except Exception as e:
        print(f"Model auto-detect issue (using fallback): {e}")

    print(f"✅ Successfully selected AI Model: {selected_model_name}")
    model = genai.GenerativeModel(selected_model_name)
    
    prompt = f"""
    You are an expert YouTube scriptwriter and video producer. 
    Your task is to write a highly engaging, 2-minute video script about a VERY RECENT or ONGOING IMPORTANT GLOBAL EVENT (e.g., Geopolitics, Global Economy, Major Tech News, International Conflicts, Space Discoveries).
    
    CRITICAL: DO NOT use any of these previously covered topics: {used_topics}. Pick a fresh topic!
    
    Length: The video needs to be around 2 minutes. This means you must generate EXACTLY 14 to 16 scenes.
    Language: The 'tts_urdu' narration MUST be in fluent Roman Urdu (Urdu written in English alphabets).
    
    Output Format: You MUST return ONLY a raw, valid JSON object (no markdown, no backticks, no code blocks). 
    Use this exact structure:
    {{
        "topic": "English topic name (e.g., Middle East Crisis 2024)",
        "badge": "SHORT BADGE (e.g., GLOBAL NEWS)",
        "title": "Catchy YouTube Title",
        "tagline": "A powerful hook/tagline",
        "description": "YouTube description text",
        "hashtags": "#News #Global #Update",
        "scenes": [
            {{
                "tts_urdu": "Roman Urdu narration for this scene (around 15-25 words)",
                "caption_part1": "SHORT CAPTION 1 (UPPERCASE)",
                "caption_part2": "SHORT CAPTION 2 (UPPERCASE)",
                "search_query_1": "stock photo search term 1 (english)",
                "search_query_2": "stock photo search term 2 (english)",
                "video_query": "stock video search term (english, optional)"
            }}
        ]
    }}
    """
    
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
        
    script_data = json.loads(raw_text.strip())
    
    # Save topic to memory
    used_topics.append(script_data["topic"])
    with open(USED_TOPICS_FILE, "w") as f:
        json.dump(used_topics, f, indent=2)
        
    return script_data

def fetch_contextual_stock_video(query, filename):
    if not query or not PIXABAY_API_KEY:
        return None
    try:
        encoded = urllib.parse.quote(query.strip())
        p_url = f"[https://pixabay.com/api/videos/?key=](https://pixabay.com/api/videos/?key=){PIXABAY_API_KEY}&q={encoded}&safesearch=true&per_page=10"
        r = requests.get(p_url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                vid_url = hit.get("videos", {}).get("medium", {}).get("url")
                if vid_url and vid_url not in USED_MEDIA_URLS:
                    USED_MEDIA_URLS.add(vid_url)
                    vr = requests.get(vid_url, headers=HEADERS, timeout=30)
                    if vr.status_code == 200 and len(vr.content) > 50000:
                        with open(filename, "wb") as f:
                            f.write(vr.content)
                        return filename
    except Exception:
        pass
    return None

def fetch_exact_scene_photo(query, filename):
    if PIXABAY_API_KEY:
        try:
            encoded = urllib.parse.quote(query.strip())
            p_url = f"[https://pixabay.com/api/?key=](https://pixabay.com/api/?key=){PIXABAY_API_KEY}&q={encoded}&image_type=photo&safesearch=true&per_page=15"
            r = requests.get(p_url, headers=HEADERS, timeout=18)
            if r.status_code == 200:
                for hit in r.json().get("hits", []):
                    img_url = hit.get("largeImageURL")
                    if img_url and img_url not in USED_MEDIA_URLS:
                        USED_MEDIA_URLS.add(img_url)
                        img_r = requests.get(img_url, headers=HEADERS, timeout=15)
                        if img_r.status_code == 200:
                            with open(filename, "wb") as f:
                                f.write(img_r.content)
                            return filename
        except Exception:
            pass
    # Fallback solid color if nothing found
    img = Image.new("RGB", (1080, 1920), (22, 28, 42))
    img.save(filename, "JPEG")
    return filename

def create_burned_hud_overlay(caption_text, badge_text, scene_idx, total_scenes, part_num):
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Vignette
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

    # Badge
    bw, bh = 620, 82
    bx, by = (1080 - bw) // 2, 95
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=41, fill=(220, 30, 30, 250), outline=(255, 255, 255, 240), width=4)
    b_text = badge_text.upper()
    b_bbox = draw.textbbox((0, 0), b_text, font=badge_font)
    draw.text((bx + (bw - (b_bbox[2]-b_bbox[0])) // 2, by + (bh - (b_bbox[3]-b_bbox[1])) // 2 - 4), b_text, font=badge_font, fill=(255, 255, 255, 255))

    # Caption
    lines = textwrap.wrap(caption_text.upper(), width=15)
    if not lines: lines = ["GLOBAL UPDATE!"]

    line_height = 92
    total_text_h = len(lines) * line_height
    box_y1 = 1360 - (total_text_h // 2)
    
    draw.rounded_rectangle([55, box_y1, 1025, box_y1 + total_text_h + 44], radius=28, fill=(10, 12, 18, 230), outline=(255, 215, 0, 220), width=4)

    for i, line in enumerate(lines):
        t_bbox = draw.textbbox((0, 0), line, font=cap_font)
        tx = (1080 - (t_bbox[2]-t_bbox[0])) // 2
        ty = box_y1 + 20 + (i * line_height)
        fill_col = (255, 230, 0, 255) if (part_num==1 and i==0) or (part_num==2 and i!=0) else (255, 255, 255, 255)
        if part_num == 2 and i == 0: fill_col = (0, 255, 150, 255)
        
        for dx, dy in [(-4, -4), (4, -4), (-4, 4), (4, 4), (0, 5)]:
            draw.text((tx + dx, ty + dy), line, font=cap_font, fill=(0, 0, 0, 255))
        draw.text((tx, ty), line, font=cap_font, fill=fill_col)

    # Progress bar
    prog_w = int(980 * ((scene_idx + (0.5 if part_num == 1 else 1.0)) / total_scenes))
    draw.rounded_rectangle([50, 1835, 1030, 1855], radius=10, fill=(255, 255, 255, 75))
    draw.rounded_rectangle([50, 1835, 50 + max(prog_w, 25), 1855], radius=10, fill=(255, 215, 0, 255))

    out_png = f"hud_{scene_idx}_p{part_num}.png"
    overlay.save(out_png)
    return out_png

async def synthesize_scene_voice(urdu_text, index):
    raw = f"raw_voice_{index}.mp3"
    out = f"voice_{index}.m4a"
    communicate = edge_tts.Communicate(urdu_text, voice="ur-PK-AsadNeural", rate="+14%", pitch="-2Hz")
    await communicate.save(raw)
    subprocess.run(["ffmpeg", "-y", "-i", raw, "-ar", "44100", "-ac", "2", "-c:a", "aac", out], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def get_audio_dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path])
    return max(float(out.decode().strip()), 3.0)

def make_subclip(media_path, is_video, overlay_path, duration, out_clip):
    vf = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
    cmd = ["ffmpeg", "-y"]
    if is_video:
        cmd += ["-stream_loop", "-1", "-t", str(duration), "-i", media_path]
    else:
        cmd += ["-loop", "1", "-t", str(duration), "-i", media_path]
    
    cmd += ["-loop", "1", "-t", str(duration), "-i", overlay_path, "-filter_complex", vf, "-map", "[v]", "-r", "24", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", out_clip]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def render_scene(scene, idx, total, badge):
    audio = asyncio.run(synthesize_scene_voice(scene["tts_urdu"], idx))
    dur = get_audio_dur(audio)
    
    v_q = scene.get("video_query", "")
    vid_file = fetch_contextual_stock_video(v_q, f"vid_{idx}.mp4") if v_q else None
    m1, is_v1 = (vid_file, True) if vid_file else (fetch_exact_scene_photo(scene.get("search_query_1",""), f"p_{idx}_1.jpg"), False)
    m2, is_v2 = (fetch_exact_scene_photo(scene.get("search_query_2",""), f"p_{idx}_2.jpg"), False)

    sub1, sub2 = f"sub_{idx}_1.mp4", f"sub_{idx}_2.mp4"
    make_subclip(m1, is_v1, create_burned_hud_overlay(scene["caption_part1"], badge, idx, total, 1), round(dur/2, 2), sub1)
    make_subclip(m2, is_v2, create_burned_hud_overlay(scene["caption_part2"], badge, idx, total, 2), round(dur - dur/2, 2), sub2)

    list_f = f"list_{idx}.txt"
    with open(list_f, "w") as f: f.write(f"file '{sub1}'\nfile '{sub2}'\n")
    
    out = f"scene_{idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_f, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-shortest", out], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def build_video(data):
    scenes = data["scenes"]
    files = [render_scene(s, i, len(scenes), data.get("badge", "NEWS")) for i, s in enumerate(scenes)]
    with open("master.txt", "w") as f:
        for sf in files: f.write(f"file '{sf}'\n")
    
    raw = "raw_reel.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "master.txt", "-c:v", "copy", "-c:a", "aac", raw], check=True)
    subprocess.run(["cp", raw, "final_reel.mp4"], check=False)
    return "final_reel.mp4"

def get_youtube_service():
    creds = google.oauth2.credentials.Credentials(
        None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET
    )
    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(video_path, data):
    if not YOUTUBE_REFRESH_TOKEN:
        return False, "YouTube Credentials Missing"
        
    print("🚀 Uploading to YouTube...")
    try:
        youtube = get_youtube_service()
        body = {
            "snippet": {
                "title": data["title"],
                "description": data["description"] + "\n\n" + data["hashtags"],
                "tags": data["hashtags"].replace("#", "").split(),
                "categoryId": "25" # News & Politics
            },
            "status": {
                "privacyStatus": "public",  # Can be 'public', 'private', or 'unlisted'
                "madeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        
        vid_id = response.get('id')
        return True, f"Uploaded! Link: [https://youtube.com/watch?v=](https://youtube.com/watch?v=){vid_id}"
    except Exception as e:
        print(f"YouTube Error: {e}")
        return False, str(e)[:150]

def send_to_telegram(video_path, script_data, yt_ok, yt_msg):
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_BOT_TOKEN}/sendVideo"
    status = f"✅ YouTube Post: {yt_msg}" if yt_ok else f"⚠️ YouTube Post: {yt_msg}"
    cap = f"🔥 {script_data.get('title')}\n\n{status}"[:1000]
    
    with open(video_path, "rb") as vf:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": cap}, files={"video": vf})

if __name__ == "__main__":
    script = get_gemini_script()
    print(f"Targeting Topic: {script['topic']}")
    final = build_video(script)
    yt_ok, yt_msg = upload_to_youtube(final, script)
    send_to_telegram(final, script, yt_ok, yt_msg)
