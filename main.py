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
cookie_manager = stx.CookieManager(key="auth_mgr_v30")

# --- GÜNCEL MÜFREDAT (MAARİF MODELİ EKLENDİ) ---
MUFREDAT = {
    "5. Sınıf (Maarif Modeli)": {
        "Matematik": ["Doğal Sayılar ve İşlemler", "Kesirler ve Ondalık Gösterim", "Geometrik Şekiller", "Veri Toplama ve Değerlendirme", "Uzunluk ve Zaman Ölçme"],
        "Fen Bilimleri": ["Gökyüzündeki Komşularımız", "Canlılar Dünyasına Yolculuk", "Kuvvetin Etkileri", "Maddenin Değişimi", "Işığın Yayılması", "İnsan ve Çevre"],
        "Türkçe": ["Erdemler", "Milli Kültür", "Bilim ve Teknoloji", "Birey ve Toplum", "Okuma Kültürü"],
        "Sosyal Bilgiler": ["Birey ve Toplum", "Kültür ve Miras", "İnsanlar, Yerler ve Çevreler", "Üretim, Dağıtım ve Tüketim"]
    },
    "6. Sınıf": {
        "Matematik": ["Doğal Sayılarla İşlemler", "Çarpanlar ve Katlar", "Kümeler", "Tam Sayılar", "Kesirler", "Ondalık Gösterim", "Oran", "Cebirsel İfadeler", "Veri Analizi", "Açılar", "Alan Ölçme", "Çember", "Geometrik Cisimler"],
        "Fen Bilimleri": ["Güneş Sistemi ve Tutulmalar", "Vücudumuzdaki Sistemler", "Kuvvet ve Hareket", "Madde ve Isı", "Ses ve Özellikleri", "Denetleyici ve Düzenleyici Sistemler"],
        "Türkçe": ["Sözcükte Anlam", "Cümlede Anlam", "Paragraf", "İsim-Sıfat-Zamir", "Yazım Kuralları"],
        "Sosyal Bilgiler": ["Biz ve Değerlerimiz", "Tarihe Yolculuk", "Yeryüzünde Yaşam", "Bilim ve Teknoloji", "Üretiyorum, Tüketiyorum"]
    },
    "7. Sınıf": {
        "Matematik": ["Tam Sayılar", "Rasyonel Sayılar", "Cebirsel İfadeler", "Eşitlik ve Denklem", "Oran ve Orantı", "Yüzdeler", "Doğrular ve Açılar", "Çokgenler", "Çember ve Daire", "Veri Analizi"],
        "Fen Bilimleri": ["Güneş Sistemi", "Hücre ve Bölünmeler", "Kuvvet ve Enerji", "Saf Madde ve Karışımlar", "Işığın Madde ile Etkileşimi", "Canlılarda Üreme"],
        "Türkçe": ["Fiiller", "Zarflar", "Ek Fiil", "Anlatım Bozuklukları", "Metin Türleri"],
        "Sosyal Bilgiler": ["İletişim ve İnsan", "Türk Tarihinde Yolculuk", "Ülkemizde Nüfus", "Zaman İçinde Bilim", "Ekonomi ve Sosyal Hayat"]
    },
    "8. Sınıf (LGS)": {
        "Matematik": ["Çarpanlar ve Katlar", "Üslü İfadeler", "Kareköklü İfadeler", "Veri Analizi", "Olasılık", "Cebirsel İfadeler", "Doğrusal Denklemler", "Eşitsizlikler", "Üçgenler", "Eşlik ve Benzerlik", "Dönüşüm Geometrisi", "Geometrik Cisimler"],
        "Fen Bilimleri": ["Mevsimler ve İklim", "DNA ve Genetik Kod", "Basınç", "Madde ve Endüstri", "Basit Makineler", "Enerji Dönüşümleri", "Elektrik Yükleri"],
        "Türkçe": ["Fiilimsiler", "Cümlenin Ögeleri", "Fiilde Çatı", "Cümle Türleri", "Yazım ve Noktalama", "Sözel Mantık"],
        "İnkılap Tarihi": ["Bir Kahraman Doğuyor", "Milli Uyanış", "Ya İstiklal Ya Ölüm", "Atatürkçülük", "Demokratikleşme Çabaları", "Dış Politika"]
    },
    "9. Sınıf (Maarif Modeli)": {
        "Matematik": ["Sayılar ve Nicelikler", "Denklemler ve Eşitsizlikler", "Fonksiyonlar", "Üçgenler", "Veri"],
        "Edebiyat": ["Giriş", "Hikaye", "Şiir", "Masal/Fabl", "Roman", "Tiyatro", "Biyografi"]
    },
    "10. Sınıf": {
        "Matematik": ["Sayma ve Olasılık", "Fonksiyonlar", "Polinomlar", "İkinci Dereceden Denklemler", "Dörtgenler", "Katı Cisimler"],
        "Edebiyat": ["Giriş", "Hikaye", "Şiir", "Destan/Efsane", "Roman", "Tiyatro", "Anı"]
    },
    "11. Sınıf": {
        "Matematik": ["Trigonometri", "Analitik Geometri", "Fonksiyon Uygulamaları", "Denklem Sistemleri", "Çember ve Daire", "Olasılık"],
        "Edebiyat": ["Giriş", "Hikaye", "Şiir", "Makale", "Sohbet", "Roman", "Tiyatro", "Eleştiri"]
    },
    "12. Sınıf (YKS)": {
        "Matematik": ["Logaritma", "Diziler", "Trigonometri", "Dönüşümler", "Türev", "İntegral", "Çemberin Analitiği"],
        "Edebiyat": ["Giriş", "Hikaye", "Şiir", "Roman", "Tiyatro", "Deneme", "Nutuk"]
    }
}

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

