import streamlit as st
from openai import OpenAI
import base64
import random
import urllib.parse
import sqlite3
import time

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- VERİTABANI FONKSİYONLARI ---
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

# --- CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 50px;
        font-weight: bold;
    }
    a[href*="whatsapp"] button { color: #25D366 !important; border-color: #25D366 !important; }
    a[href^="mailto"] button { color: #0078D4 !important; border-color: #0078D4 !important; }
    h1 { text-align: center; color: #1E1E1E; margin-bottom: 0px; }
    p { text-align: center; color: #666; margin-top: 5px; }
    [data-testid="column"] { padding: 0 0.3rem !important; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ==========================================
# 1. BÖLÜM: GİRİŞ VE KAYIT
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔒 ÖdevMatik</h1>", unsafe_allow_html=True)
    st.write("")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with tab1:
        st.info("Hesabın varsa giriş yap.")
        with st.form("giris_formu"):
            login_user_name = st.text_input("Kullanıcı Adı (Email):")
            login_password = st.text_input("Şifre:", type='password')
            submit_login = st.form_submit_button("Giriş Yap", type="primary")
            
            if submit_login:
                if login_user(login_user_name, login_password):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user_name
                    st.success("Giriş Başarılı!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")

    with tab2:
        st.info("Yeni hesap oluştur. **5 Soru Hakkı Hediye!** 🎁")
        with st.form("kayit_formu"):
            new_user = st.text_input("Kullanıcı Adı Belirle:")
            new_password = st.text_input("Şifre Belirle:", type='password')
            submit_register = st.form_submit_button("Kayıt Ol")
            
            if submit_register:
                if new_user and new_password:
                    if add_user(new_user, new_password):
                        st.success("Kayıt Başarılı! Şimdi 'Giriş Yap' sekmesinden girebilirsin.")
                    else:
                        st.error("Bu kullanıcı adı zaten alınmış.")
                else:
                    st.warning("Lütfen tüm alanları doldur.")

    st.stop() 

# ==========================================
# 2. BÖLÜM: UYGULAMA İÇERİSİ
# ==========================================

current_credit = get_credit(st.session_state.username)

# --- YAN MENÜ ---
with st.sidebar:
    st.title(f"👤 {st.session_state.username}")
    st.metric("Kalan Hakkın", f"{current_credit} Soru")
    
    if current_credit == 0:
        st.error("Hakkın bitti!")
        st.button("💎 Premium Al (Sınırsız)")
    
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()
    
    if "OPEN
