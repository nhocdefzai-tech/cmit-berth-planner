import streamlit as st
import pandas as pd
import datetime
import warnings
import json
from fpdf import FPDF  # Đã thêm thư viện này

# 1. Cấu hình
warnings.filterwarnings("ignore")
st.set_page_config(layout="wide", page_title="CMIT Berthing & Productivity Master Control")

st.title("🚢 CMIT - BERTH PLANNER & PERFORMANCE DASHBOARD")

# --- HÀM TẠO PDF ---
def create_pdf(barge_data):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BAO CAO SO DO CAU BEN CMIT", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    for item in barge_data:
        info_str = f"- {item['name']}: {item['length']}m | {item['bays']} Bays | Luồng: {item['position_type'].upper()}"
        pdf.cell(0, 10, info_str, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIC DỮ LIỆU & GIAO DIỆN (Giữ nguyên phần xử lý của bạn) ---
if "custom_barges" not in st.session_state:
    st.session_state.custom_barges = {}

# (Phần xử lý Excel và SideBar của bạn giữ nguyên ở đây...)
# ... [Để nguyên đoạn code xử lý file N4 và SideBar của bạn] ...

# --- CẤU TRÚC TAB CHÍNH ---
tab_main, tab_config = st.tabs(["🗺️ BERTH PLANNER & DASHBOARD", "⚙️ CONFIG BARGE SPEC"])

with tab_config:
    # ... [Để nguyên đoạn code Config Barge của bạn] ...
    pass 

with tab_main:
    # ... [Để nguyên đoạn Code xử lý JS/HTML và hiển thị danh sách của bạn] ...
    
    # Đảm bảo biến js_barges_list đã được tạo xong tại đây
    js_barges_list = [] # (Đảm bảo logic tạo list này nằm trong tab_main)
    
    # Nút In PDF tích hợp ở cuối tab_main
    st.markdown("---")
    if st.button("🖨️ Xuất sơ đồ ra PDF"):
        if 'js_barges_list' in locals() and js_barges_list:
            pdf_bytes = create_pdf(js_barges_list)
            st.download_button(
                label="📥 Tải file PDF báo cáo",
                data=pdf_bytes,
                file_name="CMIT_Berth_Report.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Vui lòng chọn sà lan trước khi xuất PDF.")

# --- CUỐI FILE ---
st.components.v1.html("<script>setTimeout(function(){ window.location.reload(); }, 30000);</script>", height=0)