# --- PDF TEMİZLEYİCİ VE OLUŞTURUCU ---
def clean_text_for_pdf(text):
    # Türkçe karakterler ve Matematik sembolleri için harita
    replacements = {
        'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ç': 'c', 'Ç': 'C', 'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
        '√': 'kok', '²': '^2', '³': '^3', 'π': 'pi', '∞': 'sonsuz', '≠': 'esit degil', '≤': '<=', '≥': '>='
    }
    # Markdown temizliği (Basitçe)
    text = text.replace('**', '').replace('__', '').replace('###', '').replace('##', '').replace('#', '')
    
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    
    # ASCII dışı karakterleri temizle (Garanti olsun diye)
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Başlık
    safe_title = clean_text_for_pdf(title)
    pdf.cell(0, 10, safe_title, ln=True, align='C')
    pdf.ln(10)
    
    # İçerik
    pdf.set_font("Arial", size=12)
    safe_content = clean_text_for_pdf(content)
    pdf.multi_cell(0, 10, safe_content)
        
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

# --- ÇEREZ ---
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
# YAN MENÜ
# ==========================================
with st.sidebar:
    st.title("🗂️ Menü")
    
    # ANA EKRAN BUTONU
    if st.button("🏠 Ana Ekran (Soru Çöz)", use_container_width=True):
        st.session_state.ozel_icerik = None
        st.session_state.son_cevap = None
        st.rerun()
    
    st.divider()

    # 1. DERS NOTU (MÜFREDATLI + DETAYLI)
    with st.expander("📚 Ders Notu Oluştur"):
        st.caption("Sınıfına uygun özet çıkar!")
        not_sinif = st.selectbox("Sınıf:", list(MUFREDAT.keys()), key="not_sinif")
        dersler = list(MUFREDAT[not_sinif].keys()) if not_sinif in MUFREDAT else ["Matematik", "Fen", "Türkçe"]
        not_ders = st.selectbox("Ders:", dersler, key="not_ders")
        konular = MUFREDAT[not_sinif].get(not_ders, ["Genel"])
        not_konu = st.selectbox("Konu:", konular, key="not_konu")
        
        if st.button("Notu Hazırla 📄"):
            if st.session_state.logged_in:
                kredi = get_credit(st.session_state.username)
                if kredi > 0:
                    deduct_credit(st.session_state.username)
                    st.toast("1 Hak kullanıldı", icon="🎫")
                    with st.spinner(f"{not_sinif} seviyesinde detaylı notlar hazırlanıyor..."):
                        # --- GÜÇLENDİRİLMİŞ PROMPT (DETAYLI ANLATIM) ---
                        not_prompt = f"""
                        GÖREV: Sen uzman bir {not_ders} öğretmenisin.
                        HEDEF KİTLE: {not_sinif} öğrencisi.
                        KONU: {not_konu}
                        
                        YAPMAN GEREKENLER:
                        1. Bu konuyu bir öğrencinin kendi başına çalışıp anlayabileceği kadar DETAYLI anlat. (En az 400 kelime).
                        2. Sadece tanım verme; mantığını, neden-sonuç ilişkisini açıkla.
                        3. "Önemli Noktalar" başlığı altında, sınavda çıkabilecek tuzakları ve ipuçlarını listele.
                        4. En az 3 adet ÇÖZÜMLÜ ÖRNEK ekle (Adım adım çözüm olsun).
                        5. Varsa formülleri veya kuralları kutu içinde gibi vurgula.
                        6. Üslubun samimi, motive edici ve akıcı olsun.
                        """
                        try:
                            # Notlar uzun olacağı için token limitini artırdım
                            resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": not_prompt}], max_tokens=1500)
                            st.session_state.ozel_icerik = resp.choices[0].message.content
                            st.session_state.icerik_tipi = "Ders Notu"
                            st.rerun()
                        except: st.error("Hata")
                else: st.error("Hakkın bitti!")
            else: st.warning("Üye olmalısın.")

    # 2. TEST HAZIRLA
    with st.expander("📝 Test Hazırla"):
        st.caption("Kendini test et!")
        q_sinif = st.selectbox("Sınıf:", list(MUFREDAT.keys()), key="q_sinif")
        q_dersler = list(MUFREDAT[q_sinif].keys()) if q_sinif in MUFREDAT else ["Matematik", "Fen"]
        q_ders = st.selectbox("Ders:", q_dersler, key="q_ders")
        q_konular = MUFREDAT[q_sinif].get(q_ders, ["Genel"])
        q_konu = st.selectbox("Konu:", q_konular, key="q_konu")
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

