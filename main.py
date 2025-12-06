import streamlit as st
from openai import OpenAI
import base64
import random

# --- AYARLAR VE SAYFA YAPISI ---
st.set_page_config(
    page_title="ÖdevMatik",  # Bitişik başlık
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- YÜKLENİYOR MESAJLARI (Dinamik ve Eğlenceli) ---
loading_messages = [
    "Hoca kitapları karıştırıyor... 📚",
    "Formüller hesaplanıyor... 🧮",
    "Beyin fırtınası yapılıyor... 🧠",
    "Tebeşir tozu yutuluyor... 💨",
    "Çözüm yolda, az sabır... 🚀"
]

# --- YAN MENÜ (Sidebar) ---
with st.sidebar:
    st.title("📝 Menü")
    
    # GENİŞLETİLEBİLİR HAKKINDA KUTUSU (Yeni İstek)
    with st.expander("ℹ️ Nasıl Kullanılır? (Tıkla Oku)"):
        st.write("""
        **Adım 1:** Soruyu nasıl soracağını seç (Galeri, Kamera veya Yazı).
        
        **Adım 2:** Fotoğrafı yükle veya sorunu detaylıca yaz.
        
        **Adım 3:** Mavi butona tıkla ve arkanı yaslan. Yapay zeka çözümü senin için hazırlayacak.
        
        ---
        *İpucu: Yazı ile sorduğun sorular daha hızlı ve ekonomik çözülür!*
        """)
    
    st.divider() # Çizgi
    
    st.header("⚙️ Ayarlar")
    # Şifre kontrolü (Secrets'tan)
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success("✅ Sistem Hazır")
    else:
        api_key = st.text_input("OpenAI Şifreni (Key) Yapıştır:", type="password")
        if not api_key:
            st.warning("⚠️ Şifre girmeden çalışmaz.")
            st.stop()

client = OpenAI(api_key=api_key)

# --- ANA SAYFA BAŞLIĞI ---
st.markdown("<h1 style='text-align: center;'>📝 ÖdevMatik</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>Fotoğraf yükle veya sorunu yaz, çözüm deftere gelsin!</p>", unsafe_allow_html=True)
st.divider()

# --- GİRİŞ YÖNTEMİ SEÇİMİ ---
secim = st.radio("👇 Soruyu nasıl soracaksın?", ["📁 Galeriden Seç", "📸 Kamerayı Aç", "⌨️ Elle Yaz"], horizontal=True)

gorsel_veri = None
metin_sorusu = None
form_tetiklendi = False

# --- 1. GALERİ ---
if secim == "📁 Galeriden Seç":
    st.info("Aşağıdaki alana tıkla ve fotoğrafı seç")
    yuklenen_dosya = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if yuklenen_dosya:
        gorsel_veri = yuklenen_dosya.getvalue()
        st.image(gorsel_veri, caption="Seçilen Fotoğraf", use_column_width=True)
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True):
            form_tetiklendi = True

# --- 2. KAMERA ---
elif secim == "📸 Kamerayı Aç":
    cekilen_foto = st.camera_input("Kamerayı aç ve çek")
    if cekilen_foto:
        gorsel_veri = cekilen_foto.getvalue()
        if st.button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True):
            form_tetiklendi = True

# --- 3. METİN (FORM) ---
elif secim == "⌨️ Elle Yaz":
    with st.form(key='soru_formu'):
        metin_sorusu = st.text_area(
            "Sorunu buraya detaylıca yaz:", 
            height=150, 
            placeholder="Matematik veya Sözel sorunu buraya yazabilirsin..."
        )
        gonder_butonu = st.form_submit_button("Çöz ve Yazdır ✍️", type="primary", use_container_width=True)
        if gonder_butonu and metin_sorusu:
            form_tetiklendi = True

# --- ORTAK ÇÖZÜM MOTORU ---
if form_tetiklendi:
    # Rastgele bir yükleniyor mesajı seç
    spinner_mesaji = random.choice(loading_messages)
    
    with st.spinner(spinner_mesaji): # Dinamik mesaj burada çıkacak
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

# --- ALT BİLGİ ve UYARI NOTU (Yeni İstek) ---
st.divider()
st.caption("⚠️ Yasal Uyarı: Bu bir yapay zeka asistanıdır ve nadiren de olsa hatalı sonuçlar üretebilir. Önemli ödevlerinizde sonuçları kontrol etmeniz önerilir.")
st.caption("© 2024 ÖdevMatik - Made with ❤️")
