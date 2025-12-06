import streamlit as st
from openai import OpenAI
import base64
import random
import urllib.parse

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- MODERN CSS ---
st.markdown("""
<style>
    /* Standart Streamlit Butonları */
    div.stButton > button {
        width: 100%;
        height: 60px;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        background-color: white;
        color: #31333F;
        font-weight: 800;
        font-size: 20px !important;
        transition: all 0.2s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div.stButton > button:hover {
        border-color: #4CAF50;
        color: #4CAF50;
        transform: translateY(-2px);
    }
    
    /* HTML Butonumuzun Stili (Yazdır Butonu İçin) */
    .custom-print-btn {
        width: 100%;
        height: 60px;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        background-color: white;
        color: #31333F;
        font-weight: 800;
        font-size: 20px;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .custom-print-btn:hover {
        border-color: #FF5722 !important; /* Turuncu vurgu */
        color: #FF5722 !important;
        transform: translateY(-2px);
    }

    /* Link Butonları (WhatsApp/Mail) */
    a[href*="whatsapp"] button { color: #25D366 !important; border-color: #25D366 !important; }
    a[href^="mailto"] button { color: #0078D4 !important; border-color: #0078D4 !important; }
    
    h1 { text-align: center; color: #1E1E1E; margin-bottom: 0px; }
    p { text-align: center; color: #666; margin-top: 5px; }
    [data-testid="column"] { padding: 0 0.3rem !important; }
</style>
""", unsafe_allow_html=True)

loading_messages = [
    "Hoca kitapları karıştırıyor... 📚",
    "Formüller hesaplanıyor... 🧮",
    "Beyin fırtınası yapılıyor... 🧠",
    "Çözüm yolda, az sabır... 🚀"
]

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

# --- ANA EKRAN ---
st.markdown("<h1>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
st.markdown("<p>Ödev asistanın cebinde!</p>", unsafe_allow_html=True)
st.write("")

# --- MENÜ BUTONLARI ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📁 Galeri", use_container_width=True): st.session_state.aktif_mod = "Galeri"
with col2:
    if st.button("📸 Kamera", use_container_width=True): st.session_state.aktif_mod = "Kamera"
with col3:
    if st.button("⌨️ Yaz", use_container_width=True): st.session_state.aktif_mod = "Yaz"

st.divider()

gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

# --- MODLAR ---
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

# --- ÇÖZÜM VE AKSİYONLAR ---
if form_tetiklendi:
    with st.spinner(random.choice(loading_messages)):
        try:
            ana_prompt = """GÖREV: Soruyu öğrenci gibi çöz. Adım adım git. LaTeX kullanma. Samimi ol. Sonucu net belirt."""

            # HİBRİT MODEL SEÇİMİ
            if gorsel_veri:
                secilen_model = "gpt-4o"
                base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
            elif metin_sorusu:
                secilen_model = "gpt-4o-mini"
                messages = [{"role": "system", "content": ana_prompt}, {"role": "user", "content": f"Soru: {metin_sorusu}"}]

            response = client.chat.completions.create(model=secilen_model, messages=messages, max_tokens=1000)
            cevap = response.choices[0].message.content
            
            # KAĞIT GÖRÜNÜMÜ
            st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="margin-top: 20px; background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{cevap}</div>""", unsafe_allow_html=True)

            # --- PAYLAŞIM ALANI ---
            st.write("")
            st.markdown("### 📤 Paylaş ve Kaydet")
            
            paylasim_metni = urllib.parse.quote(f"ÖdevMatik Çözümü:\n\n{cevap}\n\n--- ÖdevMatik ile çözüldü.")
            whatsapp_link = f"https://api.whatsapp.com/send?text={paylasim_metni}"
            mail_link = f"mailto:?subject=ÖdevMatik Çözümü&body={paylasim_metni}"

            p_col1, p_col2, p_col3 = st.columns(3)
            
            with p_col1:
                st.link_button("💬 WhatsApp", whatsapp_link, use_container_width=True)
            
            with p_col2:
                st.link_button("📧 Mail At", mail_link, use_container_width=True)
            
            with p_col3:
                # DÜZELTME: Streamlit butonu yerine SAF HTML BUTONU kullanıyoruz.
                # Bu buton sayfayı yenilemez, direkt JS çalıştırır.
                st.markdown(f"""
                <button onclick="window.print()" class="custom-print-btn">
                    🖨️ Yazdır/PDF
                </button>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Hata: {e}")

st.divider()
st.caption("⚠️ Sonuçlar yapay zeka tarafından üretilmiştir.")