# --- ÖZEL İÇERİK (NOT/TEST) ---
if st.session_state.ozel_icerik:
    st.info(f"📢 **{st.session_state.icerik_tipi} Hazır:**")
    st.markdown(f"""<div style="background-color:#fff9c4;padding:20px;border-radius:10px;color:#000080;font-size:18px;">{st.session_state.ozel_icerik}</div>""", unsafe_allow_html=True)
    
    # PDF İNDİR (TEMİZLENMİŞ)
    try:
        pdf_data = create_pdf(f"OdevMatik {st.session_state.icerik_tipi}", st.session_state.ozel_icerik)
        b64_pdf = base64.b64encode(pdf_data).decode('latin-1')
        href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="odevmatik_cikti.pdf"><button style="width:100%;height:50px;border-radius:10px;background-color:#FF5722;color:white;font-weight:bold;border:none;cursor:pointer;">📥 PDF Olarak İndir</button></a>'
        st.markdown(href, unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"PDF Oluşturulamadı: {e}")
    
    st.markdown("---")
    if st.button("⬅️ Geri Dön (Ana Ekran)"):
        st.session_state.ozel_icerik = None
        st.rerun()

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
        st.divider()

    # Kilit Kontrolü
    if guest_locked and not st.session_state.logged_in:
        st.warning("⚠️ Misafir hakkını kullandın! Yeni soru için lütfen sağ üstten **Giriş Yap** veya **Kayıt Ol**.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📁 Galeri", use_container_width=True): 
                st.session_state.aktif_mod = "Galeri"
        with col2:
            if st.button("📸 Kamera", use_container_width=True): 
                st.session_state.aktif_mod = "Kamera"
        with col3:
            if st.button("⌨️ Yaz", use_container_width=True): 
                st.session_state.aktif_mod = "Yaz"

        if "aktif_mod" not in st.session_state: st.session_state.aktif_mod = "Galeri"

        st.write("")

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
                can_proceed = True

            if can_proceed:
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
                        
                        if st.session_state.logged_in:
                            save_history(st.session_state.username, "Soru", cevap)
                        
                        st.session_state.son_cevap = cevap
                        
                        if not st.session_state.logged_in:
                            st.session_state.guest_locked_session = True
                            try:
                                cookie_manager.set("guest_used", "true", expires_at=datetime.datetime.now() + datetime.timedelta(days=1))
                            except: pass
                        
                        st.rerun()

                    except Exception as e:
                        st.error(f"Hata: {e}")

st.divider()
st.caption("⚠️ **Yasal Uyarı:** Sonuçlar yapay zeka tarafından üretilmiştir ve hatalı olabilir.")
