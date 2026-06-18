import os
import json
import urllib.parse
import hmac
import hashlib
import threading
from flask import Flask, render_template, jsonify, request, send_from_directory
from telebot import TeleBot, types
from dotenv import load_dotenv
# Load database and environment variables
from database import Database
load_dotenv()
db = Database()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN_ID = os.getenv("MAIN_ADMIN_ID")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:5000")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi. .env faylini tekshiring.")
if not MAIN_ADMIN_ID:
    raise ValueError("MAIN_ADMIN_ID topilmadi. .env faylini tekshiring.")
# Initialize Bot
bot = TeleBot(BOT_TOKEN)
# Initialize Flask App
app = Flask(__name__, static_folder="static", template_folder="templates")
# --- TELEGRAM WEBAPP SIGNATURE VALIDATION ---
def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Validates Telegram WebApp initData to ensure requests are authentic.
    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data))
        hash_val = parsed.pop('hash', None)
        if not hash_val:
            return None
        
        # Sort key-value pairs alphabetically
        sorted_params = sorted(parsed.items())
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_params])
        
        # Calculate secret key: HMAC-SHA256(token, "WebAppData")
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Calculate expected hash: HMAC-SHA256(data_check_string, secret_key)
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calc_hash == hash_val:
            # Parse user object if exists
            user_data = parsed.get('user')
            if user_data:
                parsed['user'] = json.loads(user_data)
            return parsed
        return None
    except Exception as e:
        print(f"Verify Init Data Error: {e}")
        return None
def get_authorized_user(headers):
    """Helper to check authorization header and return user dict if valid."""
    init_data = headers.get('X-Telegram-Init-Data')
    if not init_data:
        return None
    return verify_telegram_init_data(init_data)
# --- FLASK WEB SERVER ENDPOINTS ---
@app.route('/')
def index_route():
    return render_template("index.html")
@app.route('/admin-panel')
def admin_route():
    return render_template("admin.html")
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)
# --- USER APIS ---
@app.route('/api/tournaments', methods=['GET'])
def get_tournaments_api():
    tournaments = db.get_active_tournaments()
    return jsonify(tournaments)
@app.route('/api/register', methods=['POST'])
def register_team_api():
    # Authenticate
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Avtorizatsiyadan o'tish amalga oshmadi."}), 401
    
    tg_user_id = user_info['user']['id']
    data = request.json
    
    tournament_id = data.get('tournament_id')
    team_name = data.get('team_name')
    captain_name = data.get('captain_name')
    captain_phone = data.get('captain_phone')
    members = data.get('members') # List of 4 member names
    
    if not all([tournament_id, team_name, captain_name, captain_phone]) or len(members) != 4:
        return jsonify({"error": "Barcha maydonlar to'liq to'ldirilishi shart."}), 400
        
    success, res = db.register_team(
        tournament_id=tournament_id,
        team_name=team_name,
        captain_name=captain_name,
        captain_phone=captain_phone,
        members_list=members,
        user_id=tg_user_id
    )
    
    if not success:
        return jsonify({"error": res}), 400
        
    # If tournament is now full, notify admins
    if res.get("is_now_full"):
        game_name = res.get("game_name")
        total_slots = res.get("total_slots")
        notify_message = (
            f"🚨 **DIQQAT! SLON TO'LDI!**\n\n"
            f"🎮 **O'yin**: {game_name}\n"
            f"📊 **Jami slotlar**: {total_slots}/{total_slots}\n"
            f"👥 Oxirgi ro'yxatdan o'tgan jamoa: **{team_name}**\n\n"
            f"Admin panel orqali ishtirokchilar ro'yxatini yuklab olishingiz mumkin."
        )
        # Send to Main Admin
        try:
            bot.send_message(MAIN_ADMIN_ID, notify_message, parse_mode="Markdown")
        except Exception:
            pass
            
        # Send to other admins
        for admin in db.get_admins():
            try:
                bot.send_message(admin['chat_id'], notify_message, parse_mode="Markdown")
            except Exception:
                pass
                
    return jsonify({
        "success": True,
        "game_name": res.get("game_name"),
        "is_now_full": res.get("is_now_full")
    })
# --- ADMIN APIS ---
@app.route('/api/admin/stats', methods=['GET'])
def admin_stats_api():
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if not db.is_admin(chat_id, MAIN_ADMIN_ID):
        return jsonify({"error": "Kirish rad etildi"}), 403
        
    stats = db.get_stats()
    is_main = str(chat_id) == str(MAIN_ADMIN_ID)
    
    return jsonify({
        "stats": stats,
        "is_main_admin": is_main
    })
@app.route('/api/admin/tournaments-all', methods=['GET'])
def admin_tournaments_all_api():
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if not db.is_admin(chat_id, MAIN_ADMIN_ID):
        return jsonify({"error": "Forbidden"}), 403
        
    return jsonify(db.get_all_tournaments())
