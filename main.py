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

# --- VERİTABANI FONKSİYONLARI (SQLite) ---
# Bu kısım kullanıcıları ve kredilerini hafızada tutar
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Kullanıcı tablosu: kullanıcı adı, şifre, kredi
    c.execute('CREATE TABLE IF NOT EXISTS usersTable (username TEXT PRIMARY KEY, password TEXT, credit INTEGER)')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Yeni kullanıcıya varsayılan 5 kredi veriyoruz
        c.execute('INSERT INTO usersTable (username, password, credit) VALUES (?, ?, ?)', (username, password, 5))
        conn.commit()
        result = True
    except:
        result = False # Kullanıcı adı zaten varsa hata verir
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
    # Krediyi 1 azalt
    c.execute('UPDATE usersTable SET credit = credit - 1 WHERE username =?', (username,))
    conn.commit()
    conn.close()

# Veritabanını başlat
init_db()

# --- CSS VE TASARIM ---
st.markdown("""
<style>
    /* Buton Tasarımları */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 50px;
        font-weight: bold;
    }
    /* Giriş kutusu ortalama */
    .login-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ==========================================
# 1. BÖLÜM: GİRİŞ VE KAYIT EKRANI (TURNİKE)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔒 ÖdevMatik Giriş</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with tab1:
        st.info("Hesabın varsa giriş yap.")
        login_user_name = st.text_input("Kullanıcı Adı (Email):", key="login_user")
        login_password = st.text_input("Şifre:", type='password', key="login_pass")
        
        if st.button("Giriş Yap"):
            if login_user(login_user_name, login_password):
                st.session_state.logged_in = True
                st.session_state.username = login_user_name
                st.success(f"Hoşgeldin {login_user_name}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

    with tab2:
        st.info("Yeni hesap oluştur. **5 Soru Hakkı Hediye!** 🎁")
        new_user = st.text_input("Kullanıcı Adı Belirle:", key="new_user")
        new_password = st.text_input("Şifre Belirle:", type='password', key="new_pass")
        
        if st.button("Kayıt Ol"):
            if add_user(new_user, new_password):
                st.success("Kayıt Başarılı! Şimdi 'Giriş Yap' sekmesinden girebilirsin.")
            else:
                st.error("Bu kullanıcı adı zaten alınmış.")

    st.stop() # Giriş yapmadan aşağıya (uygulamaya) geçit yok!

# ==========================================
# 2. BÖLÜM: UYGULAMANIN KENDİSİ (İÇERİSİ)
# ==========================================

# Kalan Krediyi Çek
current_credit = get_credit(st.session_state.username)

# --- YAN MENÜ (PROFİL) ---
with st.sidebar:
    st.title(f"👤 {st.session_state.username}")
    st.metric("Kalan Hakkın", f"{current_credit} Soru")
    
    if current_credit == 0:
        st.error("Hakkın bitti!")
        st.button("💎 Premium Al (Sınırsız)") # Şimdilik göstermelik
    
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()
        
    st.divider()
    
    # API KEY KONTROLÜ
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("Admin Şifresi:", type="password")
        if not api_key: st.stop()

client = OpenAI(api_key=api_key)

# --- ANA EKRAN ---
st.markdown("<h1>📝 ÖdevMatik</h1>", unsafe_allow_html=True)

# KREDİ KONTROLÜ (EN ÖNEMLİ KISIM)
if current_credit <= 0:
    st.error("😔 Üzgünüm, bugünkü soru sorma hakkın bitti!")
    st.info("Daha fazla soru sormak için yarını bekleyebilir veya Premium üye olabilirsin.")
    st.stop() # Uygulamayı durdur, soru sordurma!

# --- MENÜ VE İŞLEMLER (ESKİ KODUN AYNISI) ---
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
        st.image(gorsel_veri, use_container_width=True)
        st.write("")
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True): form_tetiklendi = True

elif st.session_state.aktif_mod == "Kamera":
    st.info("📸 **Fotoğraf Çek**")
    cekilen_foto = st.camera_input("Kamerayı aç")
    if cekilen_foto:
        gorsel_veri = cekilen_foto.getvalue()
        st.write("")
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True): form_tetiklendi = True

elif st.session_state.aktif_mod == "Yaz":
    st.info("⌨️ **Soruyu Elle Yaz**")
    with st.form(key='soru_formu'):
        metin_sorusu = st.text_area("", height=150, placeholder="Sorunu buraya yaz...")
        st.write("")
        gonder_butonu = st.form_submit_button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True)
        if gonder_butonu and metin_sorusu: form_tetiklendi = True

# --- ÇÖZÜM MOTORU ---
if form_tetiklendi:
    # ÖNCE KREDİYİ DÜŞ (KURNZLIK OLMASIN)
    deduct_credit(st.session_state.username)
    st.toast("Kredinizden 1 hak düştü!", icon="ticket") # Bildirim göster
    
    loading_messages = ["Hoca bakıyor...", "İşlemler yapılıyor...", "Çözülüyor..."]
    with st.spinner(random.choice(loading_messages)):
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
st.caption("⚠️ Sonuçlar yapay zeka tarafından üretilmiştir.")
