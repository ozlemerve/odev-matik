import streamlit as st
from openai import OpenAI
import base64
import random
import urllib.parse
import sqlite3
import time
import extra_streamlit_components as stx
import datetime
from fpdf import FPDF
import requests
import os
import re

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ÇEREZ YÖNETİCİSİ ---
cookie_manager = stx.CookieManager(key="auth_mgr_final_fix")

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
    c.execute('''CREATE TABLE IF NOT EXISTS historyTable_v2 
                 (username TEXT, question TEXT, answer TEXT, image_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM usersTable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    conn.close()
    return data

def add_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO usersTable (username, password, credit) VALUES (?, ?, ?)', (username, password, 100))
        conn.commit()
        result = True
    except: result = False
    conn.close()
    return result

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

def save_history(username, question, answer, image_data=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO historyTable_v2 (username, question, answer, image_data) VALUES (?, ?, ?, ?)', (username, question, answer, image_data))
    conn.commit()
    conn.close()

def get_user_history(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT question, answer, image_data, timestamp FROM historyTable_v2 WHERE username =? ORDER BY timestamp DESC LIMIT 10', (username,))
    data = c.fetchall()
    conn.close()
    return data

def get_total_solved(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('SELECT COUNT(*) FROM historyTable_v2 WHERE username =?', (username,))
        data = c.fetchone()
        count = data[0] if data else 0
    except: count = 0
    conn.close()
    return count

init_db()

# --- TEMİZLEYİCİ ---
def clean_latex(text):
    text = text.replace(r'\frac', '').replace('{', '').replace('}', '/')
    text = text.replace(r'\sqrt', 'kök').replace(r'\times', 'x').replace(r'\cdot', '.')
    text = text.replace(r'\(', '').replace(r'\)', '').replace(r'\[', '').replace(r'\]', '')
    return text

def clean_text_for_pdf(text):
    text = clean_latex(text)
    replacements = {
        'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ç': 'c', 'Ç': 'C', 'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
        '√': 'kok', '²': '^2', '³': '^3', 'π': 'pi', '∞': 'sonsuz', '≠': 'esit degil', '≤': '<=', '≥': '>=', '×': 'x', '·': '.'
    }
    text = text.replace('**', '').replace('__', '').replace('###', '').replace('##', '').replace('#', '')
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_safe_pdf(title, content):
    font_path = "DejaVuSans.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/realsung/whiteboard/raw/master/src/fonts/DejaVuSans.ttf"
            r = requests.get(url, timeout=2)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except: pass

    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(font_path):
        pdf.add_font('DejaVu', '', font_path, uni=True)
        pdf.set_font('DejaVu', '', 12)
        use_unicode = True
    else:
        pdf.set_font("Arial", size=12)
        use_unicode = False
    
    safe_title = title if use_unicode else clean_text_for_pdf(title)
    pdf.cell(0, 10, safe_title, ln=True, align='C')
    pdf.ln(10)
    
    safe_content = content if use_unicode else clean_text_for_pdf(content)
    pdf.multi_cell(0, 7, safe_content)
    return pdf.output(dest='S').encode('latin-1')

# --- CSS ---
st.markdown("""
<style>
    div.stButton > button { width: 100%; border-radius: 10px; height: 50px; font-weight: bold; }
    .stat-box { background-color: #e3f2fd; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px; border: 1px solid #90caf9; }
    .stat-title { font-size: 14px; color: #555; }
    .stat-value { font-size: 24px; font-weight: bold; color: #1565c0; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "son_cevap" not in st.session_state: st.session_state.son_cevap = None

time.sleep(0.1)
try:
    cookies = cookie_manager.get_all()
    user_token = cookies.get("user_token")
    if user_token and not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.username = user_token
        st.rerun()
except: pass

if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.warning("API Key Eksik!")
    st.stop()

client = OpenAI(api_key=api_key)

# ==========================================
# ÜST BAR
# ==========================================
col_logo, col_auth = st.columns([2, 1])
with col_logo:
    st.markdown("<h1 style='margin-bottom:0;'>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:grey;'>Eğitim Koçun Cebinde!</p>", unsafe_allow_html=True)

with col_auth:
    if not st.session_state.logged_in:
        with st.expander("🔐 Giriş"):
            tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
            with tab1:
                with st.form("l_form"):
                    u = st.text_input("Email")
                    p = st.text_input("Şifre", type="password")
                    if st.form_submit_button("Gir"):
                        if login_user(u, p):
                            st.session_state.logged_in = True
                            st.session_state.username = u
                            cookie_manager.set("user_token", u, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                            st.rerun()
                        else: st.error("Hata")
            with tab2:
                with st.form("r_form"):
                    nu = st.text_input("Email")
                    np = st.text_input("Şifre", type="password")
                    if st.form_submit_button("Kayıt Ol"):
                        if add_user(nu, np): st.success("Oldu! Giriş yap.");
                        else: st.error("Hata")
    else:
        kredi = get_credit(st.session_state.username)
        st.info(f"👤 **{st.session_state.username.split('@')[0]}**")
        st.caption(f"🎫 Hak: **{kredi}**")

st.divider()

# ==========================================
# YAN MENÜ
# ==========================================
with st.sidebar:
    st.title("🗂️ Panel")
    if st.button("🏠 Ana Ekran", use_container_width=True):
        st.session_state.son_cevap = None
        st.rerun()
    st.divider()
    
    if st.session_state.logged_in:
        total = get_total_solved(st.session_state.username)
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"<div class='stat-box'><div class='stat-title'>Çözülen</div><div class='stat-value'>{total}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='stat-box'><div class='stat-title'>Hak</div><div class='stat-value'>{get_credit(st.session_state.username)}</div></div>", unsafe_allow_html=True)
        
        with st.expander("📜 Geçmiş"):
            try:
                hist = get_user_history(st.session_state.username)
                if hist:
                    for q, a, img, t in hist:
                        st.text(t[:16])
                        if img:
                            try: st.image(base64.b64decode(img), caption="Soru", use_container_width=True)
                            except: pass
                        else: st.caption(q[:30])
                        with st.popover("Cevap"): st.write(clean_latex(a))
                        st.divider()
                else: st.caption("Yok.")
            except: pass
        
        if st.button("🚪 Çıkış"):
            st.session_state.logged_in = False
            st.session_state.username = "Misafir"
            cookie_manager.delete("user_token")
            st.rerun()
    else:
        st.warning("Misafir Modu: 1 Hak")

    if st.checkbox("Admin"):
        if st.button("Sıfırla"):
            try: cookie_manager.delete("guest_used"); st.rerun()
            except: pass

# ==========================================
# ANA EKRAN
# ==========================================

guest_locked = False
if not st.session_state.logged_in:
    try:
        if cookie_manager.get("guest_used"): guest_locked = True
    except: pass

# --- SONUÇ ---
if st.session_state.son_cevap:
    clean_cevap = clean_latex(st.session_state.son_cevap)
    st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;padding:25px;font-family:'Patrick Hand',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{clean_cevap}</div>""", unsafe_allow_html=True)
    
    try:
        pdf_bytes = create_safe_pdf("Cozum", clean_cevap)
        st.download_button("📥 PDF İndir", pdf_bytes, "cozum.pdf", "application/pdf", use_container_width=True, type="primary")
    except: pass
    
    st.markdown("### 📤 Paylaş")
    url_txt = urllib.parse.quote(f"Çözüm:\n\n{clean_cevap}\n\n--- ÖdevMatik")
    c1, c2 = st.columns(2)
    with c1: st.link_button("💬 WhatsApp", f"https://api.whatsapp.com/send?text={url_txt}", use_container_width=True)
    with c2: st.link_button("📧 Mail", f"mailto:?body={url_txt}", use_container_width=True)
    
    st.divider()
    if st.button("⬅️ Yeni Soru"):
        st.session_state.son_cevap = None
        st.rerun()

elif guest_locked and not st.session_state.logged_in:
    st.warning("⚠️ Hakkın bitti! Devam etmek için sağ üstten **Kayıt Ol**.")

else:
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📁 Galeri", use_container_width=True): st.session_state.aktif_mod = "Galeri"
    with col2:
        if st.button("📸 Kamera", use_container_width=True): st.session_state.aktif_mod = "Kamera"
    with col3:
        if st.button("⌨️ Yaz", use_container_width=True): st.session_state.aktif_mod = "Yaz"

    if "aktif_mod" not in st.session_state: st.session_state.aktif_mod = "Galeri"
    st.write("")
    
    gorsel_veri = None; metin_sorusu = None; run = False

    if st.session_state.aktif_mod == "Galeri":
        st.info("📂 **Galeriden Seç**")
        up = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
        if up: gorsel_veri = up.getvalue(); 
        if st.button("Çöz ✍️", type="primary", use_container_width=True): run = True
    elif st.session_state.aktif_mod == "Kamera":
        st.info("📸 **Fotoğraf Çek**")
        cam = st.camera_input("Kamera")
        if cam: gorsel_veri = cam.getvalue(); 
        if st.button("Çöz ✍️", type="primary", use_container_width=True): run = True
    elif st.session_state.aktif_mod == "Yaz":
        st.info("⌨️ **Soruyu Yaz**")
        with st.form("txt"):
            metin_sorusu = st.text_area("", height=150)
            if st.form_submit_button("Çöz ✍️", type="primary", use_container_width=True): run = True

    if run:
        can = False
        if st.session_state.logged_in:
            if get_credit(st.session_state.username) > 0:
                deduct_credit(st.session_state.username); st.toast("Hakkın düştü", icon="🎫"); can = True
            else: st.error("Bitti!")
        else:
            try: cookie_manager.set("guest_used", "true", expires_at=datetime.datetime.now() + datetime.timedelta(days=1)); can = True
            except: pass

        if can:
            with st.spinner("Çözülüyor..."):
                try:
                    # GÜÇLENDİRİLMİŞ PROMPT (GEOMETRİ VE DETAY İÇİN)
                    prompt = """
                    GÖREV: Öğrenciye özel ders öğretmeni gibi detaylı çözüm yap.
                    
                    KURALLAR:
                    1. Asla LaTeX kodu kullanma. Karekök için 'kök()', üs için '^' kullan.
                    2. Eğer resimde GEOMETRİ veya ŞEKİL varsa: Şekli görmeden çözemeyeceğini SÖYLEME. Gördüğün kadarıyla varsayım yap ve çözmeye çalış.
                    3. Adım adım, açıklayıcı ol.
                    4. Sonucu net belirt.
                    """
                    
                    if gorsel_veri:
                        model = "gpt-4o"
                        img = base64.b64encode(gorsel_veri).decode('utf-8')
                        msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}]
                    else:
                        model = "gpt-4o-mini"
                        msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]

                    resp = client.chat.completions.create(model=model, messages=msgs, max_tokens=1000)
                    ans = resp.choices[0].message.content
                    
                    if st.session_state.logged_in:
                        img_save = base64.b64encode(gorsel_veri).decode('utf-8') if gorsel_veri else None
                        save_history(st.session_state.username, "Soru", ans, img_save)
                    
                    st.session_state.son_cevap = ans
                    st.rerun()
                except Exception as e: st.error(f"Hata: {e}")
