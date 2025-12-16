import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
import pandas as pd
import pytesseract
from pypdf import PdfWriter, PdfReader

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="DocMorph X",
    page_icon="📄",
    layout="wide"
)

# --------------------------------------------------
# FIX SIDEBAR TEXT VISIBILITY
# --------------------------------------------------
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background-color: #0f1117 !important;
}
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}
html, body {
    background-color: #ffffff;
    color: #000000;
    font-family: 'Segoe UI', sans-serif;
}
.card {
    background: white;
    border-radius: 10px;
    padding: 24px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "count" not in st.session_state:
    st.session_state.count = 0

# --------------------------------------------------
# FORCE TESSERACT PATH (Windows)
# --------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\pc\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("📄 DocMorph X")
tool = st.sidebar.radio(
    "Choose Tool",
    ["JPG → PDF", "JPG → Clean Sheet", "JPG → Excel"]
)
orientation = st.sidebar.radio("Page Orientation", ["Portrait", "Landscape"])
password = st.sidebar.text_input("PDF Password (optional)", type="password")
st.sidebar.metric("Total Conversions", st.session_state.count)

# --------------------------------------------------
# IMAGE PROCESSING UTILITIES
# --------------------------------------------------
def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    return blur

def clean_sheet(pil_img):
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    thresh = cv2.adaptiveThreshold(
        img, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    return Image.fromarray(thresh)

def image_to_pdf(images, password=None):
    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    if password:
        reader = PdfReader(io.BytesIO(buffer.getvalue()))
        writer = PdfWriter()
        for p in reader.pages:
            writer.add_page(p)
        writer.encrypt(password)
        secured = io.BytesIO()
        writer.write(secured)
        return secured
    return buffer

# --------------------------------------------------
# STRUCTURED TABLE OCR FOR JPG → EXCEL
# --------------------------------------------------
def image_to_excel_structured(pil_img):
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

    # Horizontal lines
    horizontal = thresh.copy()
    cols = horizontal.shape[1] // 30
    horizontal_size = cols
    horizontal_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
    horizontal = cv2.erode(horizontal, horizontal_structure)
    horizontal = cv2.dilate(horizontal, horizontal_structure)

    # Vertical lines
    vertical = thresh.copy()
    rows = vertical.shape[0] // 30
    vertical_size = rows
    vertical_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
    vertical = cv2.erode(vertical, vertical_structure)
    vertical = cv2.dilate(vertical, vertical_structure)

    # Combine lines to get table grid
    mask = horizontal + vertical
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))  # top->bottom, left->right

    rows_list = []
    current_y = -1
    row_cells = []

    for x, y, w, h in boxes:
        if current_y == -1:
            current_y = y
        if y > current_y + 10:
            if row_cells:
                rows_list.append(row_cells)
            row_cells = []
            current_y = y
        cell_img = img[y:y+h, x:x+w]
        cell_pil = Image.fromarray(cv2.cvtColor(cell_img, cv2.COLOR_BGR2RGB))
        text = pytesseract.image_to_string(cell_pil, config='--psm 6').strip()
        row_cells.append(text)
    if row_cells:
        rows_list.append(row_cells)

    if not rows_list:
        return pd.DataFrame()
    max_cols = max(len(r) for r in rows_list)
    df = pd.DataFrame([r + ['']*(max_cols-len(r)) for r in rows_list])
    return df

def multi_image_to_excel_structured(images):
    all_tables = []
    for img in images:
        df = image_to_excel_structured(img)
        if not df.empty:
            all_tables.append(df)
    if not all_tables:
        return pd.DataFrame()
    return pd.concat(all_tables, ignore_index=True)

# --------------------------------------------------
# MAIN UI
# --------------------------------------------------
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.title("📄 DocMorph X")
st.caption("Intelligent Document Conversion & Data Extraction Studio")

uploaded = st.file_uploader(
    "Upload JPG / JPEG Images",
    type=["jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded:
    images = []
    for file in uploaded:
        img = Image.open(file).convert("RGB")
        if orientation == "Landscape":
            img = img.rotate(90, expand=True)
        images.append(img)

    # ---------------- JPG → PDF ----------------
    if tool == "JPG → PDF":
        st.subheader("PDF Preview")
        for img in images:
            st.image(img, width=250)
        if st.button("Generate PDF"):
            pdf = image_to_pdf(images, password)
            st.session_state.count += 1
            st.download_button(
                "Download PDF",
                pdf.getvalue(),
                "DocMorphX_Output.pdf",
                "application/pdf"
            )

    # ---------------- JPG → CLEAN SHEET ----------------
    elif tool == "JPG → Clean Sheet":
        st.subheader("Clean Sheet Preview")
        cleaned = [clean_sheet(img) for img in images]
        for img in cleaned:
            st.image(img, width=250)
        if st.button("Export as PDF"):
            pdf = image_to_pdf(cleaned, password)
            st.session_state.count += 1
            st.download_button(
                "Download Clean PDF",
                pdf.getvalue(),
                "DocMorphX_CleanSheet.pdf",
                "application/pdf"
            )

    # ---------------- JPG → EXCEL ----------------
    elif tool == "JPG → Excel":
        st.subheader("Extracted Table Preview")
        df = multi_image_to_excel_structured(images)
        if df.empty:
            st.warning("No tables detected in the uploaded images.")
        else:
            st.dataframe(df)
            if st.button("Download Excel"):
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                st.session_state.count += 1
                st.download_button(
                    "Download Excel",
                    buffer.getvalue(),
                    "DocMorphX_Data.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("""
<br>
<p style="text-align:center; opacity:0.6;">
DocMorph X • Intelligent Document Conversion Platform
</p>
""", unsafe_allow_html=True)
