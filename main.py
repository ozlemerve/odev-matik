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
import extra_streamlit_components as stx # Çerez Yöneticisi
import datetime

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ÇEREZ YÖNETİCİSİ (ANTI-REFRESH) ---
@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

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
    .guest-warning {
        padding: 15px; background-color: #fff3cd; color: #856404;
        border: 1px solid #ffeeba; border-radius: 10px;
        text-align: center; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "guest_credit" not in st.session_state: st.session_state.guest_credit = 1
if "verification_code" not in st.session_state: st.session_state.verification_code = None

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
            st.rerun()
    else:
        st.title("👤 Misafir Modu")
        
        # MİSAFİR KONTROLÜ (ÇEREZ OKUMA)
        guest_cookie = cookie_manager.get("guest_used")
        
        if guest_cookie:
            st.error("🔒 Deneme hakkın bitti!")
            st.info("Kayıt olarak 5 hak daha kazan!")
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
                    else: st.error("Hata!")

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
                if st.button("Onayla ve Kayıt Ol"):
                    if kod_gir == st.session_state.verification_code:
                        if add_user(r_email, r_pass):
                            st.success("Kayıt Başarılı! Giriş yap.")
                            st.session_state.verification_code = None

# ==========================================
# ANA EKRAN
# ==========================================
st.markdown("<h1>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
if not st.session_state.logged_in:
    st.markdown("<p>Hemen dene, beğenirsen kayıt ol!</p>", unsafe_allow_html=True)
else:
    st.markdown("<p>Ödev asistanın cebinde!</p>", unsafe_allow_html=True)
st.write("")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📁 Galeri", use_container_width=True): st.session_state.aktif_mod = "Galeri"
with col2:
    if st.button("📸 Kamera", use_container_width=True): st.session_state.aktif_mod = "Kamera"
with col3:
    if st.button("⌨️ Yaz", use_container_width=True): st.session_state.aktif_mod = "Yaz"

if "aktif_mod" not in st.session_state: st.session_state.aktif_mod = "Galeri"

st.divider()

# MİSAFİR KİLİDİ (ÇEREZ VARSA DURDUR)
guest_cookie = cookie_manager.get("guest_used")
if not st.session_state.logged_in and guest_cookie:
    st.warning("⚠️ Misafir hakkını kullandın! Devam etmek için lütfen soldan **Ücretsiz Kayıt Ol**.")
    st.stop()

gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

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

# --- ÇÖZÜM MOTORU ---
if form_tetiklendi:
    # 1. KREDİ DÜŞME / ÇEREZ ATMA
    if st.session_state.logged_in:
        kredi = get_credit(st.session_state.username)
        if kredi <= 0:
            st.error("😔 Hakkın bitti!")
            st.stop()
        deduct_credit(st.session_state.username)
        st.toast("1 Hak düştü!", icon="🎫")
    else:
        # Misafir damgası bas (1 gün geçerli)
        cookie_manager.set("guest_used", "true", expires_at=datetime.datetime.now() + datetime.timedelta(days=1))
        st.toast("Misafir hakkın kullanıldı!", icon="🎁")

    with st.spinner(random.choice(["Hoca bakıyor...", "Çözülüyor..."])):
        try:
            ana_prompt = """GÖREV: Soruyu öğrenci gibi çöz. Adım adım git. LaTeX kullanma. Samimi ol."""

            if gorsel_veri:
                secilen_model = "gpt-4o"
                base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
            elif metin_sorusu:
                secilen_model = "gpt-4o-mini"
                messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]

            response = client.chat.completions.create(model=secilen_model, messages=messages, max_tokens=1000)
            cevap = response.choices[0].message.content
            
            st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{cevap}</div>""", unsafe_allow_html=True)

            st.write("")
            st.markdown("### 📤 Paylaş")
            paylasim_metni = urllib.parse.quote(f"ÖdevMatik Çözümü:\n\n{cevap}\n\n--- ÖdevMatik ile çözüldü.")
            whatsapp_link = f"https://api.whatsapp.com/send?text={paylasim_metni}"
            mail_link = f"mailto:?subject=ÖdevMatik Çözümü&body={paylasim_metni}"
            p_col1, p_col2 = st.columns(2)
            with p_col1: st.link_button("💬 WhatsApp", whatsapp_link, use_container_width=True)
            with p_col2: st.link_button("📧 Mail At", mail_link, use_container_width=True)

        except Exception as e:
            st.error(f"Hata: {e}")

st.divider()
st.caption("⚠️ **Yasal Uyarı:** Sonuçlar yapay zeka tarafından üretilmiştir ve hatalı olabilir.")
