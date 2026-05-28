import streamlit as st
import pandas as pd
import datetime
import warnings
import json

# 1. Cấu hình trang và tối ưu giao diện màn hình rộng
warnings.filterwarnings("ignore")
st.set_page_config(layout="wide", page_title="CMIT Berthing & Productivity Master Control")

st.title("🚢 CMIT - BERTH PLANNER & PERFORMANCE DASHBOARD")
st.caption("Quản lý cầu bến CMIT - Hỗ trợ phân luồng kéo thả sà lan Cập Cầu (Inner) và Cập Mạn (Outer) chống chồng lấn")

st.write(f"🔄 *Cập nhật log lúc: {datetime.datetime.now().strftime('%H:%M:%S')} (Tự động làm mới sau 30s)*")

# Khởi tạo vùng lưu trữ trạng thái sà lan tự thêm mới
if "custom_barges" not in st.session_state:
    st.session_state.custom_barges = {}

# Khởi tạo vùng lưu trữ tạm thời thông số LOA/Bay được điều chỉnh từ File N4 để tránh bị mất khi nạp lại vòng lặp
if "n4_barges_config" not in st.session_state:
    st.session_state.n4_barges_config = {}

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
# 3. ĐỌC VÀ XỬ LÝ DỮ LIỆU GỐC TỪ FILE LOG N4
# =====================================================================
file_path = "MoveEvent_20260526_2203.xlsx"

barge_summary = {}
truck_summary = {}

try:
    df_raw = pd.read_excel(file_path, skiprows=4)
    df_raw.columns = df_raw.columns.str.strip()
    
    iso_col = next((c for c in df_raw.columns if 'ISO' in c or 'Unit Type' in c or 'Size' in c), None)
    df_raw['TEU'] = df_raw[iso_col].apply(lambda x: 1 if str(x).strip().startswith("2") else 2) if iso_col else 1.5
    
    df_raw['Time_Clean'] = df_raw['Time Completed'].astype(str).str.replace(":", "")
    df_raw['Time_DT'] = pd.to_datetime(df_raw['Time_Clean'], format='%d-%b-%y %H%M', errors='coerce')
    df_raw = df_raw.dropna(subset=['Time_DT', 'Carrier Visit'])
    
    che_col = next((c for c in ['Put CHE Name', 'Fetch CHE Name'] if c in df_raw.columns), None)

    for carrier, group in df_raw.groupby('Carrier Visit'):
        carrier_str = str(carrier).strip()
        if "GATE" in carrier_str or "INFO" in carrier_str or pd.isna(carrier):
            continue
            
        if carrier_str[0].isdigit():
            total_moves = len(group)
            total_teus = int(group['TEU'].sum())
            first_m = group['Time_DT'].min()
            last_m = group['Time_DT'].max()
            
            if carrier_str in truck_summary:
                truck_summary[carrier_str]['total_moves'] += total_moves
                truck_summary[carrier_str]['total_teus'] += total_teus
                truck_summary[carrier_str]['first_move'] = min(truck_summary[carrier_str]['first_move'], first_m)
                truck_summary[carrier_str]['last_move'] = max(truck_summary[carrier_str]['last_move'], last_m)
            else:
                truck_summary[carrier_str] = {
                    "vessel_name": carrier_str, "total_moves": total_moves, "total_teus": total_teus,
                    "first_move": first_m, "last_move": last_m, "cranes": {}
                }
            continue

        moves_df = group[group['Move Kind'].isin(['Load', 'Discharge', 'Sling', 'Restow'])]
        if len(moves_df) == 0:
            continue
            
        total_moves = len(moves_df)
        total_teus = int(group['TEU'].sum())
        first_m = group['Time_DT'].min()
        last_m = group['Time_DT'].max()
        
        crane_details = {}
        if che_col:
            qc_moves = moves_df[moves_df[che_col].astype(str).str.startswith("QC", na=False)]
            for qc_name, qc_group in qc_moves.groupby(che_col):
                c_moves = len(qc_group)
                c_first = qc_group['Time_DT'].min()
                c_last = qc_group['Time_DT'].max()
                c_gmph = 0.0
                if pd.notna(c_first) and pd.notna(c_last):
                    hours = (c_last - c_first).total_seconds() / 3600
                    if hours > 0: c_gmph = round(c_moves / hours, 1)
                
                crane_details[qc_name] = {
                    "moves": c_moves, "gmph": c_gmph,
                    "timeline": f"{c_first.strftime('%H:%M')} ➔ {c_last.strftime('%H:%M')}"
                }

        if carrier_str in barge_summary:
            barge_summary[carrier_str]['total_moves'] += total_moves
            barge_summary[carrier_str]['total_teus'] += total_teus
            barge_summary[carrier_str]['first_move'] = min(barge_summary[carrier_str]['first_move'], first_m)
            barge_summary[carrier_str]['last_move'] = max(barge_summary[carrier_str]['last_move'], last_m)
            for q_name, q_data in crane_details.items():
                if q_name in barge_summary[carrier_str]['cranes']:
                    barge_summary[carrier_str]['cranes'][q_name]['moves'] += q_data['moves']
                else:
                    barge_summary[carrier_str]['cranes'][q_name] = q_data
        else:
            # Khôi phục thông số chiều dài và số bay từ cấu hình chỉnh sửa (nếu có), mặc định là 70m và 4 bửng
            saved_len = st.session_state.n4_barges_config.get(carrier_str, {}).get('length', 70)
            saved_bay = st.session_state.n4_barges_config.get(carrier_str, {}).get('bays', 4)
            
            barge_summary[carrier_str] = {
                "vessel_name": carrier_str, "total_moves": total_moves, "total_teus": total_teus,
                "first_move": first_m, "last_move": last_m, "cranes": crane_details, "is_custom": False,
                "length": saved_len, "bays": saved_bay
            }

    for b_info in barge_summary.values():
        g_hours = (b_info['last_move'] - b_info['first_move']).total_seconds() / 3600
        n_hours = g_hours - (total_delay_mins / 60)
        b_info['gmph'] = round(b_info['total_moves'] / g_hours, 1) if g_hours > 0 else 0
        b_info['nmph'] = round(b_info['total_moves'] / n_hours, 1) if n_hours > 0 else 0

    for t_info in truck_summary.values():
        g_hours = (t_info['last_move'] - t_info['first_move']).total_seconds() / 3600
        t_info['gmph'] = round(t_info['total_moves'] / g_hours, 1) if g_hours > 0 else 0
        t_info['nmph'] = t_info['gmph']

