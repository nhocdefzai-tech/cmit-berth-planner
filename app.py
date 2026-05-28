import streamlit as st
import pandas as pd
import datetime
import warnings
import json
import streamlit.components.v1 as components
from fpdf import FPDF

# 1. CẤU HÌNH TRANG
warnings.filterwarnings("ignore")
st.set_page_config(layout="wide", page_title="CMIT Berthing Master")

if "custom_barges" not in st.session_state:
    st.session_state.custom_barges = {}

# Tiêu đề chính (chỉ để 1 lần duy nhất ở đây)
st.title("🚢 CMIT - BERTH PLANNER & PERFORMANCE DASHBOARD")
st.write(f"🔄 *Cập nhật log: {datetime.datetime.now().strftime('%H:%M:%S')}")

# =====================================================================
# 2. THANH SIDEBAR - QUẢN LÝ MÃ GIẢM TRỪ (DELAY 5X)
# =====================================================================
st.sidebar.header("🛠️ QUẢN LÝ MÃ GIẢM TRỪ (DELAY 5X)")
d51_mins = st.sidebar.number_input("⏱️ Code 51 (Hatch Cover):", min_value=0, value=30, step=5)
d52_mins = st.sidebar.number_input("⏱️ Code 52 (Scheduled Breaks):", min_value=0, value=45, step=5)
d53_mins = st.sidebar.number_input("⏱️ Code 53 (Technical / Repairs):", min_value=0, value=15, step=5)
d54_mins = st.sidebar.number_input("⏱️ Code 54 (Weather Delays):", min_value=0, value=0, step=5)
d55_mins = st.sidebar.number_input("⏱️ Code 55 (Power Failure):", min_value=0, value=0, step=5)

total_delay_mins = d51_mins + d52_mins + d53_mins + d54_mins + d55_mins

st.sidebar.markdown("### 📊 Tổng thời gian giảm trừ:")
st.sidebar.subheader(f"{total_delay_mins} phút")

# =====================================================================
# 3. ĐỌC VÀ XỬ LÝ DỮ LIỆU GỐC (TỐI ƯU HÓA)
# =====================================================================
# Bắt buộc khởi tạo biến trước khi đọc file
file_path = "MoveEvent_20260526_2203.xlsx" # Đảm bảo tên file chính xác
barge_summary = {}
truck_summary = {}
try:
    df_raw = pd.read_excel(file_path, skiprows=4)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Khai báo biến global tránh lỗi
    if 'total_delay_mins' not in locals(): total_delay_mins = 0
    
    # Chuẩn hóa tên Carrier
    def clean_carrier_name(name):
        s = str(name).strip().upper()
        # Loại bỏ các ký tự L ở cuối nếu là chữ cái
        while s.endswith('L') and len(s) > 4:
            s = s[:-1]
        return s

    for carrier, group in df_raw.groupby('Carrier Visit'):
        norm_name = clean_carrier_name(carrier)
        if "GATE" in norm_name or "INFO" in norm_name or pd.isna(carrier): continue
        
        # Cấu trúc dữ liệu chuẩn
        data_template = {
            "vessel_name": norm_name, "total_moves": 0, "total_teus": 0,
            "first_move": group['Time_DT'].min(), "last_move": group['Time_DT'].max(),
            "cranes": {}
        }
        
        if norm_name[0].isdigit():
            # Xử lý XE (Truck)
            if norm_name not in truck_summary: truck_summary[norm_name] = data_template.copy()
            truck_summary[norm_name]['total_moves'] += len(group)
            truck_summary[norm_name]['total_teus'] += int(group['TEU'].sum() if 'TEU' in group.columns else 0)
        else:
            # Xử lý SÀ LAN (Barge)
            if norm_name not in barge_summary: barge_summary[norm_name] = data_template.copy()
            moves_df = group[group['Move Kind'].isin(['Load', 'Discharge', 'Sling', 'Restow'])]
            barge_summary[norm_name]['total_moves'] += len(moves_df)
            barge_summary[norm_name]['total_teus'] += int(group['TEU'].sum() if 'TEU' in group.columns else 0)

