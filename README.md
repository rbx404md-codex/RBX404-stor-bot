# Digital Store Bot — RBX404 Premium Emoji Store

Telegram-এ ফাইল/ভিডিও/ডকুমেন্ট বিক্রির বট। আসল ফাইল কখনো সার্ভার/ফোনে জমা থাকে
না — সব থাকে একটা প্রাইভেট **Storage Channel**-এ। ডাটাবেজও নিয়মিত অটোমেটিক
একটা প্রাইভেট **Backup Channel**-এ ব্যাকআপ হয়, তাই Termux বন্ধ হলে বা নতুন
হোস্টে (Railway/VPS) সরিয়ে নিলেও ডেটা হারায় না।

## ফিচার (সম্পূর্ণ)
- Welcome message + welcome image (`assets/welcome.jpg` বসিয়ে দিন)
- ক্যাটাগরি + প্রোডাক্ট ব্রাউজিং, প্রতিটি প্রোডাক্টে ঐচ্ছিক 🔍 Preview/Sample ফাইল
- 🪙 Coin Wallet (ম্যানুয়াল bKash/Nagad টপ-আপ request, অ্যাডমিন অ্যাপ্রুভ/রিজেক্ট)
- 💳 Top-up request history, duplicate Transaction ID protection, user notification
- ⭐ Telegram Stars-এ সরাসরি পেমেন্ট (auto verify + auto delivery)
- 🎟️ Coupon system (percent / fixed-coin discount)
- 🎁 Referral system (unique link, প্রথম কেনাকাটায় রেফারারকে কয়েন রিওয়ার্ড)
- 📚 Purchased Library / re-download
- 👑 Admin panel: প্রোডাক্ট অ্যাড (+ Preview আপলোড), প্রোডাক্ট লিস্ট/Enable-Disable,
  ক্যাটাগরি অ্যাড, কয়েন ম্যানেজ, Top-up review, কুপন তৈরি, ব্যান/আনব্যান,
  সেলস স্ট্যাটস, ম্যানুয়াল ব্যাকআপ
- ℹ️ `/help` এবং Telegram-এর command menu-তে built-in command list
- `/cancel` — যেকোনো মাল্টি-স্টেপ ফ্লো (যেমন প্রোডাক্ট অ্যাড করার মাঝপথে) থেকে বের হওয়ার কমান্ড
- 💾 Auto DB backup (pinned message) + auto restore on boot
- 🛡️ গ্লোবাল এরর হ্যান্ডলার — কোনো একটা মেসেজে বাগ থাকলেও পুরো বট ক্র্যাশ করবে না
- 🔄 Watchdog script (Termux ক্র্যাশ রিকভারি)
- 📌 Force Join gate — নির্দিষ্ট Channel-এ Join না করলে user access বন্ধ
- 🧰 Product tools — নাম/description/price edit, Featured toggle, safe archive/delete
- 🔎 Product search, Featured-first result এবং wishlist
- ❤️ Wishlist add/remove ও saved product list
- ⭐ Buyer-only rating/review এবং product rating summary
- 🎁 Daily check-in bonus (একই দিনে duplicate claim বন্ধ)
- 🏆 Referral leaderboard
- 🆘 Support ticket — admin reply করলে ticket auto-close ও user notification
- 📢 Admin broadcast to all non-banned users
- 🛠️ Maintenance mode
- 📋 Improved purchase history with one-click re-download এবং review entry
- 🧾 FAQ, terms/privacy guidance এবং richer Help menu
- 🎨 সব user-visible message/caption-এ Telegram custom emoji layer; ID না থাকলে Unicode fallback
- 🔗 Universal `/linkgen` for text, documents, photos, video, audio, voice and GIF with opaque tokens
- 🌐 Mini web portal with password/expiry/view-limit/one-time link options and download proxy
- ♻️ Membership cache + referral status revalidation (`pending`, `active`, `left`, `invalid`)
- 🌐 User language selector (বাংলা, English, हिन्दी, اردو, Русский, العربية)
- 🛡️ Per-user rate limiting, mute/premium profile flags, and activity retention cleanup
- 📊 Expanded admin analytics with active users, recent orders, active links, and top products
- 🧾 Idempotent Telegram Stars order recording using the Telegram charge ID
- 🔁 Admin-only `/user`, `/mute`, `/premium`, and one-time `/refund ORDER_ID` tools
- 📢 Broadcast text, photo, video, document, audio, and GIF messages
- 🐳 Docker Compose deployment with a persistent data volume and health check
- ♻️ Portable Linux watchdog runner (`watchdog.sh`) alongside the Termux-compatible `run.sh`

