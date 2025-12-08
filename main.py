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
cookie_manager = stx.CookieManager(key="auth_mgr_v35")

# --- MÜFREDAT (GÜNCEL) ---
MUFREDAT = {
    "5. Sınıf (Maarif)": {
        "Matematik": ["Doğal Sayılar", "Kesirler", "Ondalık Gösterim", "Yüzdeler", "Geometrik Cisimler"],
        "Fen": ["Güneş, Dünya, Ay", "Canlılar", "Kuvvet", "Madde", "Işık", "Elektrik"],
        "Türkçe": ["Okuma Kültürü", "Erdemler", "Bilim", "Milli Kültür"],
        "Sosyal": ["Birey ve Toplum", "Kültür", "Yeryüzü", "Bilim", "Ekonomi"]
    },
    "6. Sınıf (Maarif)": {
        "Matematik": ["Doğal Sayılar", "Çarpanlar", "Kümeler", "Tam Sayılar", "Kesirler", "Ondalık", "Oran", "Cebir", "Veri", "Açılar"],
        "Fen": ["Güneş Sistemi", "Vücudumuz", "Kuvvet", "Madde", "Ses", "Elektrik"],
        "Türkçe": ["Duygular", "Doğa", "Milli Mücadele", "Bilim", "Sanat"],
        "Sosyal": ["Değerlerimiz", "Tarih", "Coğrafya", "Bilim", "Ekonomi", "Yönetim"]
    },
    "7. Sınıf": {
        "Matematik": ["Tam Sayılar", "Rasyonel Sayılar", "Cebirsel", "Denklem", "Oran-Orantı", "Yüzdeler", "Doğrular", "Çokgenler", "Çember"],
        "Fen": ["Uzay", "Hücre", "Kuvvet-Enerji", "Madde", "Işık", "Canlılar", "Elektrik"],
        "Türkçe": ["Erdemler", "Milli Kültür", "Kişisel Gelişim", "Sanat"],
        "Sosyal": ["İletişim", "Tarih", "Nüfus", "Bilim", "Ekonomi"]
    },
    "8. Sınıf (LGS)": {
        "Matematik": ["Çarpanlar Katlar", "Üslü Sayılar", "Kareköklü İfadeler", "Veri Analizi", "Olasılık", "Cebirsel", "Denklem", "Eşitsizlik", "Üçgenler", "Dönüşüm", "Cisimler"],
        "Fen": ["Mevsimler", "DNA", "Basınç", "Madde", "Basit Makineler", "Enerji", "Elektrik"],
        "Türkçe": ["Fiilimsiler", "Cümle Ögeleri", "Çatı", "Cümle Türleri", "Yazım", "Mantık"],
        "İnkılap": ["Bir Kahraman Doğuyor", "Milli Uyanış", "Ya İstiklal", "Atatürkçülük", "Demokratikleşme", "Dış Politika"]
    },
    "9. Sınıf (Maarif)": { "Matematik": ["Mantık", "Kümeler", "Denklemler", "Üçgenler", "Veri"], "Fizik": ["Fizik Bilimi", "Madde", "Hareket", "Enerji", "Isı", "Elektrostatik"], "Kimya": ["Kimya Bilimi", "Atom", "Etkileşimler", "Hal Değişimi"], "Biyoloji": ["Canlılık", "Hücre", "Canlılar Dünyası"] },
    "10. Sınıf (Maarif)": { "Matematik": ["Sayma Olasılık", "Fonksiyon", "Polinom", "Denklem", "Dörtgen", "Katı Cisim"], "Fizik": ["Elektrik", "Basınç", "Dalgalar", "Optik"], "Kimya": ["Kanunlar", "Karışımlar", "Asit-Baz"], "Biyoloji": ["Bölünmeler", "Kalıtım", "Ekosistem"] },
    "11. Sınıf": { "Matematik": ["Trigonometri", "Analitik", "Fonksiyon", "Denklem Sis.", "Çember", "Olasılık"], "Fizik": ["Kuvvet", "Elektrik"], "Kimya": ["Atom", "Gazlar", "Çözeltiler", "Enerji", "Hız", "Denge"], "Biyoloji": ["Sistemler", "Komünite"] },
    "12. Sınıf": { "Matematik": ["Logaritma", "Dizi", "Trigonometri", "Dönüşüm", "Türev", "İntegral", "Çember Analitiği"], "Fizik": ["Çembersel", "Harmonik", "Dalga M.", "Atom Fiziği", "Modern Fizik"], "Kimya": ["Elektrik", "Organik"], "Biyoloji": ["Genden Proteine", "Enerji", "Bitki"] }
}

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
    c.execute('''CREATE TABLE IF NOT EXISTS historyTable (username TEXT, question TEXT, answer TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
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

# --- FONT YÖNETİCİSİ ---
def download_font():
    font_url = "https://github.com/realsung/whiteboard/raw/master/src/fonts/DejaVuSans.ttf"
    if not os.path.exists("DejaVuSans.ttf"):
        response = requests.get(font_url)
        with open("DejaVuSans.ttf", "wb") as f:
            f.write(response.content)

def create_pdf_with_math(title, content):
    download_font()
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.set_font('DejaVu', '', 14)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('DejaVu', '', 11)
    pdf.multi_cell(0, 7, content)
    return pdf.output(dest='S').encode('latin-1')

# --- E-POSTA ---
def send_verification_email(to_email, code):
    try:
        sender_email = st.secrets["EMAIL_ADDRESS"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
    except: return False
    subject = "ÖdevMatik Kod"
    body = f"Kodun: {code}"
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
if "guest_locked_session" not in st.session_state: st.session_state.guest_locked_session = False
if "ozel_icerik" not in st.session_state: st.session_state.ozel_icerik = None

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
# YAN MENÜ
# ==========================================
with st.sidebar:
    st.title("🗂️ Menü")
    if st.button("🏠 Ana Ekran", use_container_width=True):
        st.session_state.ozel_icerik = None
        st.session_state.son_cevap = None
        st.rerun()
    st.divider()

    # 1. DERS NOTU (ÖZEL AYAR: MATEMATİK 15 SORU)
    with st.expander("📚 Ders Notu Oluştur"):
        st.caption("Detaylı ve sembollü anlatım!")
        not_sinif = st.selectbox("Sınıf:", list(MUFREDAT.keys()), key="not_sinif")
        dersler = list(MUFREDAT[not_sinif].keys()) if not_sinif in MUFREDAT else ["Matematik"]
        not_ders = st.selectbox("Ders:", dersler, key="not_ders")
        konular = MUFREDAT[not_sinif].get(not_ders, ["Genel"])
        not_konu = st.selectbox("Konu:", konular, key="not_konu")
        
        if st.button("Notu Hazırla 📄"):
            if st.session_state.logged_in:
                kredi = get_credit(st.session_state.username)
                if kredi > 0:
                    deduct_credit(st.session_state.username)
                    st.toast("1 Hak kullanıldı", icon="🎫")
                    with st.spinner("Hazırlanıyor..."):
                        
                        # --- ÖZEL MATEMATİK PROMPTU ---
                        if not_ders == "Matematik":
                            not_prompt = f"""
                            SEN BİR MATEMATİK DERS KİTABI YAZARISIN.
                            DERS: Matematik. SINIF: {not_sinif}. KONU: {not_konu}.
                            
                            GÖREVLER:
                            1. Konuyu BÜTÜN DETAYLARIYLA, ispatlarıyla anlat.
                            2. "Tanım", "Kural", "Uyarı" başlıkları kullan.
                            3. İçerik EN AZ 1100 KELİME olacak. Kısa kesme.
                            4. EN AZ 15 ADET "Çözümlü Örnek" ekle. Örnekler kolaydan zora gitsin. Çözümleri adım adım göster.
                            5. Matematik sembollerini (√, ², π, ∫) DOĞRUDAN kullan. LaTeX kullanma.
                            """
                        else:
                            # Diğer dersler için standart ama dolu prompt
                            not_prompt = f"""
                            SEN BİR DERS KİTABI YAZARISIN.
                            DERS: {not_ders}. SINIF: {not_sinif}. KONU: {not_konu}.
                            
                            GÖREVLER:
                            1. Konuyu akademik ve detaylı anlat. Sohbet dili kullanma.
                            2. En az 800 kelime olsun.
                            3. En az 3 tane çözümlü/açıklamalı örnek ver.
                            4. Önemli yerleri vurgula.
                            """
                            
                        try:
                            # Matematik için limiti artırdık (3000 Token)
                            max_tok = 3000 if not_ders == "Matematik" else 2000
                            resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": not_prompt}], max_tokens=max_tok)
                            st.session_state.ozel_icerik = resp.choices[0].message.content
                            st.session_state.icerik_tipi = "Ders Notu"
                            st.rerun()
                        except: st.error("Hata")
                else: st.error("Hakkın bitti!")
            else: st.warning("Üye olmalısın.")

    # 2. TEST HAZIRLA
    with st.expander("📝 Test Hazırla"):
        q_sinif = st.selectbox("Sınıf:", list(MUFREDAT.keys()), key="q_sinif")
        q_dersler = list(MUFREDAT[q_sinif].keys()) if q_sinif in MUFREDAT else ["Matematik"]
        q_ders = st.selectbox("Ders:", q_dersler, key="q_ders")
        q_konular = MUFREDAT[q_sinif].get(q_ders, ["Genel"])
        q_konu = st.selectbox("Konu:", q_konular, key="q_konu")
        q_zorluk = st.select_slider("Zorluk:", options=["Kolay", "Orta", "Zor"])
        
        if st.button("Soru Yazdır ✍️"):
            if st.session_state.logged_in:
                kredi = get_credit(st.session_state.username)
                if kredi > 0:
                    deduct_credit(st.session_state.username)
                    st.toast("1 Hak kullanıldı", icon="🎫")
                    with st.spinner("Soru yazılıyor..."):
                        soru_prompt = f"""
                        GÖREV: {q_sinif} {q_ders} "{q_konu}" konusu. {q_zorluk} seviye 1 adet soru yaz.
                        KURAL: LaTeX kullanma, sembolleri (√, ², π) doğrudan kullan.
                        Cevabı altına 'ÇÖZÜM:' başlığıyla ekle.
                        """
                        try:
                            resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": soru_prompt}], max_tokens=1000)
                            st.session_state.ozel_icerik = resp.choices[0].message.content
                            st.session_state.icerik_tipi = "Test Sorusu"
                            st.rerun()
                        except: st.error("Hata")
                else: st.error("Hakkın bitti!")
            else: st.warning("Üye olmalısın.")

    st.divider()
    if st.session_state.logged_in:
        if st.button("🚪 Çıkış Yap"):
            st.session_state.logged_in = False
            st.session_state.username = "Misafir"
            cookie_manager.delete("user_token")
            st.rerun()
            
    if st.checkbox("Admin Modu"):
        if st.button("Misafir Hakkını Sıfırla"):
            try: cookie_manager.delete("guest_used"); st.session_state.guest_locked_session = False; st.rerun()
            except: pass
        if st.session_state.logged_in:
            if st.button("💰 Kendine 100 Kredi Yükle"):
                update_credit(st.session_state.username, 100)
                st.success("Yüklendi! Yenile.")
                time.sleep(1)
                st.rerun()

# ==========================================
# ANA EKRAN AKIŞI
# ==========================================

guest_locked = False
if not st.session_state.logged_in:
    if st.session_state.guest_locked_session: guest_locked = True
    else:
        try:
            cookies = cookie_manager.get_all()
            if "guest_used" in cookies: guest_locked = True; st.session_state.guest_locked_session = True
        except: pass

# --- ÖZEL İÇERİK ---
if st.session_state.ozel_icerik:
    st.info(f"📢 **{st.session_state.icerik_tipi} Hazır:**")
    st.markdown(f"""<div style="background-color:#fff9c4;padding:20px;border-radius:10px;color:#000080;font-size:18px;">{st.session_state.ozel_icerik}</div>""", unsafe_allow_html=True)
    
    try:
        pdf_data = create_pdf_with_math(f"OdevMatik {st.session_state.icerik_tipi}", st.session_state.ozel_icerik)
        b64_pdf = base64.b64encode(pdf_data).decode('latin-1')
        href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="odevmatik_not.pdf"><button style="width:100%;height:50px;border-radius:10px;background-color:#FF5722;color:white;font-weight:bold;border:none;cursor:pointer;">📥 PDF Olarak İndir (Sembollü)</button></a>'
        st.markdown(href, unsafe_allow_html=True)
    except Exception as e: st.caption(f"PDF Hatası: {e}")
    
    st.markdown("---")
    if st.button("⬅️ Geri Dön (Ana Ekran)"): st.session_state.ozel_icerik = None; st.rerun()

else:
    # SONUÇ GÖSTERİMİ
    if st.session_state.son_cevap:
        st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{st.session_state.son_cevap}</div>""", unsafe_allow_html=True)
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
                            base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                            messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
                        elif metin_sorusu:
                            secilen_model = "gpt-4o-mini"
                            messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]

                        response = client.chat.completions.create(model=secilen_model, messages=messages, max_tokens=1000)
                        cevap = response.choices[0].message.content
                        if st.session_state.logged_in: save_history(st.session_state.username, "Soru", cevap)
                        st.session_state.son_cevap = cevap
                        if not st.session_state.logged_in:
                            st.session_state.guest_locked_session = True
                        st.rerun()
                    except Exception as e: st.error(f"Hata: {e}")

st.divider()
st.caption("⚠️ **Yasal Uyarı:** Sonuçlar yapay zeka tarafından üretilmiştir ve hatalı olabilir.")
