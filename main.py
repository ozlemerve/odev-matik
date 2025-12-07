import streamlit as st
from openai import OpenAI
import base64
import random
import urllib.parse
import sqlite3
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import extra_streamlit_components as stx
import datetime

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ÇEREZ YÖNETİCİSİ (DÜZELTİLDİ) ---
# Hata veren @st.cache_resource kaldırıldı.
cookie_manager = stx.CookieManager()

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
    c.execute('''CREATE TABLE IF NOT EXISTS historyTable 
                 (username TEXT, question TEXT, answer TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('CREATE TABLE IF NOT EXISTS feedbackTable (username TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO usersTable (username, password, credit) VALUES (?, ?, ?)', (username, password, 5))
        conn.commit()
        result = True
    except:
        result = False
    conn.close()
    return result

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM usersTable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    conn.close()
    return data

def get_credit(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT credit FROM usersTable WHERE username =?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else 0

def deduct_credit(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE usersTable SET credit = credit - 1 WHERE username =?', (username,))
    conn.commit()
    conn.close()

def save_history(username, question, answer):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO historyTable (username, question, answer) VALUES (?, ?, ?)', (username, question, answer))
    conn.commit()
    conn.close()

def get_user_history(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT question, answer, timestamp FROM historyTable WHERE username =? ORDER BY timestamp DESC LIMIT 10', (username,))
    data = c.fetchall()
    conn.close()
    return data

def get_total_solved(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM historyTable WHERE username =?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else 0

def save_feedback(username, message):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO feedbackTable (username, message) VALUES (?, ?)', (username, message))
    conn.commit()
    conn.close()

init_db()

# --- E-POSTA ---
def send_verification_email(to_email, code):
    try:
        sender_email = st.secrets["EMAIL_ADDRESS"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
    except:
        return False
    
    subject = "ÖdevMatik Doğrulama Kodu"
    body = f"Merhaba,\n\nKodunuz: {code}\n\nÖdevMatik Ekibi"
    msg = MIMEMultipart()
    msg['From'] = f"ÖdevMatik Güvenlik <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True
    except:
        return False

# --- CSS ---
st.markdown("""
<style>
    div.stButton > button { width: 100%; border-radius: 10px; height: 50px; font-weight: bold; }
    a[href*="whatsapp"] button { color: #25D366 !important; border-color: #25D366 !important; }
    a[href^="mailto"] button { color: #0078D4 !important; border-color: #0078D4 !important; }
    .stat-box { background-color: #e3f2fd; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px; border: 1px solid #90caf9; }
    .stat-title { font-size: 14px; color: #555; }
    .stat-value { font-size: 24px; font-weight: bold; color: #1565c0; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM BAŞLATMA ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "verification_code" not in st.session_state: st.session_state.verification_code = None
if "son_cevap" not in st.session_state: st.session_state.son_cevap = None

# API KEY KONTROL
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.warning("API Key Eksik!")
    st.stop()

client = OpenAI(api_key=api_key)

# 🚀 KALICI OTURUM KONTROLÜ (GÜÇLENDİRİLMİŞ)
# Sayfa her açıldığında çerezleri kontrol et
# time.sleep eklemiyoruz, direkt CookieManager'ın yüklenmesini bekliyoruz
auth_cookie = cookie_manager.get("user_token")
if auth_cookie and not st.session_state.logged_in:
    st.session_state.logged_in = True
    st.session_state.username = auth_cookie

# ==========================================
# ÜST BAR (HEADER)
# ==========================================
col_logo, col_auth = st.columns([2, 1])

with col_logo:
    st.markdown("<h1 style='margin-bottom:0;'>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:grey;'>Ödev asistanın cebinde!</p>", unsafe_allow_html=True)

with col_auth:
    if not st.session_state.logged_in:
        with st.expander("🔐 Giriş / Kayıt"):
            tab_login, tab_register = st.tabs(["Giriş", "Kayıt"])
            with tab_login:
                with st.form("top_login"):
                    l_user = st.text_input("Email", label_visibility="collapsed", placeholder="Email")
                    l_pass = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifre")
                    if st.form_submit_button("Giriş Yap", type="primary"):
                        if login_user(l_user, l_pass):
                            st.session_state.logged_in = True
                            st.session_state.username = l_user
                            # ÇEREZ KAYDET (30 GÜN)
                            cookie_manager.set("user_token", l_user, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                            st.rerun()
                        else: st.error("Hatalı!")
            with tab_register:
                r_email = st.text_input("Email", key="r_email")
                r_pass = st.text_input("Şifre", type="password", key="r_pass")
                if st.button("Kod Gönder"):
                    if "@" in r_email:
                        code = str(random.randint(1000,9999))
                        if send_verification_email(r_email, code):
                            st.session_state.verification_code = code
                            st.success("Kod yollandı!")
                        else: st.error("Hata")
                if st.session_state.verification_code:
                    kod_gir = st.text_input("Kod:")
                    if st.button("Onayla"):
                        if kod_gir == st.session_state.verification_code:
