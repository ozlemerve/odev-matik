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

# --- ÇEREZ YÖNETİCİSİ ---
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

# --- OTURUM BAŞLATMA VE KONTROL ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "verification_code" not in st.session_state: st.session_state.verification_code = None
if "son_cevap" not in st.session_state: st.session_state.son_cevap = None

# 🚀 KALICI OTURUM KONTROLÜ (YENİ)
# Sayfa yenilense bile çereze bakıp oturumu geri açar
try:
    user_cookie = cookie_manager.get("user_token")
    if user_cookie and not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.username = user_cookie
except:
    pass

if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.warning("API Key Eksik!")
    st.stop()

client = OpenAI(api_key=api_key)

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
                            # 🚀 ÇEREZ KAYDET (30 GÜN)
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
                            if add_user(r_email, r_pass):
                                st.success("Oldu! Giriş yap.")
                                st.session_state.verification_code = None
    else:
        # GİRİŞ YAPILMIŞSA SADE GÖRÜNÜM
        kredi = get_credit(st.session_state.username)
        st.info(f"👤 **{st.session_state.username.split('@')[0]}**")
        st.caption(f"🎫 Kalan Hak: **{kredi}**")

st.divider()

# ==========================================
# YAN MENÜ (PROFIL & AYARLAR)
# ==========================================
with st.sidebar:
    st.title("🗂️ Öğrenci Paneli")
    
    if st.session_state.logged_in:
        total_solved = get_total_solved(st.session_state.username)
        if total_solved < 5: rutbe = "Çırak 👶"
        elif total_solved < 20: rutbe = "Kalfa 🧑‍🎓"
        elif total_solved < 50: rutbe = "Usta 👨‍🏫"
        else: rutbe = "Profesör 🧙‍♂️"
        
        st.write(f"**Rütben:** {rutbe}")
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"<div class='stat-box'><div class='stat-title'>Çözülen</div><div class='stat-value'>{total_solved}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='stat-box'><div class='stat-title'>Hak</div><div class='stat-value'>{get_credit(st.session_state.username)}</div></div>", unsafe_allow_html=True)
        
        st.divider()

        with st.expander("📜 Geçmiş Çözümlerim"):
            gecmis_veriler = get_user_history(st.session_state.username)
            if gecmis_veriler:
                for soru, cevap, zaman in gecmis_veriler:
                    st.text(f"📅 {zaman[:10]}")
                    st.caption(f"❓ {soru[:30]}...")
                    with st.popover("Cevabı Gör"):
                        st.write(cevap)
            else: st.caption("Henüz soru çözmedin.")

        st.divider()

        with st.expander("💬 Bize Ulaşın"):
            with st.form("feedback_form"):
                feedback_msg = st.text_area("Mesajınız:")
                if st.form_submit_button("Gönder"):
                    save_feedback(st.session_state.username, feedback_msg)
                    st.success("İletildi.")
        
        st.divider()
        # ÇIKIŞ BUTONU BURAYA GELDİ
        if st.button("🚪 Çıkış Yap"):
            st.session_state.logged_in = False
            st.session_state.username = "Misafir"
            # 🚀 ÇEREZİ SİL (ÇIKIŞ)
            cookie_manager.delete("user_token")
            time.sleep(0.5)
            st.rerun()

    else:
        st.warning("⚠️ Misafir Modu")
        st.info("🎁 **Üye ol, 5 soru hakkı kazan!**")
        st.write("Misafir modunda sadece 1 hakkın var.")

    st.divider()
    if st.checkbox("Admin Modu"):
        if st.button("Misafir Hakkını Sıfırla"):
            try: cookie_manager.delete("guest_used"); st.rerun()
            except: pass

# ==========================================
# ANA EKRAN AKIŞI
# ==========================================

guest_locked = False
try:
    if not st.session_state.logged_in and cookie_manager.get("guest_used"):
        guest_locked = True
except: pass

if guest_locked and not st.session_state.logged_in:
    st.warning("⚠️ Misafir hakkını kullandın! Devam etmek için sağ üstten **Giriş Yap** veya **Kayıt Ol**.")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📁 Galeri", use_container_width=True): st.session_state.aktif_mod = "Galeri"
