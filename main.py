import streamlit as st
from openai import OpenAI
import base64

# --- AYARLAR ---
st.set_page_config(page_title="Ödev Matik", page_icon="📝")

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI Şifreni (Key) Yapıştır:", type="password")
    
    if not api_key:
        st.warning("⚠️ Şifre girmeden çalışmaz.")
        st.stop()

client = OpenAI(api_key=api_key)

st.title("📝 Ödev Matik")
st.write("Fotoğraf yükle veya sorunu yaz, çözüm deftere gelsin!")

# --- GİRİŞ YÖNTEMİ SEÇİMİ ---
# O parantez içindeki yazıyı sildim, tertemiz oldu.
secim = st.radio("Soruyu nasıl soracaksın?", ["📁 Galeriden Seç", "📸 Kamerayı Aç", "⌨️ Elle Yaz"], horizontal=True)

gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

# --- 1. YÖNTEM: GALERİ ---
if secim == "📁 Galeriden Seç":
    st.info("👇 Aşağıdaki kutuya tıkla")
    yuklenen_dosya = st.file_uploader("Dosya Seç", accept_multiple_files=False)
    if yuklenen_dosya:
        gorsel_veri = yuklenen_dosya.getvalue()
        if st.button("Çöz ve Yazdır ✍️"):
            form_tetiklendi = True

# --- 2. YÖNTEM: KAMERA ---
elif secim == "📸 Kamerayı Aç":
    cekilen_foto = st.camera_input("Fotoğraf Çek")
    if cekilen_foto:
        gorsel_veri = cekilen_foto.getvalue()
        if st.button("Çöz ve Yazdır ✍️"):
            form_tetiklendi = True

# --- 3. YÖNTEM: MANUEL METİN (FORM YAPISI) ---
elif secim == "⌨️ Elle Yaz":
    # Form kullanarak kutuyu ve butonu birleştiriyoruz.
    with st.form(key='soru_formu'):
        metin_sorusu = st.text_area(
            "Sorunu buraya detaylıca yaz:", 
            height=180, # Geniş ve ferah kutu
            placeholder="Matematik veya Sözel sorunu buraya yazabilirsin..."
        )
        # Buton formun içinde, sağ altta şık durur
        gonder_butonu = st.form_submit_button("Çöz ve Yazdır ✍️", type="primary")
        
        if gonder_butonu and metin_sorusu:
            form_tetiklendi = True

# --- ORTAK ÇÖZÜM MOTORU ---
if form_tetiklendi:
    with st.spinner("Hoca çözüyor..."):
        try:
            ana_prompt = """
            GÖREV: Soruyu öğrenci gibi çöz.
            1. Cevabı çok kısa tutma ama destan da yazma. Adım adım git.
            2. LaTeX formatı ($$) KULLANMA. Düz metin kullan. (Örn: x^2 yerine x kare yaz).
            3. Okunaklı ve samimi bir dil kullan.
            4. Cevabı en sonda net belirt.
            """

            # EĞER FOTOĞRAF VARSA
            if gorsel_veri:
                base64_image = base64.b64encode(gorsel_veri).decode('utf-8')
                messages = [
                    {"role": "system", "content": ana_prompt},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}
                ]
            
            # EĞER SADECE METİN VARSA
            elif metin_sorusu:
                messages = [
                    {"role": "system", "content": ana_prompt},
                    {"role": "user", "content": f"Soru: {metin_sorusu}"}
                ]

            # AI ÇAĞRISI
            response = client.chat.completions.create(
                model="gpt-4o", 
                messages=messages,
                max_tokens=1000
            )
            
            cevap = response.choices[0].message.content
            
            # --- KAĞIT GÖRÜNÜMÜ ---
            st.markdown(f"""<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet"><div style="background-color:#fff9c4;background-image:linear-gradient(#999 1px, transparent 1px);background-size:100% 1.8em;border:1px solid #ccc;border-radius:8px;padding:25px;padding-top:5px;font-family:'Patrick Hand','Comic Sans MS',cursive;font-size:22px;color:#000080;line-height:1.8em;box-shadow:5px 5px 15px rgba(0,0,0,0.1);white-space:pre-wrap;">{cevap}</div>""", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Hata: {e}")