@app.route('/api/admin/tournaments', methods=['POST'])
def admin_create_tournament_api():
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if not db.is_admin(chat_id, MAIN_ADMIN_ID):
        return jsonify({"error": "Forbidden"}), 403
        
    data = request.json
    game_name = data.get("game_name")
    total_slots = data.get("total_slots")
    
    if not game_name or not total_slots:
        return jsonify({"error": "Nokorrek ma'lumotlar"}), 400
        
    tournament_id = db.create_tournament(game_name, int(total_slots))
    return jsonify({"success": True, "id": tournament_id})
@app.route('/api/admin/tournaments/<int:id>/close', methods=['POST'])
def admin_close_tournament_api(id):
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if not db.is_admin(chat_id, MAIN_ADMIN_ID):
        return jsonify({"error": "Forbidden"}), 403
        
    db.close_tournament(id)
    return jsonify({"success": True})
@app.route('/api/admin/registrations', methods=['GET'])
def admin_get_registrations_api():
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if not db.is_admin(chat_id, MAIN_ADMIN_ID):
        return jsonify({"error": "Forbidden"}), 403
        
    tournament_id = request.args.get("tournament_id")
    if not tournament_id:
        return jsonify({"error": "Turnir ID kiritilmagan"}), 400
        
    regs = db.get_registrations(int(tournament_id))
    return jsonify(regs)
# --- ADMINS MANAGEMENT (OWNER ONLY) ---
@app.route('/api/admin/admins', methods=['GET', 'POST'])
def admin_manage_admins_api():
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if str(chat_id) != str(MAIN_ADMIN_ID):
        return jsonify({"error": "Ushbu amal faqat asosiy admin uchun ruxsat etilgan."}), 403
        
    if request.method == 'GET':
        return jsonify(db.get_admins())
    else:
        data = request.json
        new_chat_id = data.get("chat_id")
        name = data.get("name")
        if not new_chat_id or not name:
            return jsonify({"error": "Ma'lumotlar to'liq emas"}), 400
            
        success = db.add_admin(int(new_chat_id), name)
        if not success:
            return jsonify({"error": "Ushbu admin allaqachon mavjud"}), 400
        return jsonify({"success": True})
@app.route('/api/admin/admins/<int:admin_chat_id>', methods=['DELETE'])
def admin_delete_admin_api(admin_chat_id):
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if str(chat_id) != str(MAIN_ADMIN_ID):
        return jsonify({"error": "Ushbu amal faqat asosiy admin uchun ruxsat etilgan."}), 403
        
    db.remove_admin(admin_chat_id)
    return jsonify({"success": True})
# --- BROADCAST API ---
@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast_api():
    user_info = get_authorized_user(request.headers)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401
    
    chat_id = user_info['user']['id']
    if not db.is_admin(chat_id, MAIN_ADMIN_ID):
        return jsonify({"error": "Forbidden"}), 403
        
    data = request.json
    target = data.get("target") # "all" or "t_<id>"
    message = data.get("message")
    
    if not target or not message:
        return jsonify({"error": "Matn kiritilmagan"}), 400
        
    # Find list of recipient user_ids
    recipients = []
    if target == "all":
        recipients = db.get_all_registered_users()
        # Fallback: also send to main admin and registered admins to test
        recipients.append(int(MAIN_ADMIN_ID))
        for adm in db.get_admins():
            recipients.append(adm['chat_id'])
        recipients = list(set(recipients)) # unique
    elif target.startswith("t_"):
        t_id = int(target.split("_")[1])
        regs = db.get_registrations(t_id)
        recipients = list(set([r['user_id'] for r in regs]))
        
    sent_count = 0
    formatted_msg = f"📢 **YANGILIK / HABAR**\n\n{message}"
    
    for rid in recipients:
        try:
            bot.send_message(rid, formatted_msg, parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            print(f"Xabar yuborilmadi {rid}: {e}")
            
    return jsonify({"success": True, "sent_count": sent_count})
# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    
    # Check if admin
    is_adm = db.is_admin(chat_id, MAIN_ADMIN_ID)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if is_adm:
        # Create Web App links
        admin_webapp = types.WebAppInfo(f"{WEBAPP_URL}/admin-panel")
        user_webapp = types.WebAppInfo(f"{WEBAPP_URL}/")
        
        btn_admin = types.KeyboardButton("⚙️ Admin Panel", web_app=admin_webapp)
        btn_user = types.KeyboardButton("📝 Turnirlar (User view)", web_app=user_webapp)
        btn_stats = types.KeyboardButton("📊 Statistika")
        
        markup.add(btn_admin)
        markup.add(btn_user, btn_stats)
        
        welcome_text = (
            f"🎮 **Salom, Admin {message.from_user.first_name}!**\n\n"
            f"PIXEL Game Zone boshqaruv botiga xush kelibsiz. "
            f"Quyidagi tugmalar orqali Web App boshqaruv panelini ochishingiz mumkin."
        )
        bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    else:
        user_webapp = types.WebAppInfo(f"{WEBAPP_URL}/")
        btn_reg = types.KeyboardButton("📝 Ro'yxatdan O'tish", web_app=user_webapp)
        btn_my_team = types.KeyboardButton("👥 Mening Jamoam")
        btn_stats = types.KeyboardButton("📊 Turnirlar Holati")
        btn_rules = types.KeyboardButton("ℹ️ Qoidalar va Manzil")
        
        markup.row(btn_reg)
        markup.row(btn_my_team, btn_stats)
        markup.row(btn_rules)
        
        welcome_text = (
            f"🎮 **PIXEL Game Zone klubi botiga xush kelibsiz!**\n\n"
            f"Ushbu bot orqali klubimizda o'tkaziladigan turnirlarga jamoangizni ro'yxatdan o'tkazishingiz mumkin. "
            f"Pastdagi 'Ro'yxatdan o'tish' tugmasini bosing!"
        )
        bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="Markdown")
