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

# --- MODERN CSS (BUTONLARI GÜZELLEŞTİRME) ---
# Bu kod, butonları büyütür, kenarlarını yuvarlar ve mobil uygulama hissi verir.
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        height: 60px;
        border-radius: 12px;
        border: 2px solid #f0f2f6;
        background-color: white;
        color: #31333F;
        font-weight: bold;
        font-size: 18px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover {
        border-color: #4CAF50;
        color: #4CAF50;
        transform: translateY(-2px);
    }
    div.stButton > button:focus {
        border-color: #4CAF50;
        background-color: #e8f5e9;
        color: #4CAF50;
    }
    h1 { text-align: center; color: #1E1E1E; }
    p { text-align: center; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- YÜKLENİYOR MESAJLARI ---
loading_messages = [
    "Hoca kitapları karıştırıyor... 📚",
    "Formüller hesaplanıyor... 🧮",
    "Beyin fırtınası yapılıyor... 🧠",
    "Çözüm yolda, az sabır... 🚀"
]

# --- SESSION STATE (SEÇİMİ HAFIZADA TUTMAK İÇİN) ---
if "aktif_mod" not in st.session_state:
    st.session_state.aktif_mod = "Galeri" # Varsayılan mod

# --- YAN MENÜ ---
with st.sidebar:
    st.title("📝 Menü")
    with st.expander("ℹ️ Nasıl Kullanılır?"):
        st.write("Fotoğrafı yükle veya sorunu yaz, yapay zeka senin için deftere çözsün.")
    
    st.divider()
    
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success("✅ Sistem Hazır")
    else:
        api_key = st.text_input("OpenAI Şifreni (Key) Yapıştır:", type="password")
        if not api_key:
            st.warning("⚠️ Şifre girmeden çalışmaz.")
            st.stop()

client = OpenAI(api_key=api_key)

# --- ANA BAŞLIK ---
st.markdown("<h1>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
st.markdown("<p>Ödev asistanın cebinde!</p>", unsafe_allow_html=True)
st.divider()

# --- MODERN MENÜ (YAN YANA 3 BÜYÜK BUTON) ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📁 Galeri"):
        st.session_state.aktif_mod = "Galeri"

with col2:
    if st.button("📸 Kamera"):
        st.session_state.aktif_mod = "Kamera"

with col3:
    if st.button("⌨️ Yaz"):
        st.session_state.aktif_mod = "Yaz"

# --- SEÇİME GÖRE İÇERİK GÖSTERME ---
gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

# 1. MOD: GALERİ
if st.session_state.aktif_mod == "Galeri":
    st.info("📂 **Galeriden Fotoğraf Seç**")
    yuklenen_dosya = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if yuklenen_dosya:
        gorsel_veri = yuklenen_dosya.getvalue()
        st.image(gorsel_veri, caption="Seçilen Fotoğraf", use_container_width=True)
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True):
            form_tetiklendi = True

# 2. MOD: KAMERA
elif st.session_state.aktif_mod == "Kamera":
    st.info("📸 **Fotoğraf Çek**")
    cekilen_foto = st.camera_input("Kamerayı aç")
    if cekilen_foto:
        gorsel_veri = cekilen_foto.getvalue()
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True):
            form_tetiklendi = True

# 3. MOD: YAZI
elif st.session_state.aktif_mod == "Yaz":
    st.info("⌨️ **Soruyu Elle Yaz**")
    with st.form(key='soru_formu'):
        metin_sorusu = st.text_area("Sorunu buraya yaz:", height=150, placeholder="Matematik, Tarih, Türkçe...")
        gonder_butonu = st.form_submit_button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True)
        if gonder_butonu and metin_sorusu:
            form_tetiklendi = True

# --- ÇÖZÜM MOTORU (HİBRİT) ---
if form_tetiklendi:
    spinner_mesaji = random.choice(loading_messages)
    
    with st.spinner(spinner_mesaji):
        try:
            ana_prompt = """
            GÖREV: Soruyu öğrenci gibi çöz.
            1. Cevabı çok kısa tutma ama destan da yazma. Adım adım git.
            2. LaTeX formatı ($$) KULLANMA. Düz metin kullan.
            3. Okunaklı ve samimi bir dil kullan.
            4. Cevabı en sonda net belirt.
            """

            # --- AKILLI MODEL SEÇİMİ ---
            # Fotoğraf varsa: PAHALI MODEL (gpt-4o)
            if gorsel_veri:
                secilen_model = "gpt-4o"
                base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                messages = [
                    {"role": "system", "content": ana_prompt},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}
                ]
            
            # Sadece yazı varsa: UCUZ MODEL (gpt-4o-mini)
            elif metin_sorusu:
                secilen_model = "gpt-4o-mini"
                messages = [
                    {"role": "system", "content": ana_prompt},
                    {"role": "user", "content": f"Soru: {metin_sorusu}"}
                ]

            # AI ÇAĞRISI
            response = client.chat.completions.create(
                model=secilen_model, 
                messages=messages,
                max_tokens=1000
            )
            
            cevap = response.choices[0].message.content
            
            # --- KAĞIT GÖRÜNÜMÜ ---
            st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{cevap}</div>""", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Hata: {e}")

# --- YASAL UYARI (SADE) ---
st.divider()
st.caption("⚠️ Sonuçlar yapay zeka tarafından üretilmiştir, lütfen kontrol ediniz.")