except Exception as e:
    st.error(f"❌ Lỗi xử lý: {e}")

# Hàm tạo PDF
def create_pdf(barge_data):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BAO CAO SO DO CAU BEN CMIT", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    for item in barge_data:
        pdf.cell(0, 10, f"- {item['name']}: {item['length']}m | {item['bays']} Bays | {item['position_type']}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

def get_js_barges_data(selected_inner, selected_outer):
    data = []
    # Thêm kiểm tra sự tồn tại của key trong all_active_barges
    for name in selected_inner:
        if name in all_active_barges:
            info = all_active_barges[name]
            data.append({
                "name": info['vessel_name'], 
                "length": info.get('length', 70), # Dùng .get() để tránh lỗi nếu thiếu thông số
                "bays": info.get('bays', 4), 
                "is_custom": info.get('is_custom', False), 
                "position_type": "inner"
            })
            
    for name in selected_outer:
        if name in all_active_barges:
            info = all_active_barges[name]
            data.append({
                "name": info['vessel_name'], 
                "length": info.get('length', 70), 
                "bays": info.get('bays', 4), 
                "is_custom": info.get('is_custom', False), 
                "position_type": "outer"
            })
    return data

# 2. KHỞI TẠO TABS CHÍNH (Chỉ khai báo 1 lần)
all_active_barges = {**barge_summary, **st.session_state.custom_barges}
tab_main, tab_config = st.tabs(["🗺️ BERTH PLANNER & DASHBOARD", "⚙️ CONFIG BARGE SPEC"])

with tab_config:
    st.subheader("➕ THÊM SÀ LAN MỚI NGOÀI KẾ HOẠCH CA")
    with st.form("add_new_barge_form", clear_on_submit=True):
        col_new_name, col_new_len, col_new_bay = st.columns([2, 1, 1])
        with col_new_name:
            new_name = st.text_input("Tên Sà Lan Mới:", placeholder="Ví dụ: TAN CANG 99, KIM MINH...")
        with col_new_len:
            new_len = st.number_input("Chiều dài LOA (mét):", min_value=30, max_value=150, value=70)
        with col_new_bay:
            new_bay = st.number_input("Số lượng Bay (1-5):", min_value=1, max_value=5, value=4)
            
        submit_btn = st.form_submit_button("➕ Thêm sà lan vào danh sách")
        if submit_btn and new_name:
            clean_name = new_name.strip().upper()
            st.session_state.custom_barges[clean_name] = {
                "vessel_name": clean_name, "length": new_len, "bays": new_bay,
                "total_moves": 0, "total_teus": 0, "gmph": 0.0, "nmph": 0.0,
                "first_move": datetime.datetime.now(), "last_move": datetime.datetime.now(),
                "cranes": {}, "is_custom": True
            }
            st.success(f"✅ Đã thêm sà lan **{clean_name}** vào danh sách cấu hình!")
    
    st.markdown("---")
    st.subheader("⚙️ CẤU HÌNH THÔNG SỐ SÀ LAN HIỆN HÀNH")
    
    if st.session_state.custom_barges:
        st.write("🔹 **Danh sách sà lan tự thêm:**")
        for cb_name, cb_info in list(st.session_state.custom_barges.items()):
            col_txt, col_l_cb, col_b_cb, col_del = st.columns([2, 1, 1, 0.5])
            with col_txt: st.markdown(f"🛳️ **{cb_name}** *(Thủ công)*")
            with col_l_cb: st.session_state.custom_barges[cb_name]['length'] = st.number_input(f"LOA (m) - {cb_name}", min_value=30, max_value=150, value=int(cb_info['length']), key=f"c_len_{cb_name}")
            with col_b_cb: st.session_state.custom_barges[cb_name]['bays'] = st.number_input(f"Bays - {cb_name}", min_value=1, max_value=5, value=int(cb_info['bays']), key=f"c_bay_{cb_name}")
            with col_del:
                if st.button("🗑️ Xóa", key=f"del_{cb_name}"):
                    del st.session_state.custom_barges[cb_name]
                    st.rerun()

    st.write("🔹 **Danh sách sà lan từ File N4:**")
    for b_name in barge_summary.keys():
        st.markdown(f"🛳️ Sà lan: **{b_name}**")
        col_l, col_b = st.columns(2)
        with col_l:
            if f"len_{b_name}" not in st.session_state: st.session_state[f"len_{b_name}"] = 70 
            barge_summary[b_name]['length'] = st.number_input(f"Chiều dài LOA (mét) - {b_name}:", min_value=40, max_value=120, key=f"len_{b_name}")
        with col_b:
            if f"bay_{b_name}" not in st.session_state: st.session_state[f"bay_{b_name}"] = 4 
            barge_summary[b_name]['bays'] = st.number_input(f"Số lượng Bay - {b_name}:", min_value=1, max_value=5, key=f"bay_{b_name}")

# 4. GIAO DIỆN CHÍNH
with tab_main:
    col_print, col_title = st.columns([1, 5])
    with col_print:
        if st.button("🖨️ Xuất PDF"):
                pdf_data = create_pdf(js_barges_list)
                st.download_button("📥 Tải ngay", pdf_data, "CMIT_Report.pdf", "application/pdf")
    
    st.subheader("🗺️ SƠ ĐỒ SỐ HÓA CẦU BẾN CMIT")
    st.caption("Băng Dưới: Sà lan cập cầu bến trực tiếp (Inner)       |       Băng Trên: Sà lan đậu ngoài cập mạn (Outer)")
    
    # Hàm định dạng nhãn hiển thị kèm thông số trong danh sách xổ xuống
    def format_barge_label(barge_name):
        if barge_name in all_active_barges:
            info = all_active_barges[barge_name]
            return f"{barge_name} (LOA: {info['length']}m | {info['bays']} Bays)"
        return barge_name

    # Tách biệt 2 luồng chọn sà lan riêng biệt với nhãn hiển thị nâng cấp
    col_sel_inner, col_sel_outer = st.columns(2)
    
    with col_sel_inner:
        st.markdown("⚓ **1. Sà lan đậu CẬP CẦU (Băng Dưới):**")
        selected_inner = st.multiselect(
            "Chọn sà lan neo bến trực tiếp:",
            options=list(all_active_barges.keys()),
            default=[], # Đặt là [] để không tự động chọn gì cả
            format_func=format_barge_label,
            key="select_inner_barges"
        )
        
    with col_sel_outer:
        st.markdown("⛓️ **2. Sà lan đậu CẬP MẠN (Băng Trên):**")
        outer_options = [name for name in all_active_barges.keys() if name not in selected_inner]
        selected_outer = st.multiselect(
            "Chọn sà lan cập mạn phía ngoài:",
            options=outer_options,
            default=[], # Đảm bảo ở đây cũng là danh sách rỗng
            format_func=format_barge_label,
            key="select_outer_barges"
        )

    # Đóng gói cấu trúc dữ liệu đẩy xuống Javascript xử lý đồ họa
    js_barges_list = get_js_barges_data(selected_inner, selected_outer)
       
    # Xử lý sà lan cập cầu (Inner - Băng dưới)
    for name in selected_inner:
        if name in all_active_barges:
            info = all_active_barges[name]
            js_barges_list.append({
                "name": info['vessel_name'], "length": info['length'], "bays": info['bays'],
                "is_custom": info.get('is_custom', False), "position_type": "inner"
            })
            
    # Xử lý sà lan cập mạn (Outer - Băng trên)
    for name in selected_outer:
        if name in all_active_barges:
            info = all_active_barges[name]
            js_barges_list.append({
                "name": info['vessel_name'], "length": info['length'], "bays": info['bays'],
                "is_custom": info.get('is_custom', False), "position_type": "outer"
            })

    js_barges_json = json.dumps(js_barges_list)

    # Hệ thống cọc bích chia tỷ lệ 600m bến CMIT
    bollard_ticks_html = ""
    for b_id in range(35):
        meter_mark = b_id * 17.5 
        left_percent = (meter_mark / 600) * 100
        label_display = f"P{b_id}" if b_id % 2 == 0 or b_id == 34 else "•"
        bollard_ticks_html += f"""
        <div style="position: absolute; left: {left_percent}%; top: 115px; transform: translateX(-50%); text-align: center;">
            <div style="width: 5px; height: 10px; background: #2C3E50; margin: 0 auto; border-radius: 1px;"></div>
            <span style="font-size: 9px; font-weight: bold; color: #34495E; display: block; margin-top: 2px;">{label_display}</span>
        </div>
        """
    
    # Hệ thống nhúng HTML/JS (đảm bảo không bị sai thụt lề)
    # Kéo giãn chiều cao container lên 250px để chia làm 2 tầng hầm tàu
    html_code = f"""
    <div id="berth-container" style="position: relative; width: 100%; height: 240px; background-color: #F8F9FA; border: 2px solid #2C3E50; border-radius: 8px; margin-bottom: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden;">
        <div style="position: absolute; top: 120px; width: 100%; height: 2px; background: #BDC3C7;"></div>
        {bollard_ticks_html}
        <div id="vessels-zone"></div>
    </div>

    <script>
        (function() {{
            const bargesData = {js_barges_json};
            const zone = document.getElementById("vessels-zone");
            
            const colors = ["#2980B9", "#27AE60", "#8E44AD", "#C0392B", "#16A085"];
            const customColor = "#E67E22"; // Màu cam cho sà lan tự tạo
            
            let elements = [];
            let currentLeftInner = 30;
            let currentLeftOuter = 40;

            bargesData.forEach((b, index) => {{
                const div = document.createElement("div");
                div.style.position = "absolute";
                
                // Định vị chiều cao tầng dựa trên luồng vị trí Đậu Cầu hay Cập Mạn
                if (b.position_type === "outer") {{
                    div.style.top = "15px"; // Băng trên dành cho Cập mạn
                    div.style.left = currentLeftOuter + "px";
                    currentLeftOuter += (b.length * 1.8) + 40;
                }} else {{
                    div.style.top = "65px"; // Băng dưới sát cọc bích dành cho Cập cầu
                    div.style.left = currentLeftInner + "px";
                    currentLeftInner += (b.length * 1.8) + 40;
                }}
                
                div.style.width = (b.length * 1.8) + "px"; 
                div.style.height = "42px";
                div.style.backgroundColor = b.is_custom ? customColor : colors[index % colors.length];
                div.style.color = "white";
                div.style.borderRadius = "5px";
                div.style.textAlign = "center";
                div.style.fontSize = "11px";
                div.style.fontWeight = "bold";
                div.style.cursor = "ew-resize";
                div.style.boxShadow = "0 4px 6px rgba(0,0,0,0.15)";
                div.style.userSelect = "none";
                div.style.display = "flex";
                div.style.flexDirection = "column";
                div.style.justifyContent = "center";
                div.style.border = "1px solid rgba(255,255,255,0.3)";
                
                let typeIcon = b.position_type === "outer" ? "⛓️ [MẠN] " : "⚓ [CẦU] ";
                let srcIcon = b.is_custom ? "📝 " : "";
                
                div.innerHTML = `<span style='white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding:0 3px;'>${{typeIcon}}${{srcIcon}}${{b.name}}</span>
                                 <span style='font-size:9px; background:rgba(0,0,0,0.25); border-radius:3px; margin:2px 4px 0 4px; padding:1px 0;'>📊 ${{b.bays}} Bays (${{b.length}}m)</span>`;
                
                zone.appendChild(div);
                
                elements.push({{
                    el: div,
                    left: parseInt(div.style.left),
                    width: (b.length * 1.8),
                    name: b.name,
                    position_type: b.position_type // Lưu loại luồng để tính toán va chạm độc lập
                }});
            }});

            // Hàm xử lý va chạm thông minh, tách riêng luồng tầng trên và tầng dưới
            function resolveCollisions(movedIndex) {{
                let changed = true;
                let loops = 0;
                const targetType = elements[movedIndex].position_type;

                while (changed && loops < 50) {{
                    changed = false;
                    loops++;
                    for (let i = 0; i < elements.length; i++) {{
                        for (let j = 0; j < elements.length; j++) {{
                            if (i === j) continue;
                            
                            let r1 = elements[i];
                            let r2 = elements[j];
                            
                            // CHỈ XỬ LÝ VA CHẠM NẾU 2 SÀ LAN CÙNG TẦNG (CÙNG LUỒNG)
                            if (r1.position_type !== targetType || r2.position_type !== targetType) continue;
                            
                            if (r1.left < r2.left + r2.width && r1.left + r1.width > r2.left) {{
                                changed = true;
                                let overlap = Math.min(r1.left + r1.width - r2.left, r2.left + r2.width - r1.left);
                                
                                if (i === movedIndex) {{
                                    if (r1.left + r1.width / 2 > r2.left + r2.width / 2) {{ r2.left -= overlap; }} else {{ r2.left += overlap; }}
                                }} else if (j === movedIndex) {{
                                    if (r2.left + r2.width / 2 > r1.left + r1.width / 2) {{ r1.left -= overlap; }} else {{ r1.left += overlap; }}
                                }} else {{
                                    r1.left -= overlap / 2; r2.left += overlap / 2;
                                }}
                                
                                if(r1.left < 5) r1.left = 5;
                                if(r2.left < 5) r2.left = 5;
                                
                                r1.el.style.left = r1.left + "px";
                                r2.el.style.left = r2.left + "px";
                            }}
                        }}
                    }}
                }}
            }}

            elements.forEach((item, index) => {{
                item.el.onmousedown = function(e) {{
                    let startX = e.clientX;
                    let initialLeft = item.left;
                    
                    document.onmousemove = function(ev) {{
                        let deltaX = ev.clientX - startX;
                        let newLeft = initialLeft + deltaX;
                        if (newLeft < 5) newLeft = 5;
                        
                        item.left = newLeft;
                        item.el.style.left = newLeft + "px";
                        
                        resolveCollisions(index);
                    }};
                    
                    document.onmouseup = function() {{
                        document.onmousemove = null;
                        document.onmouseup = null;
                    }};
                }};
            }});
        }})();
    </script>
    """

    st.components.v1.html(html_code, height=255)

# =====================================================================
# 7. KHÔI PHỤC HOÀN TOÀN KHU VỰC XE ĐẦU KÉO NGOÀI
# =====================================================================
st.write("---")
st.subheader("🚛 KHU VỰC QUẢN LÝ XE ĐẦU KÉO NGOÀI (EXTERNAL TRUCKS)")

if truck_summary:
    # 1. Chuẩn bị dữ liệu dạng bảng sạch sẽ
    truck_data = []
    for t_name, t_info in truck_summary.items():
        truck_data.append({
            "Mã Xe": t_name,
            "Số Lượt": t_info.get('total_moves', 0),
            "Tổng TEUs": t_info.get('total_teus', 0),
            "Thời điểm đầu": t_info['first_move'].strftime('%H:%M') if isinstance(t_info['first_move'], datetime.datetime) else "N/A",
            "Thời điểm cuối": t_info['last_move'].strftime('%H:%M') if isinstance(t_info['last_move'], datetime.datetime) else "N/A"
        })
    
    df_trucks = pd.DataFrame(truck_data)
    
    # 2. Hiển thị bảng duy nhất
    st.dataframe(df_trucks, use_container_width=True, hide_index=True)

    # 3. Chọn định dạng tải về
    format_choice = st.radio("Chọn định dạng file tải về:", ("CSV", "Excel"), horizontal=True, key="truck_dl_format")

    if format_choice == "CSV":
        csv_data = df_trucks.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Tải xuống CSV", csv_data, "danh_sach_xe.csv", "text/csv")
    else:
        import io
        buffer = io.BytesIO()
        # Sử dụng engine xlsxwriter (đảm bảo đã cài đặt trong requirements.txt)
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_trucks.to_excel(writer, index=False, sheet_name='Trucks')
        st.download_button(
            label="📥 Tải xuống Excel",
            data=buffer.getvalue(),
            file_name="danh_sach_xe.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Không có dữ liệu xe đầu kéo trong ca hiện tại.")
    
# Tự động refresh (Đặt ở cuối cùng của file)
components.html("<script>setTimeout(function(){ window.location.reload(); }, 30000);</script>", height=0)