@bot.message_handler(func=lambda msg: True)
def handle_text_buttons(message):
    chat_id = message.chat.id
    text = message.text
    
    if text == "📊 Statistika" or text == "📊 Turnirlar Holati":
        # Get active tournaments and general stats
        tournaments = db.get_active_tournaments()
        if not tournaments:
            bot.send_message(chat_id, "Hozircha hech qanday faol turnirlar mavjud emas.")
            return
            
        msg_text = "📊 **Turnirlardagi slotlar holati:**\n\n"
        for t in tournaments:
            filled = t['filled_slots']
            total = t['total_slots']
            status_emoji = "🚨" if filled >= total else "🟢"
            msg_text += f"{status_emoji} **{t['game_name']}** — {filled}/{total} jamoa\n"
            
        bot.send_message(chat_id, msg_text, parse_mode="Markdown")
        
    elif text == "👥 Mening Jamoam":
        # Check database for registrations under this telegram account
        regs = []
        # Since SQLite is local, we scan all active/completed registrations
        all_t = db.get_all_tournaments()
        for t in all_t:
            t_regs = db.get_registrations(t['id'])
            for r in t_regs:
                if str(r['user_id']) == str(chat_id):
                    regs.append((t['game_name'], r))
                    
        if not regs:
            bot.send_message(chat_id, "Siz hali birorta ham jamoa ro'yxatdan o'tkazmagansiz.")
            return
            
        msg_text = "👥 **Siz ro'yxatdan o'tkazgan jamoalar:**\n\n"
        for game_name, r in regs:
            msg_text += (
                f"🎮 **Turnir**: {game_name}\n"
                f"🛡️ **Jamoa**: {r['team_name']}\n"
                f"👤 **Sardor**: {r['captain_name']} ({r['captain_phone']})\n"
                f"👥 **A'zolar**: {', '.join(r['members'])}\n"
                f"-----------------------------\n"
            )
        bot.send_message(chat_id, msg_text, parse_mode="Markdown")
        
    elif text == "ℹ️ Qoidalar va Manzil":
        rules = (
            "🏢 **PIXEL Game Zone kompyuter klubi**\n\n"
            "📍 **Manzil**: Toshkent shahar (Klubning aniq manzili va telefon raqami)\n"
            "📞 **Aloqa**: +998 90 123-45-67\n\n"
            "🎮 **Turnir Qoidalari:**\n"
            "1. Har bir jamoa tarkibi aniq 5 kishidan iborat bo'lishi shart.\n"
            "2. Ro'yxatdan o'tish to'liq bepul (yoki klub qoidalariga muvofiq).\n"
            "3. Kechikkan jamoalarga texnik mag'lubiyat yoziladi.\n"
            "4. O'yin vaqtida o'zaro hurmat saqlanishi talab etiladi."
        )
        bot.send_message(chat_id, rules, parse_mode="Markdown")
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    """Fires when Web App calls tg.sendData(...)"""
    chat_id = message.chat.id
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "registered":
            team_name = data.get("team_name")
            game_name = data.get("game_name")
            success_text = (
                f"🎉 **Tabriklaymiz!**\n\n"
                f"Jamoangiz **{team_name}** muvaffaqiyatli ro'yxatdan o'tdi!\n"
                f"🎮 **O'yin**: {game_name}\n\n"
                f"Turnir boshlanish sanasi haqida kanallarimizda va bot orqali xabar beramiz."
            )
            bot.send_message(chat_id, success_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Web App Data parse error: {e}")
# --- START RUNNING ---
def run_flask_app():
    # Runs Flask server
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Mute flask default request logs for clean console
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 5000)), debug=False, use_reloader=False)
if __name__ == '__main__':
    print("---------------------------------------------")
    print("[*] PIXEL Game Zone bot & server ishga tushmoqda...")
    print(f"[*] Web App manzili: {WEBAPP_URL}")
    print(f"[*] Asosiy Admin ID: {MAIN_ADMIN_ID}")
    print("---------------------------------------------")
    
    # Start web server in background thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start telegram bot polling in main thread
    bot.infinity_polling()
