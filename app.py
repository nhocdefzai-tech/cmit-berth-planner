import streamlit as st
import pandas as pd
import datetime
import warnings
import json
import streamlit.components.v1 as components
from fpdf import FPDF
import io

def create_pdf(barge_data):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BAO CAO SO DO CAU BEN CMIT", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    for item in barge_data:
        pdf.cell(0, 10, f"- {item['name']}: {item['length']}m | {item['bays']} Bays | {item['position_type']}", ln=True)
    
    # Trả về dữ liệu dưới dạng bytes để Streamlit tải về
    return pdf.output(dest='S').encode('latin-1')

# 1. CẤU HÌNH & KHỞI TẠO BIẾN
st.set_page_config(layout="wide", page_title="CMIT Berthing Master")
warnings.filterwarnings("ignore")

# Khởi tạo session_state để không bị mất dữ liệu khi tương tác
if "barge_summary" not in st.session_state: st.session_state.barge_summary = {}
if "truck_summary" not in st.session_state: st.session_state.truck_summary = {}
if "custom_barges" not in st.session_state: st.session_state.custom_barges = {}

# Gom dữ liệu để hiển thị
all_active_barges = {**st.session_state.barge_summary, **st.session_state.custom_barges}

st.title("🚢 CMIT - BERTH PLANNER & PERFORMANCE DASHBOARD")
st.write(f"🔄 *Cập nhật log: {datetime.datetime.now().strftime('%H:%M:%S')}")

# 2. XỬ LÝ FILE (Giữ nguyên logic của bạn)
st.sidebar.header("📂 TẢI DỮ LIỆU LÊN")
uploaded_file = st.sidebar.file_uploader("Chọn file Excel báo cáo:", type=["xlsx"])

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file, skiprows=4)
        df_raw.columns = df_raw.columns.str.strip()
        
        if all(col in df_raw.columns for col in ['Carrier Visit', 'Time_DT', 'TEU', 'Move Kind']):
            new_barge, new_truck = {}, {}
            
            for carrier, group in df_raw.groupby('Carrier Visit'):
                norm_name = str(carrier).strip().upper()
                if "GATE" in norm_name or pd.isna(carrier): continue
                
                # Logic cũ của bạn: tạo template
                data_template = {
                    "vessel_name": norm_name, 
                    "total_moves": len(group), 
                    "total_teus": int(group['TEU'].sum()),
                    "first_move": group['Time_DT'].min(), 
                    "last_move": group['Time_DT'].max(),
                    "length": 70, "bays": 4
                }
                
                if norm_name[0].isdigit():
                    new_truck[norm_name] = data_template
                else:
                    new_barge[norm_name] = data_template
            
            st.session_state.barge_summary = new_barge
            st.session_state.truck_summary = new_truck
            st.success("✅ Phân tích dữ liệu thành công!")
        else:
            st.error("❌ File thiếu cột bắt buộc.")
    except Exception as e:
        st.error(f"❌ Lỗi xử lý file: {e}")

# 3. GIAO DIỆN CẤU HÌNH (TAB CẤU HÌNH)
tab_main, tab_config = st.tabs(["🗺️ BERTH PLANNER & DASHBOARD", "⚙️ CONFIG BARGE SPEC"])
with tab_config:
    st.subheader("⚙️ CẤU HÌNH SÀ LAN")
    # Hiển thị danh sách để chỉnh sửa
    current_barge_keys = list(st.session_state.barge_summary.keys())
    for b_name in current_barge_keys:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1: st.markdown(f"🛳️ **{b_name}**")
        with col2: 
            st.session_state.barge_summary[b_name]['length'] = st.number_input(
                f"LOA - {b_name}", value=int(st.session_state.barge_summary[b_name].get('length', 70)), key=f"len_{b_name}"
            )
        with col3: 
            st.session_state.barge_summary[b_name]['bays'] = st.number_input(
                f"Bays - {b_name}", value=int(st.session_state.barge_summary[b_name].get('bays', 4)), key=f"bay_{b_name}"
            )

