import streamlit as st
from PIL import Image
import io
from streamlit_sortables import sort_items
from pypdf import PdfReader, PdfWriter

# ---------------- CONFIG ---------------- #
st.set_page_config(
    page_title="DocMorph | Image to PDF Studio",
    page_icon="🧊",
    layout="centered"
)

# ---------------- SESSION STATE ---------------- #
if "conversions" not in st.session_state:
    st.session_state.conversions = 0

# ---------------- SIDEBAR ---------------- #
st.sidebar.title("🧊 DocMorph Settings")

theme = st.sidebar.toggle("🌙 Dark Mode", value=True)
orientation = st.sidebar.radio("📄 Orientation", ["Portrait", "Landscape"])
margin = st.sidebar.slider("📐 Page Margin (px)", 0, 50, 10)
pdf_password = st.sidebar.text_input("🔐 PDF Password (optional)", type="password")
show_preview = st.sidebar.checkbox("🖼️ Show Preview", value=True)

st.sidebar.markdown("---")
st.sidebar.metric("📊 Total Conversions", st.session_state.conversions)

# ---------------- THEME CSS ---------------- #
bg = (
    "linear-gradient(135deg, #0f2027, #203a43, #2c5364)"
    if theme else
    "linear-gradient(135deg, #f5f7fa, #c3cfe2)"
)
text_color = "#ffffff" if theme else "#000000"

st.markdown(f"""
<style>
html, body {{
    background: {bg};
    color: {text_color};
    font-family: 'Segoe UI', sans-serif;
}}
.glass {{
    background: rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 25px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}}
.stButton>button {{
    background: linear-gradient(135deg, #00c6ff, #0072ff);
    color: white;
    border-radius: 10px;
    font-weight: 600;
    padding: 10px 25px;
}}
.stDownloadButton>button {{
    background: linear-gradient(135deg, #1db954, #1ed760);
    color: black;
    border-radius: 10px;
    font-weight: bold;
}}
section[data-testid="stSidebar"] {{
    background: rgba(0,0,0,0.6);
}}
</style>
""", unsafe_allow_html=True)

# ---------------- MAIN UI ---------------- #
st.markdown("<div class='glass'>", unsafe_allow_html=True)

st.title("🧊 DocMorph")
st.caption("Smart Image → PDF Studio | Premium • Secure • Cloud-Ready")

uploaded_files = st.file_uploader(
    "📤 Upload JPG Images",
    type=["jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    filenames = [file.name for file in uploaded_files]

    st.subheader("🖱️ Drag to Reorder Images")
    ordered_names = sort_items(filenames, direction="vertical")

    ordered_files = [
        next(file for file in uploaded_files if file.name == name)
        for name in ordered_names
    ]

    images = []

    if show_preview:
        st.subheader("🖼️ Preview")
        cols = st.columns(3)

    for i, file in enumerate(ordered_files):
        img = Image.open(file).convert("RGB")

        if orientation == "Landscape":
            img = img.rotate(90, expand=True)

        images.append(img)

        if show_preview:
            cols[i % 3].image(img, use_container_width=True)

    if st.button("🚀 Convert to PDF"):
        base_pdf = io.BytesIO()
        images[0].save(
            base_pdf,
            format="PDF",
            save_all=True,
            append_images=images[1:]
        )

        final_pdf = base_pdf

        if pdf_password:
            reader = PdfReader(io.BytesIO(base_pdf.getvalue()))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(pdf_password)

            secured_pdf = io.BytesIO()
            writer.write(secured_pdf)
            final_pdf = secured_pdf

        st.session_state.conversions += 1
        st.success("✅ PDF Generated Successfully!")

        st.download_button(
            label="⬇️ Download PDF",
            data=final_pdf.getvalue(),
            file_name="DocMorph_Output.pdf",
            mime="application/pdf"
        )

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- FOOTER ---------------- #
st.markdown("""
<br>
<p style="text-align:center; opacity:0.6;">
🧊 DocMorph • Built with Streamlit • Portfolio Project
</p>
""", unsafe_allow_html=True)
