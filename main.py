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

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ÇEREZ YÖNETİCİSİ ---
cookie_manager = stx.CookieManager(key="auth_mgr_final")

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

# --- PDF OLUŞTURMA ---
def create_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    safe_title = title.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, safe_title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, safe_line)
    return pdf.output(dest='S').encode('latin-1')

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

# --- OTURUM ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Misafir"
if "verification_code" not in st.session_state: st.session_state.verification_code = None
if "son_cevap" not in st.session_state: st.session_state.son_cevap = None
if "guest_locked_session" not in st.session_state: st.session_state.guest_locked_session = False
if "ozel_icerik" not in st.session_state: st.session_state.ozel_icerik = None # Notlar için hafıza

# --- ÇEREZ KONTROLÜ ---
time.sleep(0.1)
try:
    cookies = cookie_manager.get_all()
    user_token = cookies.get("user_token")
    if user_token and not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.username = user_token
        st.rerun()
except:
    pass

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
# YAN MENÜ (NAVİGASYONLU)
# ==========================================
with st.sidebar:
    st.title("🗂️ Menü")
    
    # --- YENİ: ANA EKRAN TUŞU ---
    if st.button("🏠 Ana Ekran (Soru Çöz)", use_container_width=True):
        st.session_state.ozel_icerik = None # Notları kapat
        st.session_state.son_cevap = None # Eski cevabı temizle (isteğe bağlı)
        st.rerun()
    
    st.divider()

    # 1. DERS NOTU OLUŞTUR (İsim Güncellendi)
    with st.expander("📚 Ders Notu Oluştur"):
        st.caption("Sınıfına uygun özet çıkar!")
        sinif_seviyesi = st.selectbox("Sınıf Seviyesi:", ["5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "9. Sınıf (Lise 1)", "10. Sınıf (Lise 2)", "11. Sınıf (Lise 3)", "12. Sınıf (YKS)"], key="not_sinif")
        ders_secimi = st.selectbox("Ders:", ["Matematik", "Fen Bilimleri", "Türkçe", "İnkılap Tarihi", "İngilizce", "Din Kültürü"], key="not_ders")
        konu_girisi = st.text_input("Konu (Örn: Çarpanlar):", key="not_konu")
        
        if st.button("Notu Hazırla 📄"):
            if st.session_state.logged_in:
                kredi = get_credit(st.session_state.username)
                if kredi > 0:
                    deduct_credit(st.session_state.username)
                    st.toast("1 Hak kullanıldı", icon="🎫")
                    with st.spinner(f"{sinif_seviyesi} seviyesinde notlar hazırlanıyor..."):
                        not_prompt = f"""ROL: {ders_secimi} öğretmeni. HEDEF: {sinif_seviyesi}. KONU: {konu_girisi}. Özetle, formülleri ver, hap bilgi ver."""
                        try:
                            resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": not_prompt}], max_tokens=1000)
                            st.session_state.ozel_icerik = resp.choices[0].message.content
                            st.session_state.icerik_tipi = "Ders Notu"
                            st.rerun() # Sayfayı yenile ki ana ekranda çıksın
                        except: st.error("Hata")
                else: st.error("Hakkın bitti!")
            else: st.warning("Üye olmalısın.")

    # 2. TEST HAZIRLA (İsim Güncellendi)
    with st.expander("📝 Test Hazırla"):
        st.caption("Kendini test et!")
        q_sinif = st.selectbox("Sınıf:", ["5", "6", "7", "8", "9", "10", "11", "12"], key="q_sinif")
        q_ders = st.selectbox("Ders:", ["Matematik", "Fen", "Türkçe", "Sosyal"], key="q_ders")
        q_konu = st.text_input("Konu:", key="q_konu")
        q_zorluk = st.select_slider("Zorluk:", options=["Kolay", "Orta", "Zor"])
        q_tip = st.radio("Tip:", ["Çoktan Seçmeli", "Klasik"], horizontal=True)
        
        if st.button("Soru Yazdır ✍️"):
            if st.session_state.logged_in:
                kredi = get_credit(st.session_state.username)
                if kredi > 0:
                    deduct_credit(st.session_state.username)
                    st.toast("1 Hak kullanıldı", icon="🎫")
                    with st.spinner("Soru yazılıyor..."):
                        soru_prompt = f"""GÖREV: {q_sinif}. Sınıf {q_ders} sorusu yaz. KONU: {q_konu}. ZORLUK: {q_zorluk}. TİP: {q_tip}. Cevabı altına 'ÇÖZÜM:' diye ekle."""
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
        total_solved = get_total_solved(st.session_state.username)
        st.write(f"**Toplam İşlem:** {total_solved}")
        if st.button("🚪 Çıkış Yap"):
            st.session_state.logged_in = False
            st.session_state.username = "Misafir"
            cookie_manager.delete("user_token")
            st.rerun()
    
    if st.checkbox("Admin Modu"):
        if st.button("Sıfırla"):
            try: 
                cookie_manager.delete("guest_used")
                st.session_state.guest_locked_session = False
                st.rerun()
            except: pass

# ==========================================
# ANA EKRAN AKIŞI
# ==========================================

# MİSAFİR KİLİDİ
guest_locked = False
if not st.session_state.logged_in:
    if st.session_state.guest_locked_session:
        guest_locked = True
    else:
        try:
            cookies = cookie_manager.get_all()
            if "guest_used" in cookies:
                guest_locked = True
                st.session_state.guest_locked_session = True
        except: pass

# --- ÖZEL İÇERİK GÖSTERİMİ (NOT/TEST) ---
# Eğer özel içerik (not/test) varsa onu göster, soru sorma ekranını gizle
if st.session_state.ozel_icerik:
    st.info(f"📢 **{st.session_state.icerik_tipi} Hazır:**")
    st.markdown(f"""<div style="background-color:#fff9c4;padding:20px;border-radius:10px;color:#000080;font-size:18px;">{st.session_state.ozel_icerik}</div>""", unsafe_allow_html=True)
    
    # PDF İNDİR
    try:
        pdf_data = create_pdf(f"OdevMatik {st.session_state.icerik_tipi}", st.session_state.ozel_icerik)
        b64_pdf = base64.b64encode(pdf_data).decode('latin-1')
        href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="odevmatik_cikti.pdf"><button style="width:100%;height:50px;border-radius:10px;background-color:#FF5722;color:white;font-weight:bold;border:none;cursor:pointer;">📥 PDF Olarak İndir</button></a>'
        st.markdown(href, unsafe_allow_html=True)
    except: st.caption("PDF karakter hatası.")
    
    st.markdown("---")
    if st.button("⬅️ Geri Dön (Ana Ekran)"):
        st.session_state.ozel_icerik = None
        st.rerun()

# --- NORMAL SORU ÇÖZME EKRANI (Eğer özel içerik yoksa burası çalışır) ---
else:
    # Eski Cevap Varsa Göster
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
        st.divider