# 4. GIAO DIỆN CHÍNH (TAB MAIN)
with tab_main:
           
    # 1. Chọn sà lan
    col_sel_inner, col_sel_outer = st.columns(2)
    with col_sel_inner:
        selected_inner = st.multiselect("⚓ Sà lan đậu CẦU (Băng dưới):", options=list(all_active_barges.keys()))
    with col_sel_outer:
        selected_outer = st.multiselect("⛓️ Sà lan cập MẠN (Băng trên):", options=[n for n in all_active_barges.keys() if n not in selected_inner])
    
    # 2. Đóng gói dữ liệu JS
    js_barges_list = []
    for name in selected_inner:
        info = all_active_barges[name]
        js_barges_list.append({"name": name, "length": info.get('length', 70), "bays": info.get('bays', 4), "position_type": "inner"})
    for name in selected_outer:
        info = all_active_barges[name]
        js_barges_list.append({"name": name, "length": info.get('length', 70), "bays": info.get('bays', 4), "position_type": "outer"})

    js_barges_json = json.dumps(js_barges_list)

        # Nút in PDF
    if st.button("🖨️ Xuất Sơ đồ ra PDF"):
        # js_barges_list là danh sách sà lan đang được hiển thị
        if js_barges_list:
            pdf_bytes = create_pdf(js_barges_list)
            st.download_button(
                label="📥 Tải file PDF ngay",
                data=pdf_bytes,
                file_name="CMIT_Berth_Report.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("⚠️ Chưa có dữ liệu sà lan để xuất PDF!")

    # 3. NHÚNG HTML/JS (Logic sơ đồ của bạn)
    html_code = f"""
    <div id="berth-container" style="position: relative; width: 100%; height: 240px; background-color: #F8F9FA; border: 2px solid #2C3E50; border-radius: 8px; margin-bottom: 20px; overflow: hidden;">
        <div id="vessels-zone"></div>
    </div>

    <script>
        (function() {{
            const bargesData = {js_barges_json};
            const zone = document.getElementById("vessels-zone");
            let elements = [];

            bargesData.forEach((b, index) => {{
                const div = document.createElement("div");
                div.style.position = "absolute";
                div.style.top = (b.position_type === "outer" ? "15px" : "120px");
                div.style.left = (index * 120 + 30) + "px";
                div.style.width = (b.length * 1.5) + "px";
                div.style.height = "40px";
                div.style.backgroundColor = "#2980B9";
                div.style.color = "white";
                div.style.cursor = "ew-resize";
                div.style.textAlign = "center";
                div.style.fontSize = "11px";
                div.style.fontWeight = "bold";
                div.style.borderRadius = "5px";
                div.style.display = "flex";
                div.style.alignItems = "center";
                div.style.justifyContent = "center";
                div.innerHTML = `${{b.name}} (${{b.bays}}B)`;
                zone.appendChild(div);

                let item = {{ el: div, left: index * 120 + 30, width: b.length * 1.5, type: b.position_type }};
                elements.push(item);

                // Logic Kéo thả
                div.onmousedown = function(e) {{
                    let startX = e.clientX;
                    let initialLeft = item.left;
                    document.onmousemove = function(ev) {{
                        let delta = ev.clientX - startX;
                        item.left = initialLeft + delta;
                        div.style.left = item.left + "px";
                    }};
                    document.onmouseup = function() {{ document.onmousemove = null; }};
                }};
            }});
        }})();
    </script>
    """
    components.html(html_code, height=260)

# 5. KHU VỰC XE (Giữ nguyên logic bảng)
st.write("---")
st.subheader("🚛 KHU VỰC XE ĐẦU KÉO NGOÀI")

if st.session_state.truck_summary:
    # 1. Chuyển đổi dict thành DataFrame để hiển thị dạng bảng
    truck_data = []
    for t_name, t_info in st.session_state.truck_summary.items():
        truck_data.append({
            "Mã Xe/Carrier": t_name,
            "Số Lượt": t_info.get('total_moves', 0),
            "Tổng TEUs": t_info.get('total_teus', 0),
            "Thời điểm đầu": str(t_info.get('first_move', 'N/A')),
            "Thời điểm cuối": str(t_info.get('last_move', 'N/A'))
        })
    
    df_trucks = pd.DataFrame(truck_data)
    
    # Hiển thị bảng
    st.dataframe(df_trucks, use_container_width=True, hide_index=True)
    
    # 2. Tạo nút xuất file (CSV hoặc Excel)
    col_dl1, col_dl2 = st.columns(2)
    
    # Xuất CSV
    csv = df_trucks.to_csv(index=False).encode('utf-8')
    col_dl1.download_button(
        label="📥 Tải xuống CSV",
        data=csv,
        file_name="danh_sach_xe.csv",
        mime="text/csv"
    )
    
    # Xuất Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_trucks.to_excel(writer, index=False, sheet_name='Trucks')
    
    col_dl2.download_button(
        label="📥 Tải xuống Excel",
        data=buffer.getvalue(),
        file_name="danh_sach_xe.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👈 Hãy tải file báo cáo lên để hiển thị dữ liệu xe đầu kéo.")