except Exception as e:
    st.error(f"❌ Lỗi cấu trúc hoặc xử lý tệp tin Excel: {e}")
    st.stop()


# =====================================================================
# 4. CHIA PHÂN HỆ KHÔNG GIAN TAB
# =====================================================================
tab_main, tab_config = st.tabs(["🗺️ BERTH PLANNER & DASHBOARD", "⚙️ CONFIG BARGE SPEC (NHẬP THÔNG SỐ SÀ LAN)"])

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
    st.subheader("⚙️ BẢNG CẤU HÌNH THÔNG SỐ SÀ LAN HIỆN HÀNH")
    
    # --- PHẦN 1: BẢNG SÀ LAN THỦ CÔNG ---
    if st.session_state.custom_barges:
        st.write("🔹 **Danh sách sà lan tự thêm:**")
        custom_table_data = []
        for cb_name, cb_info in st.session_state.custom_barges.items():
            custom_table_data.append({
                "Tên Sà Lan (Thủ công)": cb_name,
                "Chiều dài LOA (mét)": int(cb_info['length']),
                "Số lượng Bay (Bays)": int(cb_info['bays']),
            })
        
        df_custom_editable = pd.DataFrame(custom_table_data)
        edited_custom_df = st.data_editor(
            df_custom_editable,
            use_container_width=True,
            hide_index=True,
            disabled=["Tên Sà Lan (Thủ công)"],
            key="custom_barge_editor",
            column_config={
                "Chiều dài LOA (mét)": st.column_config.NumberColumn(min_value=30, max_value=150, step=1, format="%d m"),
                "Số lượng Bay (Bays)": st.column_config.NumberColumn(min_value=1, max_value=5, step=1, format="%d B")
            }
        )
        
        # Đồng bộ ngược vào session_state cho sà lan thủ công
        for _, row in edited_custom_df.iterrows():
            name = row["Tên Sà Lan (Thủ công)"]
            st.session_state.custom_barges[name]['length'] = row["Chiều dài LOA (mét)"]
            st.session_state.custom_barges[name]['bays'] = row["Số lượng Bay (Bays)"]
            
        # Nút hỗ trợ xóa nhanh sà lan tự thêm
        to_delete = st.multiselect("🗑️ Chọn sà lan thủ công muốn xóa hoàn toàn:", options=list(st.session_state.custom_barges.keys()))
        if st.button("Xác nhận xóa sà lan đã chọn"):
            for name in to_delete:
                del st.session_state.custom_barges[name]
            st.rerun()

    # --- PHẦN 2: BẢNG SÀ LAN TỪ FILE N4 ---
    if barge_summary:
        st.write("🔹 **Danh sách sà lan lấy từ File N4:**")
        n4_table_data = []
        for b_name, b_info in barge_summary.items():
            n4_table_data.append({
                "Tên Sà Lan (N4)": b_name,
                "Chiều dài LOA (mét)": int(b_info['length']),
                "Số lượng Bay (Bays)": int(b_info['bays']),
            })
            
        df_n4_editable = pd.DataFrame(n4_table_data)
        edited_n4_df = st.data_editor(
            df_n4_editable,
            use_container_width=True,
            hide_index=True,
            disabled=["Tên Sà Lan (N4)", "Tổng Sản Lượng (Moves)", "Tổng Sản Lượng (TEUs)"],
            key="n4_barge_editor",
            column_config={
                "Chiều dài LOA (mét)": st.column_config.NumberColumn(min_value=40, max_value=120, step=1, format="%d m"),
                "Số lượng Bay (Bays)": st.column_config.NumberColumn(min_value=1, max_value=5, step=1, format="%d B")
            }
        )
        
        # Lưu vết thông số và đồng bộ ngược vào hệ thống chính dữ liệu sà lan N4
        for _, row in edited_n4_df.iterrows():
            name = row["Tên Sà Lan (N4)"]
            barge_summary[name]['length'] = row["Chiều dài LOA (mét)"]
            barge_summary[name]['bays'] = row["Số lượng Bay (Bays)"]
            # Lưu trữ lại bộ nhớ session_state để không bị reset khi trang tự reload sau 30 giây
            st.session_state.n4_barges_config[name] = {
                "length": row["Chiều dài LOA (mét)"],
                "bays": row["Số lượng Bay (Bays)"]
            }

