# PIXEL Game Zone - Turnir Ro'yxatdan O'tish Bot & Web App
Ushbu loyiha **PIXEL Game Zone** kompyuter klubi uchun maxsus ishlab chiqilgan bo'lib, u Telegram Bot va unga integratsiya qilingan vizual Web App (Mini App) yordamida o'yinchilarni turnirlarga (CS2, CS 1.6 va boshqalar) ro'yxatga oladi hamda admin panel orqali barcha jarayonlarni boshqarish imkonini beradi.
## Loyiha Imkoniyatlari
*   **Vizual Web App**: Bot ichida ochiladigan neon o'yin uslubidagi (Dark purple & Cyan) chiroyli interfeys.
*   **5 kishilik Jamoa Ro'yxati**: Jamoa nomi, Sardor ismi, telefoni va qolgan 4 ta o'yinchi ma'lumotlarini qulay shaklda yig'ish.
*   **Slotlar Nazorati**: Belgilangan limit to'lishi bilan adminga avtomatik xabar yuborish.
*   **Visual Admin Panel**:
    *   Statistika (jami turnirlar, faol slotlar, jamoalar va ishtirokchilar soni).
    *   Yangi turnirlar (o'yinlar) yaratish va ularni yopish.
    *   Ro'yxatdan o'tgan jamoalarni ko'rish va Excel/CSV formatida yuklab olish.
    *   Qo'shimcha adminlarni Chat ID va Ism orqali qo'shish/o'chirish (tugma shaklida boshqariladi).
    *   Bot foydalanuvchilariga yoki ma'lum bir turnir ishtirokchilariga xabar tarqatish (Mailing).
*   **Telegram Xavfsizligi**: Barcha API so'rovlari Telegram Web App `initData` orqali backend-da shifrlangan holda tekshiriladi. Begona foydalanuvchilar admin panelga kira olmaydi.
---
## GitHub-dan loyihani yuklab olgandan so'ng ishga tushirish qadamlari
Loyihani o'z kompyuteringiz yoki serveringizda ishga tushirish uchun quyidagi ketma-ketlikni bajaring:
### 1. Talablar
Kompyuteringizda quyidagilar o'rnatilgan bo'lishi kerak:
*   **Python 3.8+** (o'rnatish paytida `Add Python to PATH` belgisini yoqishni unutmang)
*   **Git** (kodni yuklash va boshqarish uchun)
*   **ngrok** (Web App lokal ishga tushirilganda Telegram-da ochilishi uchun HTTPS manzili kerak)
### 2. Loyihani yuklab olish (Clone)
Terminal yoki CMD-ni ochib, quyidagi buyruqni kiriting:
```bash
git clone <Sizning_GitHub_Repo_Manzilingiz>
cd pixel-bot
```
### 3. Kutubxonalarni o'rnatish
Loyiha papkasida terminal orqali kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```
### 4. `.env` faylini sozlash
Loyiha papkasida `.env` deb nomlangan fayl yarating (agar yo'q bo'lsa) va ichiga quyidagi ma'lumotlarni yozing:
```env
BOT_TOKEN=8305340326:AAEZEWUm9va5l_-nUbyGEZnNUT0i385RXcU
MAIN_ADMIN_ID=8485164743
PORT=5000
HOST=0.0.0.0
WEBAPP_URL=https://your-ngrok-subdomain.ngrok-free.app
```
*   `BOT_TOKEN`: Telegram `@BotFather` bergan token.
*   `MAIN_ADMIN_ID`: Sizning shaxsiy Telegram Chat ID-ingiz (asosiy admin).
*   `WEBAPP_URL`: ngrok orqali olinadigan vaqtincha HTTPS havola (keyingi qadamda ko'rsatilgan).
### 5. ngrok orqali HTTPS tunnel ochish
Telegram Web App faqat xavfsiz **HTTPS** manzillar bilan ishlaydi. Botni lokal (o'z kompyuteringizda) ishga tushirganda ngrok-dan foydalanamiz:
1.  ngrok-ni yuklab oling va ro'yxatdan o'ting.
2.  Terminalda quyidagi buyruqni ishga tushiring:
    ```bash
    ngrok http 5000
    ```
3.  Terminalda paydo bo'lgan `Forwarding` qismidagi `https://...` bilan boshlanuvchi manzilni nusxalang.
4.  Ushbu nusxalangan manzilni `.env` faylidagi `WEBAPP_URL` qismiga yozib saqlang (masalan: `WEBAPP_URL=https://1234-56-78.ngrok-free.app`).
### 6. Botni ishga tushirish
Terminalda quyidagi buyruqni kiriting:
```bash
python bot.py
```
Agar hammasi to'g'ri bo'lsa, konsolda quyidagi yozuvlar chiqadi:
```text
---------------------------------------------
[*] PIXEL Game Zone bot & server ishga tushmoqda...
[*] Web App manzili: https://your-ngrok-subdomain.ngrok-free.app
[*] Asosiy Admin ID: 8485164743
---------------------------------------------
```
---
## Telegram Botda Web App Tugmalarini Sozlash (BotFather orqali)
Bot ichida Web App to'g'ri ochilishi uchun BotFather-da menyu tugmasini ulashimiz kerak:
1.  Telegram-da `@BotFather` botiga kiring.
2.  `/mybots` buyrug'ini yuboring va o'z botingizni tanlang.
3.  **Bot Settings** -> **Menu Button** -> **Configure Menu Button** qismiga kiring.
4.  BotFather-ga ngrok bergan HTTPS manzilingizni yuboring (masalan: `https://1234-56-78.ngrok-free.app/`).
5.  Tugma nomini kiriting: `📝 Ro'yxatdan O'tish`.
6.  Endi botingizga kirsangiz, chap pastki burchakda menyu tugmasi Web App ko'rinishida paydo bo'ladi.
*Eslatma: Inline tugmalar bot ishga tushganda `/start` bosilganda avtomatik ravishda `.env` faylidagi `WEBAPP_URL` manzili bilan sozlanadi.*
