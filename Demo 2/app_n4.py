import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Cấu hình giao diện trang web Dashboard
st.set_page_config(page_title="CMIT Shift Report Generator", page_icon="🚢", layout="wide")

st.title("🚢 CMIT SHIFT REPORT GENERATOR")
st.markdown("---")
st.write("👋 **Terminal Supervisor!** Hệ thống này giúp chuyển đổi dữ liệu N4 thô thành file báo cáo ca trực chuẩn định dạng mẫu `SHIFT_REPORT` bằng công cụ tự động.")

# Nút tải file thô đầu vào từ hệ thống N4
uploaded_file = st.file_uploader("📁 Chọn file Excel dữ liệu N4 gốc của ca trực (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    st.success("🎉 Đã nhận dữ liệu ca trực! Đang tiến hành bóc tách và dựng form báo cáo chuẩn...")
    
    try:
        # 1. ĐỌC VÀ LÀM SẠCH DỮ LIỆU THÔ
        df = pd.read_excel(uploaded_file, skiprows=4)
        df.columns = [col.strip() for col in df.columns]
        
        # Đồng bộ hóa chuỗi dữ liệu để tính toán chính xác
        df['Move_Kind_Str'] = df['Move Kind'].astype(str).str.strip().str.upper()
        df['QC_Name'] = df['Fetch CHE Name'].fillna(df['Put CHE Name']).astype(str).str.strip().str.upper()
        df['RTG_Name'] = df['Fetch CHE Name'].fillna(df['Put CHE Name']).astype(str).str.strip().str.upper()
        
        # 2. XỬ LÝ LOGIC SỐ LIỆU CHO CÁC PHÂN MỤC BÁO CÁO
        total_moves = len(df)
        
        # Tính năng suất khai thác tổng (Moves/Hour) dựa trên thời gian thực tế hoàn thành container
        df['Time Completed'] = pd.to_datetime(df['Time Completed'], errors='coerce')
        valid_times = df['Time Completed'].dropna()
        if not valid_times.empty:
            time_delta = valid_times.max() - valid_times.min()
            total_hours = max(time_delta.total_seconds() / 3600, 0.5)
            net_productivity = total_moves / total_hours
        else:
            total_hours = 8.0
            net_productivity = total_moves / total_hours

        # Bảng 1: Move Kind Summary
        summary_move_kind = df['Move Kind'].fillna('Others').value_counts().reset_index()
        summary_move_kind.columns = ['Move Kind', 'Moves']
        
        # Bảng 2: Vessel/Barge Report
        vessel_moves = df[df['Move_Kind_Str'].isin(['LOAD', 'DISCHARGE'])]
        summary_vessel = vessel_moves['Carrier Visit'].fillna('Yard/Internal').value_counts().reset_index()
        summary_vessel.columns = ['Vessel/Barge', 'Moves']
        
        # Bảng 3: Crane Performance (QC)
        qc_df = df[df['QC_Name'].str.startswith('QC', na=False)]
        summary_qc = qc_df['QC_Name'].value_counts().reset_index()
        summary_qc.columns = ['Crane', 'Moves']
        
        # Bảng 4: Line Operator Summary
        summary_line = df['Line Op'].fillna('Unknown').value_counts().reset_index()
        summary_line.columns = ['Line Operator', 'Moves']
        
        # Bảng 5: Container Size (ISO)
        df['ISO_First_Char'] = df['Unit Type ISO'].astype(str).str.strip().str[0]
        df['Size_Group'] = df['ISO_First_Char'].map({'2': '20ft', '4': '40ft/45ft'}).fillna('Special')
        summary_size = df['Size_Group'].value_counts().reset_index()
        summary_size.columns = ['Size', 'Quantity']

        # Bảng 6: Top Yard Equipment (TT & RTG)
        summary_tt = df['Carry CHE Name'].dropna().astype(str).str.strip().str.upper().value_counts().head(5).reset_index()
        summary_tt.columns = ['Truck (TT)', 'Trips']
        
        rtg_df = df[df['RTG_Name'].str.startswith('RTG', na=False)]
        summary_rtg = rtg_df['RTG_Name'].value_counts().head(5).reset_index()
        summary_rtg.columns = ['RTG Crane', 'Moves']

        # 3. TIẾN HÀNH DỰNG FILE EXCEL GIỐNG Y HỆT FILE MẪU CHUẨN D1
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('SUMMARY REPORT')
            writer.sheets['SUMMARY REPORT'] = worksheet
            
            # Hiện đường gridline để căn chỉnh chuẩn
            worksheet.hide_gridlines(0)
            
            # --- KHỞI TẠO ĐỊNH DẠNG THEO FILE TIÊU CHUẨN D1 ---
            font_family = 'Segoe UI'
            
            # Định dạng Tiêu đề lớn chính của cảng
            main_title_fmt = workbook.add_format({
                'bold': True, 'font_size': 16, 'font_color': '#1F4E78', 'font_name': font_family, 'align': 'left', 'valign': 'vcenter'
            })
            meta_info_fmt = workbook.add_format({
                'italic': True, 'font_size': 10, 'font_color': '#595959', 'font_name': font_family
            })
            
            # Định dạng bảng Tóm tắt Chỉ số KPI chính (Khối viền cam nổi bật)
            kpi_header_fmt = workbook.add_format({
                'bold': True, 'font_size': 11, 'bg_color': '#D9E1F2', 'font_color': '#1F4E78', 'border': 1, 'align': 'center', 'font_name': font_family
            })
            kpi_label_fmt = workbook.add_format({
                'bold': True, 'font_size': 10, 'bg_color': '#F2F2F2', 'border': 1, 'font_name': font_family, 'align': 'left'
            })
            kpi_value_fmt = workbook.add_format({
                'bold': True, 'font_size': 11, 'font_color': '#C65911', 'border': 1, 'align': 'center', 'font_name': font_family
            })
            
            # Định dạng Tiêu đề các bảng danh mục nhỏ
            section_title_fmt = workbook.add_format({
                'bold': True, 'font_size': 12, 'font_color': '#1F4E78', 'font_name': font_family, 'bottom': 2, 'bottom_color': '#1F4E78'
            })
            
            # Định dạng Header của từng bảng dữ liệu (Xanh Navy chữ trắng đặc trưng)
            tbl_header_fmt = workbook.add_format({
                'bold': True, 'font_size': 10, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_name': font_family
            })
            
            # Định dạng nội dung dòng dữ liệu thô
            cell_text_fmt = workbook.add_format({'border': 1, 'align': 'left', 'font_size': 10, 'font_name': font_family})
            cell_num_fmt = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 10, 'num_format': '#,##0', 'font_name': font_family})
            
            # Định dạng dòng tổng (Total Row) ở cuối mỗi bảng dữ liệu
            total_label_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#EAEAEA', 'font_size': 10, 'font_name': font_family, 'align': 'left'})
            total_num_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#EAEAEA', 'font_size': 10, 'font_color': '#1F4E78', 'num_format': '#,##0', 'font_name': font_family, 'align': 'center'})

            # --- GHI DỮ LIỆU ĐẦU TRANG (HEADER BLOCK) ---
            worksheet.write('A1', 'CMIT TERMINAL OPERATIONAL SHIFT REPORT', main_title_fmt)
            worksheet.write('A2', f'Generated Automatically on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Shift: D1', meta_info_fmt)
            
            # --- GHI KHỐI SỐ LIỆU TỔNG HỢP KPI CA TRỰC (Dòng 4 -> 7) ---
            worksheet.merge_range('A4:B4', 'KEY PERFORMANCE INDICATORS (KPIs)', kpi_header_fmt)
            worksheet.write('A5', ' Total Volume (Moves)', kpi_label_fmt)
            worksheet.write('B5', total_moves, kpi_value_fmt)
            worksheet.write('A6', ' Total Operation Time (Hours)', kpi_label_fmt)
            worksheet.write('B6', f"{round(total_hours, 1)} hrs", kpi_value_fmt)
            worksheet.write('A7', ' Net Productive Factor (M/H)', kpi_label_fmt)
            worksheet.write('B7', f"{round(net_productivity, 1)} M/H", kpi_value_fmt)
            
            # --- PHÂN CHIA KHÔNG GIAN CÁC BẢNG THEO ĐÚNG THIẾT KẾ CỦA FILE D1 ---
            
            # [BẢNG 1] Move Kind Summary (Cột A, B - Hàng 10)
            worksheet.write('A10', '1. MOVE KIND SUMMARY', section_title_fmt)
            worksheet.write(10, 0, 'Move Kind', tbl_header_fmt)
            worksheet.write(10, 1, 'Moves', tbl_header_fmt)
            for idx, row in summary_move_kind.iterrows():
                worksheet.write(11+idx, 0, f" {row['Move Kind']}", cell_text_fmt)
                worksheet.write(11+idx, 1, row['Moves'], cell_num_fmt)
            end_r_b1 = 11 + len(summary_move_kind)
            worksheet.write(end_r_b1, 0, ' Total Moves', total_label_fmt)
            worksheet.write(end_r_b1, 1, f"=SUM(B12:B{end_r_b1})", total_num_fmt)
            
            # [BẢNG 2] Vessel / Barge Report (Cột A, B - Nằm dưới bảng 1)
            start_r_b2 = end_r_b1 + 3
            worksheet.write(start_r_b2, 0, '2. VESSEL / BARGE PERFORMANCE', section_title_fmt)
            worksheet.write(start_r_b2+1, 0, 'Vessel / Barge Name', tbl_header_fmt)
            worksheet.write(start_r_b2+1, 1, 'Moves Count', tbl_header_fmt)
            for idx, row in summary_vessel.iterrows():
                worksheet.write(start_r_b2+2+idx, 0, f" {row['Vessel/Barge']}", cell_text_fmt)
                worksheet.write(start_r_b2+2+idx, 1, row['Moves'], cell_num_fmt)
            end_r_b2 = start_r_b2 + 2 + len(summary_vessel)
            worksheet.write(end_r_b2, 0, ' Total Vessel Productivity', total_label_fmt)
            worksheet.write(end_r_b2, 1, f"=SUM(B{start_r_b2+3}:B{end_r_b2})", total_num_fmt)

            # [BẢNG 3] Crane Performance (Cột D, E - Hàng 10)
            worksheet.write('D10', '3. CRANE PRODUCTION (QC)', section_title_fmt)
            worksheet.write(10, 3, 'Crane ID', tbl_header_fmt)
            worksheet.write(10, 4, 'Moves', tbl_header_fmt)
            for idx, row in summary_qc.iterrows():
                worksheet.write(11+idx, 3, f" {row['Crane']}", cell_text_fmt)
                worksheet.write(11+idx, 4, row['Moves'], cell_num_fmt)
            end_r_b3 = 11 + len(summary_qc)
            worksheet.write(end_r_b3, 3, ' Total QC Moves', total_label_fmt)
            worksheet.write(end_r_b3, 4, f"=SUM(E12:E{end_r_b3})", total_num_fmt)

            # [BẢNG 4] Line Operator Summary (Cột D, E - Nằm dưới bảng 3)
            start_r_b4 = end_r_b3 + 3
            worksheet.write(start_r_b4, 3, '4. LINE OPERATOR SUMMARY', section_title_fmt)
            worksheet.write(start_r_b4+1, 3, 'Line Operator', tbl_header_fmt)
            worksheet.write(start_r_b4+1, 4, 'Total Moves', tbl_header_fmt)
            for idx, row in summary_line.iterrows():
                worksheet.write(start_r_b4+2+idx, 3, f" {row['Line Operator']}", cell_text_fmt)
                worksheet.write(start_r_b4+2+idx, 4, row['Moves'], cell_num_fmt)
            end_r_b4 = start_r_b4 + 2 + len(summary_line)
            worksheet.write(end_r_b4, 3, ' Total Line Volume', total_label_fmt)
            worksheet.write(end_r_b4, 4, f"=SUM(E{start_r_b4+3}:E{end_r_b4})", total_num_fmt)

            # [BẢNG 5] Container Size Breakdown (Cột G, H - Hàng 10)
            worksheet.write('G10', '5. CONTAINER SIZE BREAKDOWN', section_title_fmt)
            worksheet.write(10, 6, 'ISO Size Group', tbl_header_fmt)
            worksheet.write(10, 7, 'Quantity (Unit)', tbl_header_fmt)
            for idx, row in summary_size.iterrows():
                worksheet.write(11+idx, 6, f" {row['Size']}", cell_text_fmt)
                worksheet.write(11+idx, 7, row['Quantity'], cell_num_fmt)
            end_r_b5 = 11 + len(summary_size)
            worksheet.write(end_r_b5, 6, ' Total Teus/Units', total_label_fmt)
            worksheet.write(end_r_b5, 7, f"=SUM(H12:H{end_r_b5})", total_num_fmt)

            # [BẢNG 6] Top Yard Equipment Aktiv (Cột G, H - Nằm dưới bảng 5)
            start_r_b6 = end_r_b5 + 3
            worksheet.write(start_r_b6, 6, '6. YARD EQUIPMENT ACTIVITY', section_title_fmt)
            worksheet.write(start_r_b6+1, 6, 'Truck (TT Code)', tbl_header_fmt)
            worksheet.write(start_r_b6+1, 7, 'Total Trips', tbl_header_fmt)
            for idx, row in summary_tt.iterrows():
                worksheet.write(start_r_b6+2+idx, 6, f" {row['Truck (TT)']}", cell_text_fmt)
                worksheet.write(start_r_b6+2+idx, 7, row['Trips'], cell_num_fmt)
                
            start_r_b7 = start_r_b6 + 2 + len(summary_tt) + 2
            worksheet.write(start_r_b7, 6, 'RTG Crane Code', tbl_header_fmt)
            worksheet.write(start_r_b7, 7, 'Total Moves', tbl_header_fmt)
            for idx, row in summary_rtg.iterrows():
                worksheet.write(start_r_b7+1+idx, 6, f" {row['RTG Crane']}", cell_text_fmt)
                worksheet.write(start_r_b7+1+idx, 7, row['Moves'], cell_num_fmt)

            # TỰ ĐỘNG KHÓA ĐỘ RỘNG CỘT (Đảm bảo chữ hiển thị trọn vẹn, không dính lỗi ###)
            worksheet.set_column('A:A', 26)
            worksheet.set_column('B:B', 14)
            worksheet.set_column('C:C', 4)  # Cột trống tạo khoảng cách an toàn giữa các bảng
            worksheet.set_column('D:D', 26)
            worksheet.set_column('E:E', 14)
            worksheet.set_column('F:F', 4)  # Cột trống tạo khoảng cách an toàn
            worksheet.set_column('G:G', 26)
            worksheet.set_column('H:H', 14)

            # --- CHÈN BIỂU ĐỒ TRỰC QUAN ĐÚNG FORM VỊ TRÍ GẦN KPI TỔNG TRÊN CÙNG ---
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'name':       'Volume',
                'categories': f'=\'SUMMARY REPORT\'!$A$12:$A${end_r_b1}',
                'values':     f'=\'SUMMARY REPORT\'!$B$12:$B${end_r_b1}',
                'data_labels': {'value': True, 'position': 'outside_end'},
                'fill':       {'color': '#4F81BD'},
                'border':     {'color': '#305496'}
            })
            chart.set_title({'name': 'Operational Move Kind Structure', 'name_font': {'name': font_family, 'size': 11, 'bold': True}})
            chart.set_legend({'none': True})
            chart.set_size({'width': 500, 'height': 230})
            
            # Đặt vị trí biểu đồ nằm ngay bên phải của khối KPI tổng (Bắt đầu từ ô D4)
            worksheet.insert_chart('D4', chart)

        # 4. TRẢ KẾT QUẢ ĐỂ NGƯỜI DÙNG TẢI FILE TRỰC TIẾP TỪ WEB
        st.markdown("---")
        st.subheader("📊 Xem trước KPIs nhanh ca trực")
        w_col1, w_col2, w_col3 = st.columns(3)
        w_col1.metric("Tổng sản lượng", f"{total_moves} Moves")
        w_col2.metric("Thời gian hoạt động thực tế", f"{round(total_hours, 1)} Giờ")
        w_col3.metric("Năng suất khai thác tổng", f"{round(net_productivity, 1)} Moves/Giờ")
        
        st.markdown("###")
        st.download_button(
            label="📥 TẢI XUỐNG FILE SHIFT REPORT CHUẨN ĐỊNH DẠNG D1",
            data=output_buffer.getvalue(),
            file_name=f"SHIFT_REPORT_{datetime.now().strftime('%Y-%m-%d')}_D1.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi cấu trúc khi cố gắng dựng lại định dạng D1: {str(e)}")