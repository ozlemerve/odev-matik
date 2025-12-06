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

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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

# --- E-POSTA GÖNDERME FONKSİYONU (PROFESYONEL İSİMLİ) ---
def send_verification_email(to_email, code):
    try:
        sender_email = st.secrets["EMAIL_ADDRESS"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
    except:
        st.error("Mail ayarları (Secrets) yapılmamış!")
        return False
    
    subject = "ÖdevMatik Doğrulama Kodu"
    body = f"Merhaba,\n\nÖdevMatik kayıt işleminiz için doğrulama kodunuz: {code}\n\nBu kodu kimseyle paylaşmayın.\n\nSevgiler,\nÖdevMatik Ekibi"

    msg = MIMEMultipart()
    
    # --- İŞTE DÜZELTİLEN YER ---
    # Mail adresi yerine "ÖdevMatik Güvenlik" yazacak
    msg['From'] = f"ÖdevMatik Güvenlik <{sender_email}>"
    # ---------------------------
    
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
    except Exception as e:
        st.error(f"Mail gönderme hatası: {e}")
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

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "verification_code" not in st.session_state: st.session_state.verification_code = None

# ==========================================
# 1. BÖLÜM: GİRİŞ VE KAYIT EKRANI
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
        st.info("Yeni hesap oluştur. **Gerçek mailini gir, kod gelecek!**")
        
        # Adım 1: Mail ve Şifre Gir
        reg_email = st.text_input("E-posta Adresi:", key="reg_email")
        reg_pass = st.text_input("Şifre Belirle:", type='password', key="reg_pass")
        
        col_k1, col_k2 = st.columns([1, 2])
        
        # Doğrulama Kodu Gönder Butonu
        if col_k1.button("Kod Gönder"):
            if reg_email and "@" in reg_email:
                code = str(random.randint(1000, 9999))
                if send_verification_email(reg_email, code):
                    st.session_state.verification_code = code
                    st.success(f"Kod {reg_email} adresine gönderildi!")
                else:
                    st.error("Mail gönderilemedi.")
            else:
                st.warning("Geçerli bir e-posta giriniz.")

        # Adım 2: Kodu Doğrula ve Kayıt Ol
        if st.session_state.verification_code:
            entered_code = st.text_input("Gelen 4 Haneli Kodu Girin:")
            if st.button("Doğrula ve Kayıt Ol", type="primary"):
                if entered_code == st.session_state.verification_code:
                    if add_user(reg_email, reg_pass):
                        st.success("Tebrikler! Kayıt oldun. Şimdi 'Giriş Yap' sekmesinden girebilirsin.")
                        st.session_state.verification_code = None # Kodu sıfırla
                    else:
                        st.error("Bu e-posta zaten kayıtlı.")
                else:
                    st.error("Hatalı kod!")

    st.stop() 

# ==========================================
# 2. BÖLÜM: UYGULAMA İÇERİSİ
# ==========================================

current_credit = get_credit(st.session_state.username)

with st.sidebar:
    st.title(f"👤 {st.session_state.username.split('@')[0]}")
    st.metric("Kalan Hakkın", f"{current_credit} Soru")
    
    if current_credit == 0:
        st.error("Hakkın bitti!")
        st.button("💎 Premium Al")
    
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()
    
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        st.warning("API Key Eksik!")
        st.stop()

client = OpenAI(api_key=api_key)

st.markdown("<h1>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
st.markdown("<p>Ödev asistanın cebinde!</p>", unsafe_allow_html=True)
st.write("")

if current_credit <= 0:
    st.error("😔 Üzgünüm, bugünkü soru sorma hakkın bitti!")
    st.info("Daha fazla soru sormak için yarını bekleyebilirsin.")
    st.stop() 

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📁 Galeri", use_container_width=True): st.session_state.aktif_mod = "Galeri"
with col2:
    if st.button("📸 Kamera", use_container_width=True): st.session_state.aktif_mod = "Kamera"
with col3:
    if st.button("⌨️ Yaz", use_container_width=True): st.session_state.aktif_mod = "Yaz"

if "aktif_mod" not in st.session_state: st.session_state.aktif_mod = "Galeri"

st.divider()

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

if form_tetiklendi:
    deduct_credit(st.session_state.username)
    st.toast("Kredinizden 1 hak düştü!", icon="🎫")
    
    with st.spinner(random.choice(["Hoca bakıyor...", "İşlemler yapılıyor...", "Çözülüyor..."])):
        try:
            ana_prompt = """GÖREV: Soruyu öğrenci gibi çöz. Adım adım git. LaTeX kullanma. Samimi ol. Sonucu net belirt."""

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
st.caption("⚠️ **Yasal Uyarı:** Sonuçlar yapay zeka tarafından üretilmiştir ve hatalı olabilir. Lütfen kontrol ediniz.")