## সেটআপ (Termux / VPS / যেকোনো জায়গায় একই ধাপ)

1. **দুটো প্রাইভেট Telegram চ্যানেল বানান:**
   - একটা Storage Channel (আসল ফাইল থাকবে)
   - একটা Backup Channel (DB ব্যাকআপ থাকবে)
   - দুটো চ্যানেলেই বটকে **Admin** বানান (Post + Pin permission সহ)
   - চ্যানেলের numeric ID বের করতে চ্যানেলে যেকোনো মেসেজ ফরওয়ার্ড করুন
     [@userinfobot](https://t.me/userinfobot)-এ, অথবা @RawDataBot ব্যবহার করুন

2. **রিপো ক্লোন করুন:**
   ```bash
   git clone <your-private-repo-url>
   cd bot-project
   pip install -r requirements.txt
   ```

3. **`.env` বানান:**
   ```bash
   cp .env.example .env
   nano .env   # BOT_TOKEN, ADMIN_IDS, STORAGE_CHANNEL_ID, BACKUP_CHANNEL_ID বসান
   ```

   Top-up তথ্য পরিবর্তন করতে চাইলে এই optional values ব্যবহার করুন:
   ```env
   ADMIN_USERNAME=RBX404
   BKASH_NUMBER=01838372430
   NAGAD_NUMBER=01732466920
    DAILY_CHECKIN_REWARD=10
    # Optional: valid Telegram custom emoji document IDs.
    # One shared ID is enough; role-specific IDs can override it.
    CUSTOM_EMOJI_ID=
    CUSTOM_EMOJI_BRAND_ID=
    CUSTOM_EMOJI_SUCCESS_ID=
    CUSTOM_EMOJI_ERROR_ID=
    CUSTOM_EMOJI_STORE_ID=
    CUSTOM_EMOJI_WALLET_ID=
    CUSTOM_EMOJI_REFERRAL_ID=
    CUSTOM_EMOJI_HELP_ID=
    CUSTOM_EMOJI_SECURITY_ID=
    CUSTOM_EMOJI_SUPPORT_ID=
    CUSTOM_EMOJI_ADMIN_ID=
   ```

4. **চালান:**
   ```bash
   python main.py
   ```
   প্রথমবার চালু হলে এটি:
   - Backup channel-এ পিন করা ব্যাকআপ থাকলে সেটা restore করবে
   - না থাকলে fresh ডাটাবেজ বানাবে (টেবিল অটো তৈরি)

## Termux-এ ২৪/৭ চালানো

```bash
termux-wake-lock
chmod +x run.sh
tmux new -s bot
./run.sh
```

`run.sh` একটা watchdog — বট ক্র্যাশ করলে ৫ সেকেন্ড পর নিজে থেকেই আবার চালু হয়ে
যাবে। `tmux` সেশনে রাখলে Termux অ্যাপ বন্ধ করলেও বট চলতে থাকবে (`tmux detach` =
Ctrl+B তারপর D)। এছাড়া Android Settings থেকে Termux-কে Battery Optimization
থেকে বাদ দিন, নাহলে ফোন নিজেই প্রসেস মেরে ফেলতে পারে।

## Railway-তে migrate করলে
- একই কোডবেস, শুধু Railway-তে Environment Variables ট্যাবে `.env`-এর ভ্যালুগুলো বসান
- `Procfile` আগে থেকেই আছে (`worker: python main.py`)
- Railway-এর ডিস্ক ephemeral — কিন্তু backup/restore সিস্টেম থাকায় প্রতিবার
  redeploy-তে backup channel থেকে ডেটা ফিরে আসবে, তাই আলাদা Volume লাগবে না

## অ্যাডমিন কমান্ড
- `/admin` — অ্যাডমিন প্যানেল খুলুন
- `💳 Top-up Requests` — Pending payment খুলে Transaction ID যাচাই করুন
- `✅ Approve & Add Coins` — request-এর চাওয়া Coin একবারে Wallet-এ যোগ করুন
- `❌ Reject` — ভুল/অযাচাইকৃত payment বাতিল করুন
- `📌 Force Join` — Required Channel add/remove করুন
- `🧰 Manage Products` — product select করে edit, price change, feature বা archive করুন
- `📢 Broadcast` — সব active user-কে plain-text announcement পাঠান
- `🛠 Maintenance` — সাময়িকভাবে user access বন্ধ/চালু করুন
- `🆘 Support Tickets` — user ticket দেখে reply ও close করুন

## ইউজার Top-up flow
1. `Wallet` → `➕ Top-up (Coin)` চাপুন
2. bKash অথবা Nagad বেছে নিন
3. bKash/Nagad-এর নম্বরে **Send Money** করুন
4. Paid amount, requested Coin এবং Transaction ID দিন
5. Admin যাচাই করলে Approved/Rejected notification পাবেন
6. Approved হলে Coin স্বয়ংক্রিয়ভাবে Wallet-এ যোগ হবে

User-facing payment screen-এ Admin-এর Telegram username `@RBX404` দেখানো হয়;
Admin-এর numeric chat ID user-কে দেখানো হয় না।

## গুরুত্বপূর্ণ নিরাপত্তা নোট
- `.env` কখনো git push করবেন না (এমনকি প্রাইভেট রিপো হলেও) — `.gitignore`-এ আগে থেকেই বাদ দেওয়া আছে
- শুধু `ADMIN_IDS`-এ থাকা Telegram ID-গুলোই admin ফিচার ব্যবহার করতে পারবে
- Bot token source code বা ZIP-এ রাখা হয় না; Replit Secrets/hosting secret manager-এ `BOT_TOKEN` নামে সেট করুন।
  পুরোনো কোনো token প্রকাশিত হয়ে থাকলে BotFather থেকে revoke করে নতুন token ব্যবহার করুন।
- `BASE_URL` সেট করলে generated links সরাসরি public mini-portal URL হবে
- এই project aiogram-এর Telegram Bot API ব্যবহার করে। তাই `API_ID`/`API_HASH` যোগ করার দরকার নেই; এগুলো MTProto userbot/client-এর জন্য এবং এই bot-এর maintenance/security surface অযথা বাড়ায়

### Custom emoji setup

Telegram custom emoji ব্যবহার করতে Telegram থেকে একটি valid custom emoji document ID নিন এবং
`CUSTOM_EMOJI_ID`-এ বসান। নির্দিষ্ট UI category-তে আলাদা emoji চাইলে role-specific variable
ব্যবহার করুন। Message/caption-এ custom entity render হবে; inline button label-এ Bot API entity
parsing না থাকায় Unicode fallback রাখা হয়েছে।

## Force Join setup

Admin Panel → `📌 Force Join` থেকে Channel-এর numeric ID, display name এবং
`https://t.me/...` invite link দিন। Bot-কে সেই Channel-এ admin করে রাখুন, যাতে
membership verify করতে পারে। কোনো channel আর required না হলে একই menu থেকে remove
করুন।

## Product delete behavior

Order history এবং delivery record নষ্ট না করার জন্য Delete button product-কে
**archive** করে (`is_active=0`)। Archived product নতুন করে Store-এ দেখা বা কেনা যায়
না, কিন্তু পুরনো order থেকে re-download করা যায়।