all_active_barges = {**barge_summary, **st.session_state.custom_barges}


# =====================================================================
# 5. PHÂN HỆ ĐIỀU PHỐI CHÍNH (TAB 1)
# =====================================================================
with tab_main:
    st.subheader("🗺️ SƠ ĐỒ SỐ HÓA CẦU BẾN CMIT KÉO THẢ PHÂN LUỒNG MẠN TÀU")
    st.caption("Băng Dưới: Sà lan cập cầu bến trực tiếp (Inner) | Băng Trên: Sà lan đậu ngoài cập mạn (Outer)")
    
    # Hàm định dạng nhãn hiển thị kèm thông số trong danh sách xổ xuống
    def format_barge_label(barge_name):
        if barge_name in all_active_barges:
            info = all_active_barges[barge_name]
            return f"{barge_name} (LOA: {info['length']}m | {info['bays']} Bays)"
        return barge_name

    # Lấy danh sách đã chọn hiện tại từ session_state để lọc động
    current_inner = st.session_state.get("select_inner_barges", [])
    current_outer = st.session_state.get("select_outer_barges", [])

    # Tách biệt 2 luồng chọn sà lan riêng biệt với bộ lọc động loại trừ nhau hoàn toàn
    col_sel_inner, col_sel_outer = st.columns(2)
    
    with col_sel_inner:
        st.markdown("⚓ **1. Sà lan đậu CẬP CẦU (Băng Dưới):**")
        # Luồng 1: Loại trừ các sà lan đã lỡ chọn ở luồng Cập Mạn phía ngoài
        inner_options = [name for name in all_active_barges.keys() if name not in current_outer]
        
        selected_inner = st.multiselect(
            "Chọn sà lan neo bến trực tiếp:",
            options=inner_options,
            format_func=format_barge_label,
            key="select_inner_barges"
        )
        
    with col_sel_outer:
        st.markdown("⛓️ **2. Sà lan đậu CẬP MẠN (Băng Trên):**")
        # Luồng 2: Loại trừ TUYỆT ĐỐI các sà lan đã được chọn ở luồng Cập Cầu trực tiếp
        outer_options = [name for name in all_active_barges.keys() if name not in selected_inner]
        
        selected_outer = st.multiselect(
            "Chọn sà lan cập mạn phía ngoài:",
            options=outer_options,
            format_func=format_barge_label,
            key="select_outer_barges"
        )

    # Đóng gói cấu trúc dữ liệu đẩy xuống Javascript xử lý đồ họa
    js_barges_list = []
    
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
    # 6. HIỂN THỊ DANH SÁCH CHI TIẾT THEO PHÂN LUỒNG
    # =====================================================================
    st.subheader("📋 CHI TIẾT SÀ LAN ĐANG BIỂU DIỄN TRÊN SƠ ĐỒ")
    
    # Hiển thị sà lan cập cầu
    if selected_inner:
        st.markdown("🔹 **Danh sách sà lan đang đậu tại Cầu (Inner):**")
        for name in selected_inner:
            if name in all_active_barges:
                b_info = all_active_barges[name]
                is_cb = b_info.get('is_custom', False)
                with st.expander(f"⚓ [CẦU] {b_info['vessel_name']} ➔ LOA: {b_info['length']}m | {b_info['bays']} Bays | GMPH: {b_info['gmph']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        if is_cb: st.info("💡 Sà lan kế hoạch thêm thủ công bằng tay.")
                        else: st.markdown(f"* ⏱ **Thời gian làm:** {b_info['first_move'].strftime('%H:%M')} ➔ {b_info['last_move'].strftime('%H:%M')}\n* 📦 **Sản lượng:** `{b_info['total_teus']}` TEU")
                    with col2:
                        st.markdown(f"* 📐 **LOA:** `{b_info['length']}` m\n* 📊 **Hầm hàng:** `{b_info['bays']}` Bays\n* 📈 **NMPH:** `{b_info['nmph']}`")
                    if not is_cb and b_info['cranes']:
                        crane_table = [{"Mã Cẩu QC": q_name, "Sản lượng (Moves)": q_data['moves'], "Năng suất (GMPH)": q_data['gmph'], "Khung giờ làm": q_data['timeline']} for q_name, q_data in b_info['cranes'].items()]
                        st.dataframe(pd.DataFrame(crane_table), use_container_width=True, hide_index=True)

    # Hiển thị sà lan cập mạn
    if selected_outer:
        st.markdown("🔹 **Danh sách sà lan đang đậu Cập Mạn tàu khác (Outer):**")
        for name in selected_outer:
            if name in all_active_barges:
                b_info = all_active_barges[name]
                is_cb = b_info.get('is_custom', False)
                with st.expander(f"⛓️ [CẬP MẠN] {b_info['vessel_name']} ➔ LOA: {b_info['length']}m | {b_info['bays']} Bays", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        if is_cb: st.info("💡 Sà lan cập mạn bổ sung ngoài kế hoạch.")
                        else: st.markdown(f"* ⏱ **Thời gian làm:** {b_info['first_move'].strftime('%H:%M')} ➔ {b_info['last_move'].strftime('%H:%M')}\n* 📦 **Sản lượng:** `{b_info['total_teus']}` TEU")
                    with col2:
                        st.markdown(f"* 📐 **LOA:** `{b_info['length']}` m\n* 📊 **Hầm hàng:** `{b_info['bays']}` Bays")

    if not selected_inner and not selected_outer:
        st.info("Vui lòng lựa chọn sà lan từ hai hộp chọn phía trên để bắt đầu lập sơ đồ.")

    # =====================================================================
    # 7. KHÔI PHỤC HOÀN TOÀN KHU VỰC XE ĐẦU KÉO NGOÀI
    # =====================================================================
    st.write("---")
    st.subheader("... 🚛 KHU VỰC QUẢN LÝ XE ĐẦU KÉO NGOÀI (EXTERNAL TRUCKS)")
    
    if truck_summary:
        truck_data = []
        for t_name, t_info in truck_summary.items():
            truck_data.append({
                "Mã Xe": t_name,
                "Số Lượt": t_info['total_moves'],
                "Tổng TEUs": t_info['total_teus'],
                "Thời điểm đầu": t_info['first_move'].strftime('%H:%M'),
                "Thời điểm cuối": t_info['last_move'].strftime('%H:%M')
            })
        df_trucks = pd.DataFrame(truck_data)
        st.dataframe(df_trucks, use_container_width=True, hide_index=True)
        
        format_choice = st.radio("Chọn định dạng file tải về:", ("CSV", "Excel"), horizontal=True, key="truck_dl_format")
        if format_choice == "CSV":
            csv_data = df_trucks.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Tải xuống CSV", csv_data, "danh_sach_xe.csv", "text/csv")
        else:
            import io
            buffer = io.BytesIO()
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

# Tự động đồng bộ làm mới trang sau mỗi 30 giây
st.components.v1.html(
    "<script>setTimeout(function(){ window.location.reload(); }, 30000);</script>",
    height=0,
)
