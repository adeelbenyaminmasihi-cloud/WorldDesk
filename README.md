# YouTube Global Events Video Bot

Yeh bot automatically daily global events (news, geopolitics, tech) par YouTube Shorts/Videos generate karta hai aur upload karta hai.
Din mein 5 dafa run hone ke liye configure kiya gaya hai.

## 🚀 Setup Instructions

1. **GitHub Secrets:**
   Aapko apne GitHub repository ke `Settings > Secrets and variables > Actions` mein ja kar yeh secrets add karne hain:
   - `GEMINI_API_KEY`: AI script generation ke liye.
   - `PIXABAY_API_KEY`: HD Videos/Photos ke liye.
   - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Updates aur video backup lene ke liye.
   - `YOUTUBE_CLIENT_ID`: YouTube API OAuth Client ID.
   - `YOUTUBE_CLIENT_SECRET`: YouTube API OAuth Secret.
   - `YOUTUBE_REFRESH_TOKEN`: YouTube upload permission token.

2. **YouTube API Setup:**
   Aapko Google Cloud Console se YouTube Data API v3 enable karni hogi aur OAuth 2.0 Client ID generate karna hoga. Uske baad locally login kar ke Refresh Token generate karna hoga taake GitHub Actions background mein automatically upload kar sake.

3. **Workflow Start:**
   Ek dafa secrets add ho jayen, toh "Actions" tab mein ja kar workflow manually run kar sakte hain, ya phir cron schedule par automatically chalne dein.
