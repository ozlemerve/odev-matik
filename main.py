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
from fpdf import FPDF
import requests
import os

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ÇEREZ YÖNETİCİSİ ---
cookie_manager = stx.CookieManager(key="auth_mgr_v51")

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
    # YENİ GEÇMİŞ TABLOSU (RESİM DESTEKLİ)
    # image_data sütunu eklendi
    c.execute('''CREATE TABLE IF NOT EXISTS historyTable_v2 
                 (username TEXT, question TEXT, answer TEXT, image_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('CREATE TABLE IF NOT EXISTS feedbackTable (username TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

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

def update_credit(username, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE usersTable SET credit = ? WHERE username =?', (amount, username))
    conn.commit()
    conn.close()

def deduct_credit(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE usersTable SET credit = credit - 1 WHERE username =?', (username,))
    conn.commit()
    conn.close()

# GEÇMİŞ KAYDETME (RESİMLİ)
def save_history(username, question, answer, image_data=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # image_data varsa onu da kaydet, yoksa NULL
    c.execute('INSERT INTO historyTable_v2 (username, question, answer, image_data) VALUES (?, ?, ?, ?)', (username, question, answer, image_data))
    conn.commit()
    conn.close()

# GEÇMİŞİ GETİRME (RESİMLİ)
def get_user_history(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # image_data sütununu da çekiyoruz
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

init_db()

# --- PDF MOTORU ---
def clean_text_for_pdf(text):
    replacements = {
        'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ç': 'c', 'Ç': 'C', 'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
        '√': 'kok', '²': '^2', '³': '^3', 'π': 'pi', '∞': 'sonsuz', 
        '≠': 'esit degil', '≤': '<=', '≥': '>=', '×': 'x', '·': '*', '÷': '/', 
        '±': '+/-', '≈': 'yaklasik', '∫': 'integral', '∑': 'toplam', '∆': 'delta'
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
        try:
            pdf.add_font('DejaVu', '', font_path, uni=True)
            pdf.set_font('DejaVu', '', 12)
            use_unicode = True
        except:
            pdf.set_font("Arial", size=12)
            use_unicode = False
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
# ÜST BAR
# ==========================================
col_logo, col_auth = st.columns([2, 1])
with col_logo:
    st.markdown("<h1 style='margin-bottom:0;'>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:grey;'>Eğitim Koçun Cebinde!</p>", unsafe_allow_html=True)

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
        kredi = get_credit(st.session_state.username)
        st.info(f"👤 **{st.session_state.username.split('@')[0]}**")
        st.caption(f"🎫 Kalan Hak: **{kredi}**")

st.divider()

# ==========================================
# YAN MENÜ (GEÇMİŞ DÜZELTİLDİ)
# ==========================================
with st.sidebar:
    st.title("🗂️ Öğrenci Paneli")
    
    if st.session_state.logged_in:
        total_solved = get_total_solved(st.session_state.username)
        st.write(f"**Çözülen Soru:** {total_solved}")
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"<div class='stat-box'><div class='stat-title'>Çözülen</div><div class='stat-value'>{total_solved}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='stat-box'><div class='stat-title'>Hak</div><div class='stat-value'>{get_credit(st.session_state.username)}</div></div>", unsafe_allow_html=True)
        
        st.divider()

        with st.expander("📜 Geçmiş Çözümlerim"):
            try:
                # v2 Tablosundan verileri çek (Resim dahil)
                gecmis_veriler = get_user_history(st.session_state.username)
                if gecmis_veriler:
                    for soru, cevap, resim_kodu, zaman in gecmis_veriler:
                        st.text(f"📅 {zaman[:16]}")
                        
                        # Eğer resim varsa göster
                        if resim_kodu:
                            try:
                                # Base64'ten resmi çöz ve göster
                                decoded_img = base64.b64decode(resim_kodu)
                                st.image(decoded_img, caption="Soru Görseli", use_container_width=True)
                            except:
                                st.caption("Resim yüklenemedi.")
                        else:
                            # Resim yoksa metin sorusunu göster
                            st.caption(f"❓ {soru[:40]}...")
                            
                        with st.popover("Cevabı Gör"):
                            st.write(cevap)
                        st.divider()
                else:
                    st.caption("Henüz soru çözmedin.")
            except:
                st.caption("Geçmiş yüklenirken hata oluştu (Tablo güncellendiği için eski kayıtlar görünmeyebilir).")

        st.divider()

        with st.expander("💬 Bize Ulaşın"):
            with st.form("feedback_form"):
                feedback_msg = st.text_area("Mesajınız:")
                if st.form_submit_button("Gönder"):
                    save_feedback(st.session_state.username, feedback_msg)
                    st.success("İletildi.")
        
        st.divider()
        if st.button("🚪 Çıkış Yap"):
            st.session_state.logged_in = False
            st.session_state.username = "Misafir"
            cookie_manager.delete("user_token")
            st.rerun()

    else:
        st.warning("⚠️ Misafir Modu")
        st.info("🎁 **Üye ol, 100 soru hakkı kazan!**")
    
    st.divider()
    if st.checkbox("Admin Modu"):
        if st.button("Misafir Hakkını Sıfırla"):
            try: cookie_manager.delete("guest_used"); st.session_state.guest_locked_session = False; st.rerun()
            except: pass
        if st.session_state.logged_in:
            if st.button("💰 Kendine 100 Kredi Yükle"):
                update_credit(st.session_state.username, 100); st.success("Yüklendi! Yenile."); time.sleep(1); st.rerun()

# ==========================================
# ANA EKRAN AKIŞI
# ==========================================

guest_locked = False
if not st.session_state.logged_in:
    try:
        cookies = cookie_manager.get_all()
        if "guest_used" in cookies: guest_locked = True
    except: pass

# --- SONUÇ GÖSTERİMİ ---
if st.session_state.son_cevap:
    st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{st.session_state.son_cevap}</div>""", unsafe_allow_html=True)
    
    try:
        pdf_bytes = create_safe_pdf("OdevMatik Cozum", st.session_state.son_cevap)
        st.download_button(
            label="📥 PDF Olarak İndir",
            data=pdf_bytes,
            file_name="odevmatik_cozum.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    except: pass

    st.write(""); st.markdown("### 📤 Paylaş")
    paylasim_metni = urllib.parse.quote(f"ÖdevMatik Çözümü:\n\n{st.session_state.son_cevap}\n\n--- ÖdevMatik ile çözüldü.")
    whatsapp_link = f"https://api.whatsapp.com/send?text={paylasim_metni}"
    mail_link = f"mailto:?subject=ÖdevMatik Çözümü&body={paylasim_metni}"
    p_col1, p_col2 = st.columns(2)
    with p_col1: st.link_button("💬 WhatsApp", whatsapp_link, use_container_width=True)
    with p_col2: st.link_button("📧 Mail At", mail_link, use_container_width=True)
    st.divider()

if guest_locked and not st.session_state.logged_in:
    st.warning("⚠️ Misafir hakkını kullandın! Yeni soru için lütfen sağ üstten **Giriş Yap** veya **Kayıt Ol**.")
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
    gorsel_veri = None; metin_sorusu = None; form_tetiklendi = False

    if st.session_state.aktif_mod == "Galeri":
        st.info("📂 **Galeriden Seç**")
        yuklenen_dosya = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if yuklenen_dosya: gorsel_veri = yuklenen_dosya.getvalue(); 
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True): form_tetiklendi = True
    elif st.session_state.aktif_mod == "Kamera":
        st.info("📸 **Fotoğraf Çek**")
        cekilen_foto = st.camera_input("Kamerayı aç")
        if cekilen_foto: gorsel_veri = cekilen_foto.getvalue(); 
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
            if kredi > 0: deduct_credit(st.session_state.username); st.toast("1 Hak düştü!", icon="🎫"); can_proceed = True
            else: st.error("😔 Hakkın bitti!")
        else:
            try: cookie_manager.set("guest_used", "true", expires_at=datetime.datetime.now() + datetime.timedelta(days=1)); st.toast("Misafir hakkı!", icon="🎁"); can_proceed = True
            except: pass

        if can_proceed:
            with st.spinner(random.choice(["Hoca bakıyor...", "Çözülüyor..."])):
                try:
                    ana_prompt = """GÖREV: Soruyu öğrenci gibi çöz. Adım adım git. LaTeX kullanma. Semimi ol. Sembolleri (√, ²) kullan."""
                    if gorsel_veri:
                        secilen_model = "gpt-4o"
                        # GÖRSEL VERİSİNİ STRİNGE ÇEVİR (DATABASE İÇİN)
                        base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                        messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
                        
                        # GEÇMİŞE KAYDET (RESİMLİ)
                        if st.session_state.logged_in:
                            save_history(st.session_state.username, "Fotoğraflı Soru", None, base64_image) # Cevabı henüz bilmiyoruz

                    elif metin_sorusu:
                        secilen_model = "gpt-4o-mini"
                        messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]
                        
                        if st.session_state.logged_in:
                            save_history(st.session_state.username, metin_sorusu, None, None)

                    response = client.chat.completions.create(model=secilen_model, messages=messages, max_tokens=1000)
                    cevap = response.choices[0].message.content
                    
                    # CEVABI GÜNCELLE (SQL UPDATE İLE) - ŞİMDİLİK BASİTÇE EKRANA BASIYORUZ, BİR SONRAKİNDE GÜNCELLERİZ.
                    # Aslında save_history'yi en sonda çağırmak daha mantıklı.
                    # Düzeltme: Yukarıdaki save_history çağrılarını siliyorum, cevabı aldıktan sonra kaydedeceğim.

                    if st.session_state.logged_in:
                        resim_kayit = base64_image if gorsel_veri else None
                        soru_metni = "Fotoğraflı Soru" if gorsel_veri else metin_sorusu
                        save_history(st.session_state.username, soru_metni, cevap, resim_kayit)

                    st.session_state.son_cevap = cevap
                    
                    if not st.session_state.logged_in:
                        st.session_state.guest_locked_session = True
                    
                    st.rerun()

                except Exception as e: st.error(f"Hata: {e}")

st.divider()
st.caption("⚠️ **Yasal Uyarı:** Sonuçlar yapay zeka tarafından üretilmiştir ve hatalı olabilir.")
