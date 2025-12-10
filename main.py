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
cookie_manager = stx.CookieManager(key="auth_mgr_v73")

# --- BEKLEME MESAJLARI ---
LOADING_MESSAGES = [
    "🧠 Nöronlar ateşleniyor...",
    "🧐 Matematik profesörüne bağlanılıyor...",
    "🚀 Işık hızında hesaplanıyor...",
    "☕ Çayından bir yudum al, hallediyorum...",
    "📐 Üçgenin iç açıları toplanıyor...",
    "🔍 Mercek altına alındı...",
    "🤖 Yapay zeka düşünüyor...",
    "🎲 Zarlar atıldı, çözüm geliyor..."
]

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
    c.execute('''CREATE TABLE IF NOT EXISTS historyTable_v2 
                 (username TEXT, question TEXT, answer TEXT, image_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('CREATE TABLE IF NOT EXISTS feedbackTable (username TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
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
        # DÜZELTME 4: YENİ ÜYE ARTIK 5 KREDİ İLE BAŞLIYOR
        c.execute('INSERT INTO usersTable (username, password, credit) VALUES (?, ?, ?)', (username, password, 5))
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

def update_credit(username, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE usersTable SET credit = ? WHERE username =?', (amount, username))
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

def save_feedback(username, message):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO feedbackTable (username, message) VALUES (?, ?)', (username, message))
    conn.commit()
    conn.close()

# ADMIN
def get_all_users_raw():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username, credit FROM usersTable")
    data = c.fetchall()
    conn.close()
    return data

def get_total_stats():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usersTable")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM historyTable_v2")
    total_questions = c.fetchone()[0]
    conn.close()
    return total_users, total_questions

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

# --- E-POSTA ---
def send_verification_email(to_email, code):
    try:
        sender_email = st.secrets["EMAIL_ADDRESS"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
    except: return False
    subject = "ÖdevMatik Kod"
    body = f"Kod: {code}"
    msg = MIMEMultipart()
    msg['From'] = f"ÖdevMatik <{sender_email}>"
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
    except: return False

# --- CSS (TEMEL TASARIM) ---
st.markdown("""
<style>
    div.stButton > button { 
        width: 100%; 
        border-radius: 12px; 
        height: 55px; 
        font-weight: 800; 
        font-size: 18px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        transition: all 0.2s;
        border: 1px solid #e0e0e0;
    }
    div.stButton > button:hover { 
        transform: scale(1.02); 
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    
    .stat-box { 
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
        padding: 15px; 
        border-radius: 12px; 
        text-align: center; 
        margin-bottom: 10px; 
        border: 1px solid #90caf9; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-title { font-size: 14px; color: #1565c0; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 28px; font-weight: 900; color: #0d47a1; }
    
    .brand-title {
        font-size: 2.5rem;
        font-weight: 900;
        color: #0d47a1;
        margin-bottom: 0px;
        margin-top: -20px;
        text-shadow: 2px 2px 0px #e3f2fd;
        letter-spacing: -1px;
    }
    .brand-subtitle {
        color: #555;
        font-size: 1.1rem;
        margin-top: -5px;
        font-weight: 400;
    }
    
    .streamlit-expanderHeader {
        font-weight: 700 !important;
        color: #0d47a1 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "verification_code" not in st.session_state: st.session_state.verification_code = None
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
# YAN MENÜ (GECE MODU VE İSTATİSTİK)
# ==========================================
with st.sidebar:
    st.title("🎓 Öğrenci Paneli")
    if st.button("🏠 Ana Ekran", use_container_width=True):
        st.session_state.son_cevap = None
        st.rerun()
    st.divider()
    
    # 🌙 DÜZELTİLMİŞ GECE MODU
    dark_mode = st.toggle("🌙 Gece Modu")
    if dark_mode:
        st.markdown("""
        <style>
            .stApp { background-color: #0e1117; color: #e0e0e0; }
            [data-testid="stSidebar"] { background-color: #262730; }
            [data-testid="stHeader"] { background-color: #0e1117; }
            
            /* Logo ve Başlıklar Parlak Olmalı */
            .brand-title { color: #64b5f6 !important; text-shadow: none !important; }
            .brand-subtitle { color: #b0bec5 !important; }
            .streamlit-expanderHeader { color: #90caf9 !important; background-color: #1f2937 !important; }
            
            /* İstatistik Kutuları Koyu */
            .stat-box { 
                background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%) !important; 
                border: 1px solid #5c6bc0 !important; 
            }
            .stat-title { color: #e3f2fd !important; }
            .stat-value { color: #ffffff !important; }
            
            /* Butonlar Koyu */
            div.stButton > button { background-color: #1f2937; color: #ffffff; border: 1px solid #4b5563; }
            div.stButton > button:hover { background-color: #374151; border-color: #60a5fa; }
            
            /* Metinler */
            p, h1, h2, h3 { color: #e0e0e0; }
        </style>
        """, unsafe_allow_html=True)

    if st.session_state.logged_in:
        total = get_total_solved(st.session_state.username)
        kredi = get_credit(st.session_state.username)
        
        progress_val = min(1.0, kredi / 100)
        st.write(f"**Kalan Kredi Durumu:**")
        st.progress(progress_val)
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"<div class='stat-box'><div class='stat-title'>Çözülen</div><div class='stat-value'>{total}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='stat-box'><div class='stat-title'>Kalan</div><div class='stat-value'>{kredi}</div></div>", unsafe_allow_html=True)
        
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
                        with st.popover("Cevabı Gör"): st.write(clean_latex(a))
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

    # PATRON PANELİ
    admin_mail = st.secrets.get("ADMIN_USER", "admin@admin.com")
    if st.session_state.logged_in and st.session_state.username == admin_mail:
        st.divider()
        st.error("🔒 PATRON PANELİ")
        
        if st.button("Misafir Hakkını Sıfırla"):
            try: cookie_manager.delete("guest_used"); st.rerun()
            except: pass
            
        st.write("**💰 Kredi Yükle**")
        hedef_user = st.text_input("Kullanıcı Email:")
        miktar = st.number_input("Miktar:", value=100)
        if st.button("Yükle"):
            update_credit(hedef_user, miktar)
            st.success(f"Yüklendi: {hedef_user}")
            
        with st.expander("İstatistikler"):
            t_user, t_quest = get_total_stats()
            st.write(f"Üye: {t_user} | Soru: {t_quest}")
            users_data = get_all_users_raw()
            for u_mail, u_cred in users_data:
                st.text(f"{u_mail} - {u_cred}")

# ==========================================
# ÜST BAR
# ==========================================
col_logo, col_auth = st.columns([5, 2])

with col_logo:
    st.markdown("<div class='brand-title'>📝 ÖdevMatik</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-subtitle'>Yeni Nesil Asistan</div>", unsafe_allow_html=True)

with col_auth:
    if not st.session_state.logged_in:
        with st.expander("🔐 Giriş ve Kayıt Ol"):
            tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
            with tab1:
                with st.form("l_form"):
                    u = st.text_input("Email", label_visibility="collapsed", placeholder="Email")
                    p = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifre")
                    if st.form_submit_button("Gir"):
                        if login_user(u, p):
                            st.session_state.logged_in = True
                            st.session_state.username = u
                            cookie_manager.set("user_token", u, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                            st.rerun()
                        else: st.error("Hata")
            with tab2:
                with st.form("r_form"):
                    nu = st.text_input("Email", label_visibility="collapsed", placeholder="Email")
                    np = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifre")
                    if st.form_submit_button("Kayıt Ol"):
                        if add_user(nu, np): st.success("Oldu! Giriş yap.");
                        else: st.error("Hata")
            
            if st.checkbox("Kodla Kayıt"):
                 r_email_v = st.text_input("Email:", key="v_email")
                 r_pass_v = st.text_input("Şifre:", type="password", key="v_pass")
                 if st.button("Kod Gönder"):
                     if "@" in r_email_v:
                         code = str(random.randint(1000,9999))
                         if send_verification_email(r_email_v, code):
                             st.session_state.verification_code = code
                             st.success("Kod yollandı!")
                         else: st.error("Mail Hatası")
                 
                 if st.session_state.verification_code:
                     kod_gir = st.text_input("Kodu Gir:")
                     if st.button("Onayla"):
                         if kod_gir == st.session_state.verification_code:
                             if add_user(r_email_v, r_pass_v): st.success("Kayıt Başarılı! Giriş yap."); st.session_state.verification_code = None
                             else: st.error("Hata")
    else:
        kredi = get_credit(st.session_state.username)
        st.info(f"👤 **{st.session_state.username.split('@')[0]}**")
        st.caption(f"🎫 Kalan: **{kredi}**")

st.divider()

# ==========================================
# ANA EKRAN AKIŞI
# ==========================================

guest_locked = False
if not st.session_state.logged_in:
    try:
        cookies = cookie_manager.get_all()
        # DÜZELTME 1: ÇEREZ VARSA VE CEVAP YOKSA KİLİTLE (1 HAK)
        if "guest_used" in cookies and not st.session_state.son_cevap:
            guest_locked = True
    except: pass

# --- SONUÇ ---
if st.session_state.son_cevap:
    st.success("✅ Çözüm Başarıyla Hazırlandı!")
    st.balloons()
    
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
        # Misafirsen ve cevabı gördüysen, çıkarken kilitle
        if not st.session_state.logged_in:
             try: cookie_manager.set("guest_used", "true", expires_at=datetime.datetime.now() + datetime.timedelta(days=1))
             except: pass
        st.rerun()

elif guest_locked and not st.session_state.logged_in:
    st.warning("⚠️ Hakkın bitti! Devam etmek için sağ üstten **Giriş ve Kayıt Ol**.")

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
        if up: gorsel_veri = up.getvalue()
        if st.button("Çöz ✍️", type="primary", use_container_width=True): run = True
        
    elif st.session_state.aktif_mod == "Kamera":
        st.info("📸 **Fotoğraf Çek**")
        cam = st.camera_input("Kamerayı aç")
        if cam: gorsel_veri = cam.getvalue()
        if st.button("Çöz ✍️", type="primary", use_container_width=True): run = True
        
    elif st.session_state.aktif_mod == "Yaz":
        st.info("⌨️ **Soruyu Yaz**")
        with st.form("txt"):
            metin_sorusu = st.text_area("", height=150)
            if st.form_submit_button("Çöz ✍️", type="primary", use_container_width=True): run = True

    if run:
        if not gorsel_veri and not metin_sorusu:
            st.warning("Lütfen bir soru gir!")
        else:
            can_proceed = False
            if st.session_state.logged_in:
                if get_credit(st.session_state.username) > 0:
                    deduct_credit(st.session_state.username); can_proceed = True
                else: st.error("Kredin Bitti!")
            else:
                if not guest_locked: can_proceed = True
                else: st.error("Misafir hakkı doldu!")

            if can_proceed:
                msg = random.choice(LOADING_MESSAGES)
                with st.spinner(msg):
                    try:
                        # DÜZELTME 2: CEVAP UZUNLUĞU AYARLANDI
                        prompt = """
                        GÖREV: Öğrencinin sorduğu soruyu matematik öğretmeni gibi çöz.
                        KURALLAR:
                        1. İşlem adımlarını anlaşılır bir şekilde göster (sadece cevabı verip geçme).
                        2. Ancak çok uzun, sıkıcı ders anlatımlarına girme.
                        3. Mantığı kısaca açıkla, işlemi yap, sonucu net belirt.
                        4. Asla LaTeX kodu kullanma (\\frac, \\sqrt YASAK).
                        5. Şekil varsa: Gördüğün kadarıyla varsayım yapıp direkt sonucu bul.
                        """
                        
                        model = "gpt-4o"
                        
                        if gorsel_veri:
                            img = base64.b64encode(gorsel_veri).decode('utf-8')
                            msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}]
                        else:
                            msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]

                        resp = client.chat.completions.create(model=model, messages=msgs, max_tokens=1000)
                        ans = resp.choices[0].message.content
                        
                        if st.session_state.logged_in:
                            img_save = base64.b64encode(gorsel_veri).decode('utf-8') if gorsel_veri else None
                            save_history(st.session_state.username, "Soru", ans, img_save)
                        
                        st.session_state.son_cevap = ans
                        st.rerun()
                    except Exception as e: st.error(f"Hata: {e}")

# --- YASAL UYARI ---
st.markdown("""
<div style='text-align: center; color: grey; font-size: 0.8rem; margin-top: 50px; padding-bottom: 20px;'>
    ⚠️ <b>Yasal Uyarı:</b> Bu uygulama yapay zeka desteklidir. Sonuçlar hatalı olabilir.<br>
    Lütfen cevapları kontrol ediniz. Oluşabilecek hatalardan uygulama sorumlu tutulamaz.
</div>
""", unsafe_allow_html=True)
