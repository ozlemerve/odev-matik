import streamlit as st
from openai import OpenAI
import base64
import random

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- MODERN CSS (MÜKEMMEL DENGELİ BUTONLAR) ---
st.markdown("""
<style>
    /* Tüm butonları hedefle */
    div.stButton > button {
        width: 100%; /* Kutuyu tam doldur */
        height: 70px; /* Biraz daha yüksek ve heybetli */
        border-radius: 16px; /* Daha yuvarlak köşeler */
        border: 2px solid #e0e0e0;
        background-color: #ffffff;
        color: #31333F;
        font-weight: 800; /* Daha kalın yazı */
        font-size: 22px !important; /* İKONLARIN HEPSİ BÜYÜK VE EŞİT OLACAK */
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); /* Hafif modern gölge */
    }
    /* Üzerine gelince veya tıklayınca */
    div.stButton > button:hover, div.stButton > button:active {
        border-color: #4CAF50;
        color: #4CAF50;
        background-color: #f1f8e9;
        transform: scale(1.02); /* Hafif büyüme efekti */
    }
    /* Başlık ve alt yazı ortalama */
    h1 { text-align: center; color: #1E1E1E; margin-bottom: 0px; }
    p { text-align: center; color: #666; margin-top: 5px; }
    /* Sütunlar arası boşluğu biraz daraltmak için */
    [data-testid="column"] {
        padding: 0 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- YÜKLENİYOR MESAJLARI ---
loading_messages = [
    "Hoca kitapları karıştırıyor... 📚",
    "Formüller hesaplanıyor... 🧮",
    "Beyin fırtınası yapılıyor... 🧠",
    "Çözüm yolda, az sabır... 🚀"
]

# --- SESSION STATE ---
if "aktif_mod" not in st.session_state:
    st.session_state.aktif_mod = "Galeri"

# --- YAN MENÜ ---
with st.sidebar:
    st.title("📝 Menü")
    with st.expander("ℹ️ Nasıl Kullanılır?"):
        st.write("1. Yöntem seç.\n2. Soruyu yükle/yaz.\n3. Çözümü al.")
    
    st.divider()
    
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("Şifre:", type="password")
        if not api_key: st.stop()

client = OpenAI(api_key=api_key)

# --- ANA BAŞLIK ---
st.markdown("<h1>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
st.markdown("<p>Ödev asistanın cebinde!</p>", unsafe_allow_html=True)
st.write("") # Biraz boşluk

# --- MODERN MENÜ (3 EŞİT ve BÜYÜK BUTON) ---
col1, col2, col3 = st.columns(3)

# use_container_width=True sayesinde hepsi eşitlenir!
with col1:
    if st.button("📁 Galeri", use_container_width=True):
        st.session_state.aktif_mod = "Galeri"

with col2:
    if st.button("📸 Kamera", use_container_width=True):
        st.session_state.aktif_mod = "Kamera"

with col3:
    if st.button("⌨️ Yaz", use_container_width=True):
        st.session_state.aktif_mod = "Yaz"

st.divider()

# --- İÇERİK GÖSTERİMİ ---
gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

# 1. MOD: GALERİ
if st.session_state.aktif_mod == "Galeri":
    st.info("📂 **Galeriden Fotoğraf Seç**")
    yuklenen_dosya = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if yuklenen_dosya:
        gorsel_veri = yuklenen_dosya.getvalue()
        st.image(gorsel_veri, use_container_width=True)
        st.write("")
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True):
            form_tetiklendi = True

# 2. MOD: KAMERA
elif st.session_state.aktif_mod == "Kamera":
    st.info("📸 **Fotoğraf Çek**")
    cekilen_foto = st.camera_input("Kamerayı aç")
    if cekilen_foto:
        gorsel_veri = cekilen_foto.getvalue()
        st.write("")
