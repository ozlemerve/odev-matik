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
    initial_sidebar_state="collapsed"
)

# --- ÇEREZ YÖNETİCİSİ ---
cookie_manager = stx.CookieManager()

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
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

init_db()

# --- E-POSTA ---
def send_verification_email(to_email, code):
    try:
        sender_email = st.secrets["EMAIL_ADDRESS"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
    except:
        st.error("Mail ayarları eksik!")
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
    h1 { text-align: center; color: #1E1E1E; margin-bottom: 0px; }
    p { text-align: center; color: #666; margin-top: 5px; }
    [data-testid="column"] { padding: 0 0.3rem !important; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM VE HAFIZA ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "verification_code" not in st.session_state: st.session_state.verification_code = None
# Cevabı hafızada tutmak için yeni değişken:
if "son_cevap" not in st.session_state: st.session_state.son_cevap = None

if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.warning("API Key Eksik!")
    st.stop()

client = OpenAI(api_key=api_key)

# ==========================================
# YAN MENÜ
# ==========================================
with st.sidebar:
    if st.session_state.logged_in:
        st.title(f"👤 {st.session_state.username.split('@')[0]}")
        kredi = get_credit(st.session_state.username)
        st.metric("Kalan Hakkın", f"{kredi}")
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.session_state.username = "Misafir"
            st.session_state.son_cevap = None # Çıkınca cevabı sil
            st.rerun()
    else:
        st.title("👤 Misafir Modu")
        # Çerez Kontrolü
        try:
            guest_cookie = cookie_manager.get("guest_used")
        except:
            guest_cookie = None
        
        if guest_cookie:
            st.warning("🔒 Deneme hakkın bitti!")
            st.info("Devam etmek için kayıt ol.")
        else:
            st.success("🎁 1 Deneme Hakkın Var")
        
        st.divider()
        tab1, tab2 = st.tabs(["Giriş", "Kayıt Ol"])
        
        with tab1:
            with st.form("yan_giris"):
                l_user = st.text_input("Email")
                l_pass = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş"):
                    if login_user(l_user, l_pass):
                        st.session_state.logged_in = True
                        st.session_state.username = l_user
                        st.rerun()
                    else: st.error("Hatalı!")

        with tab2:
            st.caption("5 Hediye Hak Kazan! 🎁")
            r_email = st.text_input("Email", key="r_email")
            r_pass = st.text_input("Şifre", type="password", key="r_pass")
            if st.button("Kod Gönder"):
                if "@" in r_email:
                    code = str(random.randint(1000,9999))
                    if send_verification_email(r_email, code):
                        st.session_state.verification_code = code
                        st.success("Kod gönderildi!")
                    else: st.error("Hata")
            
            if st.session_state.verification_code:
                kod_gir = st.text_input("Kodu Gir:")
                if