with col2:
    if st.button("📸 Kamera", use_container_width=True): st.session_state.aktif_mod = "Kamera"
with col3:
    if st.button("⌨️ Yaz", use_container_width=True): st.session_state.aktif_mod = "Yaz"

if "aktif_mod" not in st.session_state: st.session_state.aktif_mod = "Galeri"

st.write("")

gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

if not guest_locked or st.session_state.logged_in:
    if st.session_state.aktif_mod == "Galeri":
        st.info("📂 **Galeriden Seç**")
        yuklenen_dosya = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if yuklenen_dosya:
            gorsel_veri = yuklenen_dosya.getvalue()
            if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True): form_tetiklendi = True

    elif st.session_state.aktif_mod == "Kamera":
        st.info("📸 **Fotoğraf Çek**")
        cekilen_foto = st.camera_input("Kamerayı aç")
        if cekilen_foto:
            gorsel_veri = cekilen_foto.getvalue()
            if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True): form_tetiklendi = True

    elif st.session_state.aktif_mod == "Yaz":
        st.info("⌨️ **Soruyu Elle Yaz**")
        with st.form(key='soru_yazma_formu'):
            metin_sorusu = st.text_area("", height=150, placeholder="Sorunu buraya yaz...")
            st.write("")
            submit_soru = st.form_submit_button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True)
            if submit_soru and metin_sorusu: form_tetiklendi = True

if form_tetiklendi:
    can_proceed = False
    if st.session_state.logged_in:
        kredi = get_credit(st.session_state.username)
        if kredi > 0:
            deduct_credit(st.session_state.username)
            st.toast("1 Hak düştü!", icon="🎫")
            can_proceed = True
        else:
            st.error("😔 Hakkın bitti!")
    else:
        try:
            cookie_manager.set("guest_used", "true", expires_at=datetime.datetime.now() + datetime.timedelta(days=1))
            st.toast("Misafir hakkın kullanıldı!", icon="🎁")
            can_proceed = True
        except: pass

    if can_proceed:
        with st.spinner(random.choice(["Hoca bakıyor...", "Çözülüyor..."])):
            try:
                ana_prompt = """GÖREV: Soruyu öğrenci gibi çöz. Adım adım git. LaTeX kullanma. Samimi ol."""

                if gorsel_veri:
                    secilen_model = "gpt-4o"
                    base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                    messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
                    kayit_sorusu = "Fotoğraflı Soru"
                elif metin_sorusu:
                    secilen_model = "gpt-4o-mini"
                    messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]
                    kayit_sorusu = metin_sorusu

                response = client.chat.completions.create(model=secilen_model, messages=messages, max_tokens=1000)
                cevap = response.choices[0].message.content
                
                if st.session_state.logged_in:
                    save_history(st.session_state.username, kayit_sorusu, cevap)
                
                st.session_state.son_cevap = cevap
                st.rerun()

            except Exception as e:
                st.error(f"Hata: {e}")

if st.session_state.son_cevap:
    st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{st.session_state.son_cevap}</div>""", unsafe_allow_html=True)
    
    st.write("")
    st.markdown("### 📤 Paylaş")
    paylasim_metni = urllib.parse.quote(f"ÖdevMatik Çözümü:\n\n{st.session_state.son_cevap}\n\n--- ÖdevMatik ile çözüldü.")
    whatsapp_link = f"https://api.whatsapp.com/send?text={paylasim_metni}"
    mail_link = f"mailto:?subject=ÖdevMatik Çözümü&body={paylasim_metni}"
    p_col1, p_col2 = st.columns(2)
    with p_col1: st.link_button("💬 WhatsApp", whatsapp_link, use_container_width=True)
    with p_col2: st.link_button("📧 Mail At", mail_link, use_container_width=True)

st.divider()
st.caption("⚠️ **Yasal Uyarı:** Sonuçlar yapay zeka tarafından üretilmiştir ve hatalı olabilir. Lütfen kontrol ediniz.")
