from __future__ import annotations

import re
from html import escape
from io import BytesIO
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


APP_VERSION = "V1.2.9"
TOTAL_ROWS_PLACEHOLDER = "35334"
DEFAULT_N4_SAMPLE_PATH = Path("docs/RawData_SHIFT_2026-05-30_D1.xlsx")

MAIN_TABS = [
    "📊 DASHBOARD",
    "DATA GỐC (LIST)",
    "TÀU & SÀ LAN",
    "REPORT",
    "CÀI ĐẶT",
    "NHẬT KÝ (LOGS)",
    "DELAY",
]

KPI_DEFAULTS = {
    "GMPH": 32,
    "AIT": 15,
    "AIT2": 20,
    "DIT": 65,
    "TTT": 25,
    "BOE": 40,
}

CRANE_GROUPS = {
    "QC": ["QC01", "QC02", "QC03", "QC04", "QC05", "QC06", "QC07"],
    "TC": ["TC15", "TC16", "TC17", "TC18", "TC19", "TC20", "TC21"],
    "HC": ["HC01", "HC02", "HC03", "HC05", "HC06", "HC08"],
}

DEFAULT_DELAY_CODES = [
    {
        "code": "00",
        "group": "Operation milestones Code 0X",
        "name": "First Move date/time (HC, gearbox) - (ngày / thời gian cho nắp hầm / thùng gù đầu tiên dỡ xuống)",
        "mode": "CODE 0X",
        "deduct": False,
        "source_row": 7,
    },
    {
        "code": "01",
        "group": "Operation milestones Code 0X",
        "name": "First Container (container đầu tiên)",
        "mode": "CODE 0X",
        "deduct": False,
        "source_row": 8,
    },
    {
        "code": "02",
        "group": "Operation milestones Code 0X",
        "name": "Last Container (container cuối cùng)",
        "mode": "CODE 0X",
        "deduct": False,
        "source_row": 9,
    },
    {
        "code": "03",
        "group": "Operation milestones Code 0X",
        "name": "Last Move date/time (HC, gearbox) (ngày / thời gian cho nắp hầm / thùng gù cuối cùng xếp lên tàu)",
        "mode": "CODE 0X",
        "deduct": False,
        "source_row": 10,
    },
    {
        "code": "21",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Gantry Fault (lỗi gantry)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 13,
    },
    {
        "code": "22",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Trolley Fault (lỗi Trolley)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 14,
    },
    {
        "code": "23",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Hoist Fault (lỗi Hoist)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 15,
    },
    {
        "code": "24",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Spreader Fault (lỗi ngáng chụp)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 16,
    },
    {
        "code": "25",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Boom Up/Down Fault (lỗi nâng/hạ boom)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 17,
    },
    {
        "code": "26",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Power Fault (lỗi nguồn)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 18,
    },
    {
        "code": "27",
        "group": "Crane Breakdown delays Code 2X",
        "name": "Spreader Replace (thay ngáng chụp)",
        "mode": "CODE 2X",
        "deduct": False,
        "source_row": 19,
    },
    {
        "code": "31",
        "group": "Operational Delays Code 3X/4X",
        "name": "Crane Sequence Changed (thay đổi thứ tự làm việc của QC)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 22,
    },
    {
        "code": "32",
        "group": "Operational Delays Code 3X/4X",
        "name": "Lashing/Unlashing (chằng/tháo/ dây chằng buộc, tháo dây gù)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 23,
    },
    {
        "code": "32A",
        "group": "Operational Delays Code 3X/4X",
        "name": "Delay due to no lasher available for unlashing at high tiers (Chờ do lasher chưa sẵn sàng lên giật gù ở tier cao)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 24,
    },
    {
        "code": "33",
        "group": "Operational Delays Code 3X/4X",
        "name": "Crane Clash (QC choán vị trí làm việc)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 25,
    },
    {
        "code": "34",
        "group": "Operational Delays Code 3X/4X",
        "name": "Boom Up/Down across accomodation (Boom nâng hạ qua khoang lái)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 26,
    },
    {
        "code": "35",
        "group": "Operational Delays Code 3X/4X",
        "name": "Yard CHE breakdown (thiết bị làm việc trong bãi container (RTG/RS/FL) bị hỏng)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 27,
    },
    {
        "code": "36",
        "group": "Operational Delays Code 3X/4X",
        "name": "Hatch Cover Move (nâng hạ nắp hầm)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 28,
    },
    {
        "code": "37",
        "group": "Operational Delays Code 3X/4X",
        "name": "Yard rehandle (sắp xếp lại trong bãi container)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 29,
    },
    {
        "code": "38",
        "group": "Operational Delays Code 3X/4X",
        "name": "Yard clash (xe tải/RTG bị nghẽn trong bãi container)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 30,
    },
    {
        "code": "39",
        "group": "Operational Delays Code 3X/4X",
        "name": "Jammed Twistlock (discharge/loading) (dính gù khi dỡ/xếp container lên tàu)",
        "mode": "CODE 3X",
        "deduct": False,
        "source_row": 31,
    },
    {
        "code": "40",
        "group": "Operational Delays Code 3X/4X",
        "name": "HHT / VMT Malfunction (Handheld/VMT bị lỗi)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 32,
    },
    {
        "code": "41",
        "group": "Operational Delays Code 3X/4X",
        "name": "Gear box move (dời thùng gù khi đang discharge/ load conts)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 33,
    },
    {
        "code": "42",
        "group": "Operational Delays Code 3X/4X",
        "name": "QC operator hot seat change (QCO thay ca nóng)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 34,
    },
    {
        "code": "43",
        "group": "Operational Delays Code 3X/4X",
        "name": "Wrongly loaded/discharged container number or container position (Xếp/dỡ container sai số container hoặc sai vị trí)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 35,
    },
    {
        "code": "44",
        "group": "Operational Delays Code 3X/4X",
        "name": "Wrongl ISO Code, couldnot close HC properly (Không đóng được nắp hầm tàu vì sai ISO Code)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 36,
    },
    {
        "code": "45",
        "group": "Operational Delays Code 3X/4X",
        "name": "Improper stacking container on board (Loading, twistlocks are not engaged properly), need to be corrected (Xếp container lên tàu chưa vào gù, phải sửa lại)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 37,
    },
    {
        "code": "46",
        "group": "Operational Delays Code 3X/4X",
        "name": "Containers sent to QCs in wrong sequence, wait for the correct ones (Dừng chờ do container ra sai trình tự)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 38,
    },
    {
        "code": "47",
        "group": "Operational Delays Code 3X/4X",
        "name": "Waiting for loading plan (Chờ kế hoạch load)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 39,
    },
    {
        "code": "48",
        "group": "Operational Delays Code 3X/4X",
        "name": "Overload fault - due to QCO's skill (lỗi quá tải - do kỹ năng của QCO)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 40,
    },
    {
        "code": "49",
        "group": "Operational Delays Code 3X/4X",
        "name": "Twistlocks input when loading - wrong twistlock type putting, not put twistlock when needed and put twistlock when not needed (Lỗi lắp và tháo gù - sai loại gù, quên lắp gù, lắp thừa gù)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 41,
    },
    {
        "code": "49A",
        "group": "Operational Delays Code 3X/4X",
        "name": "Corner casting deformed (Loading, hard to put twistlock or slinging requirement) (Lỗ gù của container bị biến dạng, khó lắp gù hoặc phải dùng cáp để xếp dỡ container)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 42,
    },
    {
        "code": "49B",
        "group": "Operational Delays Code 3X/4X",
        "name": "Other - explain (khác - giải thích rõ)",
        "mode": "CODE 4X",
        "deduct": False,
        "source_row": 43,
    },
    {
        "code": "51",
        "group": "Deduction Delays Code 5X",
        "name": "Gang at other vessel - Actual time (When gang within timeframe works on another vessel)/ (Chuyển gang sang làm tàu khác)",
        "mode": "CODE 5X",
        "deduct": True,
        "source_row": 46,
    },
    {
        "code": "52",
        "group": "Deduction Delays Code 5X",
        "name": "Special Cargo Handling / OOG (làm việc với hàng đặc biệt / quá khổ)",
        "mode": "CODE 5X",
        "deduct": True,
        "source_row": 47,
    },
    {
        "code": "53",
        "group": "Deduction Delays Code 5X",
        "name": "Scheduled breaks - Fixed time (Where entire crane stops working)/ (Dừng khai thác có kế hoạch trước) 53.1. Bảo trì (cẩu/hệ thống) có kế hoạch trước 53.2. Test ngáng đầu ca 53.3. Thời gian Tech yêu cầu QC ngừng hoạt động để sửa chữa trong ca 53.4. Thời gian để sửa chữa khi QC bị hư - được xác nhận bởi Tech (Tối đa 30' tính từ lúc Disp báo Tech): Ví dụ mục 53.4 như sau: - QC02 bị hư lúc 0810: + nếu trong vòng 30’ kể từ 0810 (tức là đến 0840) mà Tech chưa đưa ra xác nhận cần bao nhiêu thời gian thì delay bắt đầu tính từ 0841 + nếu đến 0820, Tech xác nhận cần 3h để sửa, thì delay bắt đầu tính từ 0821 53.5. Thời gian ngừng có kế hoạch phục vụ cho sự kiện cụ thể",
        "mode": "CODE 5X",
        "deduct": True,
        "source_row": 48,
    },
    {
        "code": "54",
        "group": "Deduction Delays Code 5X",
        "name": "Weather (Due to safety, cranes must stop - i.e, wind alarm (SOP) and/or heavy rain)/ Dừng do thời tiết xấu, cẩu phải dừng do gió to (SOP), mưa lớn không thể làm việc",
        "mode": "CODE 5X",
        "deduct": True,
        "source_row": 49,
    },
    {
        "code": "55",
        "group": "Deduction Delays Code 5X",
        "name": "Power Failure (mất nguồn điện - do EVN)",
        "mode": "CODE 5X",
        "deduct": True,
        "source_row": 50,
    },
    {
        "code": "61",
        "group": "Emergency Delays Code 6X",
        "name": "Accident (tai nạn)",
        "mode": "CODE 6X",
        "deduct": False,
        "source_row": 53,
    },
    {
        "code": "62",
        "group": "Emergency Delays Code 6X",
        "name": "Power Failure (mất nguồn điện - do CMIT)",
        "mode": "CODE 6X",
        "deduct": False,
        "source_row": 54,
    },
    {
        "code": "63",
        "group": "Emergency Delays Code 6X",
        "name": "TOS failure (lỗi hệ thống thông tin: máy chủ, phần mềm truy cập, vv..)",
        "mode": "CODE 6X",
        "deduct": False,
        "source_row": 55,
    },
    {
        "code": "64",
        "group": "Emergency Delays Code 6X",
        "name": "Other emergency stoppage - explain (Dừng khẩn cấp khác - giải thích)",
        "mode": "CODE 6X",
        "deduct": False,
        "source_row": 56,
    },
    {
        "code": "71",
        "group": "Other Delays Code 7X",
        "name": "Other Delays Code 7X (thời gian ngừng do những lý do khác, VD: Tàu cập/ rời cầu cảng)",
        "mode": "CODE 7X",
        "deduct": False,
        "source_row": 58,
    },
]

DEFAULT_VERSION_LOG = [
    {
        "time": "30.05.2026 LÚC 17:45",
        "detail": "Dựng lại app shell mới: header trạng thái, toolbar vận hành và 7 tab chính.",
    },
    {
        "time": "30.05.2026 LÚC 18:10",
        "detail": "Gắn module cho Lưu thay đổi, Delay, Ngày/Ca, Auto, Upload, Hướng dẫn và Phiên bản.",
    },
    {
        "time": "12.03.2026 LÚC 19:00",
        "detail": "Sửa lỗi bảng PDF tràn trang, đồng bộ cột ghi chú và margin khi xuất báo cáo.",
    },
    {
        "time": "12.03.2026 LÚC 17:30",
        "detail": "Delay: min luôn đồng bộ với timeline thực, code 5X được tính deduct.",
    },
    {
        "time": "11.03.2026 LÚC 10:00",
        "detail": "Thêm chức năng nhập mốc delay theo STS Quay và đăng nhập DWC theo cẩu.",
    },
]

REQUIRED_N4_COLUMNS = [
    ("UNIT NBR", "Số container"),
    ("MOVE KIND", "Loại lệnh"),
    ("CARRIER VISIT", "Mã chuyến tàu/sà lan"),
    ("STS QUAY", "Tên cẩu bờ"),
    ("TIME COMPLETED", "Thời gian hoàn tất"),
    ("TIME OF FETCH", "Thời gian gắp hàng"),
]


def main() -> None:
    st.set_page_config(
        page_title="SHIFT REPORT",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_state()
    inject_css()
    render_top_status()
    render_main_toolbar()

    tab_dashboard, tab_raw, tab_carriers, tab_report, tab_settings, tab_logs, tab_delay = st.tabs(MAIN_TABS)

    with tab_dashboard:
        render_dashboard()
    with tab_raw:
        render_raw_data()
    with tab_carriers:
        render_carriers()
    with tab_report:
        render_report()
    with tab_settings:
        render_settings()
    with tab_logs:
        render_logs()
    with tab_delay:
        render_delay()


def init_state() -> None:
    now = datetime.now()
    inferred_date, inferred_shift = infer_report_context_from_clock(now)

    defaults: dict[str, Any] = {
        "report_date": inferred_date,
        "shift_code": inferred_shift,
        "auto_shift": False,
        "uploaded_file_meta": None,
        "raw_data": None,
        "dashboard_data": None,
        "upload_error": "",
        "pending_changes": [],
        "audit_logs": [],
        "delay_markers": [],
        "selected_dwc_crane": "",
        "delay_marker_crane": "QC01",
        "delay_marker_date": inferred_date,
        "delay_marker_time": now.replace(second=0, microsecond=0).time(),
        "delay_hashtag": "#TEST NGANG",
        "delay_remark": "",
        "kpi_targets": KPI_DEFAULTS.copy(),
        "last_save_time": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.session_state.setdefault("report_date_widget", st.session_state.report_date)
    st.session_state.setdefault("shift_code_widget", st.session_state.shift_code)
    st.session_state.setdefault("delay_date_widget", st.session_state.delay_marker_date)
    st.session_state.setdefault("delay_time_widget", st.session_state.delay_marker_time)
    for kpi, value in st.session_state.kpi_targets.items():
        st.session_state.setdefault(f"kpi_{kpi}", value)


def render_top_status() -> None:
    now = datetime.now()
    uploaded = st.session_state.get("uploaded_file_meta")
    try:
        active_df, _source_label = get_active_n4_data()
        total_rows = f"{len(active_df):,}" if not active_df.empty else TOTAL_ROWS_PLACEHOLDER
    except Exception:
        total_rows = TOTAL_ROWS_PLACEHOLDER
    data_until = "REALTIME" if uploaded else "N4 SAMPLE"
    synced_label = st.session_state.get("last_save_time") or now
    st.markdown(
        f"""
        <div class="top-status">
            <div class="status-spacer"></div>
            <div class="status-item"><span class="dot dot-blue"></span> SYNCED: <strong>{synced_label:%H:%M:%S %d/%m/%Y}</strong></div>
            <div class="status-sep"></div>
            <div class="status-item">📦 TOTAL: <strong>{total_rows}</strong></div>
            <div class="status-sep"></div>
            <div class="status-item"><span class="dot dot-green"></span> DATA UNTIL: <strong>{data_until}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_main_toolbar() -> None:
    pending_count = len(st.session_state.pending_changes)
    save_label = f"💾 LƯU THAY ĐỔI ({pending_count})" if pending_count else "💾 LƯU THAY ĐỔI"
    auto_label = "AUTO ON" if st.session_state.auto_shift else "AUTO"
    date_label = st.session_state.report_date.strftime("%d/%m/%Y")

    st.markdown('<div class="toolbar-band">', unsafe_allow_html=True)
    cols = st.columns([1.0, 0.72, 1.28, 0.26, 0.95, 0.56, 0.26, 0.68, 0.82, 0.94, 0.7, 1.35])
    with cols[0]:
        if st.button(save_label, key="btn_save_changes", type="primary", use_container_width=True):
            render_save_changes_dialog()
    with cols[1]:
        if st.button("⏱ DELAY", key="btn_delay", use_container_width=True):
            render_delay_dialog()
    with cols[2]:
        st.markdown(
            """
            <div class="brand">
                <div class="brand-title">SHIFT REPORT</div>
                <div class="brand-subtitle">TSV MODE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cols[3]:
        if st.button("‹", key="report_prev_day", use_container_width=True):
            set_report_date(st.session_state.report_date - timedelta(days=1), "Lùi ngày báo cáo")
            st.rerun()
    with cols[4]:
        st.markdown(f'<div class="toolbar-mini-label">NGÀY · {date_label}</div>', unsafe_allow_html=True)
        st.date_input(
            "Ngày",
            key="report_date_widget",
            format="DD/MM/YYYY",
            on_change=on_report_date_changed,
            label_visibility="collapsed",
        )
    with cols[6]:
        if st.button("›", key="report_toggle_shift", use_container_width=True):
            toggle_report_shift()
            st.rerun()
    with cols[5]:
        st.markdown(f'<div class="toolbar-mini-label accent">CA · {st.session_state.shift_code}</div>', unsafe_allow_html=True)
        st.selectbox("Ca", ["D1", "D2"], key="shift_code_widget", on_change=on_shift_changed, label_visibility="collapsed")
    with cols[7]:
        if st.button(auto_label, key="btn_auto_shift", use_container_width=True):
            st.session_state.auto_shift = True
            apply_auto_report_context("Auto cập nhật ngày/ca")
            st.rerun()
    with cols[8]:
        with st.popover("⬆ UPLOAD", use_container_width=True):
            st.caption("Chọn file dữ liệu xuất từ N4. Bước này mới lưu metadata, phần parse dữ liệu sẽ làm ở tab Data gốc.")
            uploaded_file = st.file_uploader(
                "File N4",
                accept_multiple_files=False,
                label_visibility="collapsed",
                key="n4_file_uploader",
            )
            if uploaded_file is not None:
                handle_uploaded_file(uploaded_file)
                if st.session_state.upload_error:
                    st.error(f"Không đọc được file: {st.session_state.upload_error}")
                else:
                    rows = st.session_state.uploaded_file_meta.get("rows", 0)
                    st.success(f"Đã nhận file: {uploaded_file.name} · {rows:,} dòng")
    with cols[9]:
        if st.button("⊕ HƯỚNG DẪN", key="btn_guide", use_container_width=True):
            render_guide_dialog()
    with cols[10]:
        if st.button(APP_VERSION, key="btn_version", use_container_width=True):
            render_version_dialog()
    with cols[11]:
        dwc = st.session_state.selected_dwc_crane or "CHƯA LINK"
        st.markdown(
            f"""
            <div class="toolbar-right">
                <span class="live-dot"></span> LIVE (FULL RAW)
                <span class="linked-pill">🔗 {dwc}<br><small>RELOAD FULL</small></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard() -> None:
    st.markdown('<section class="tab-shell dashboard-shell">', unsafe_allow_html=True)
    df, source_label = get_active_n4_data()
    if df.empty:
        st.warning("Chưa đọc được dữ liệu N4. Hãy kiểm tra file mẫu hoặc upload file mới.")
        st.markdown("</section>", unsafe_allow_html=True)
        return

    dashboard = build_dashboard_bundle(df, st.session_state.report_date)
    st.session_state.dashboard_data = dashboard

    render_dashboard_header(source_label, dashboard)
    render_dashboard_kpis(dashboard)

    chart_col, mix_col, delay_col = st.columns([1.65, 0.9, 0.95])
    with chart_col:
        st.markdown("#### Sản lượng theo giờ")
        hourly = dashboard["hourly"]
        if hourly.empty:
            st.info("Chưa đủ thời gian để dựng biểu đồ.")
        else:
            st.bar_chart(hourly, use_container_width=True, height=280)
    with mix_col:
        st.markdown("#### Cơ cấu hoạt động")
        render_mix_panel(dashboard)
    with delay_col:
        st.markdown("#### Delay watch")
        render_delay_watch_panel(dashboard)

    crane_col, carrier_col = st.columns([1.15, 1.25])
    with crane_col:
        st.markdown("#### Crane performance")
        st.dataframe(dashboard["crane_stats"], use_container_width=True, hide_index=True, height=310)
    with carrier_col:
        st.markdown("#### Live carrier list")
        st.dataframe(dashboard["carrier_stats"], use_container_width=True, hide_index=True, height=310)

    st.markdown("</section>", unsafe_allow_html=True)


def get_active_n4_data() -> tuple[pd.DataFrame, str]:
    if st.session_state.raw_data is not None:
        uploaded = st.session_state.uploaded_file_meta or {}
        return st.session_state.raw_data.copy(), f"UPLOAD · {uploaded.get('name', 'N4 file')}"

    if DEFAULT_N4_SAMPLE_PATH.exists():
        stat = DEFAULT_N4_SAMPLE_PATH.stat()
        sample_df = load_n4_dataframe_from_path(str(DEFAULT_N4_SAMPLE_PATH), stat.st_mtime)
        return sample_df.copy(), f"GIẢ ĐỊNH N4 · {DEFAULT_N4_SAMPLE_PATH.name}"

    return pd.DataFrame(), "CHƯA CÓ DỮ LIỆU"


@st.cache_data(show_spinner=False)
def load_n4_dataframe_from_path(path_text: str, _mtime: float) -> pd.DataFrame:
    path = Path(path_text)
    return read_n4_file_bytes(path.name, path.read_bytes())


def read_n4_file_bytes(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    suffix = Path(file_name).suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return read_n4_excel(file_bytes)
    if suffix in {".csv", ".txt", ".tsv"}:
        return read_n4_csv(file_bytes, sep="\t" if suffix == ".tsv" else None)
    try:
        return read_n4_excel(file_bytes)
    except Exception:
        return read_n4_csv(file_bytes)


def read_n4_excel(file_bytes: bytes) -> pd.DataFrame:
    workbook = pd.ExcelFile(BytesIO(file_bytes))
    best: pd.DataFrame | None = None
    best_score = -1
    for sheet_name in workbook.sheet_names:
        raw = pd.read_excel(workbook, sheet_name=sheet_name, header=None, dtype=object)
        candidate = table_from_raw_rows(raw)
        score = score_n4_columns(candidate.columns)
        if score > best_score:
            best = candidate
            best_score = score
    if best is None or best.empty:
        raise ValueError("Không tìm thấy bảng dữ liệu N4 trong workbook.")
    return normalize_n4_columns(best)


def read_n4_csv(file_bytes: bytes, sep: str | None = None) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin1"):
        try:
            raw = pd.read_csv(BytesIO(file_bytes), header=None, dtype=object, encoding=encoding, sep=sep)
            return normalize_n4_columns(table_from_raw_rows(raw))
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Không đọc được file CSV/TXT: {last_error}")


def table_from_raw_rows(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    header_index = 0
    for idx, row in raw.iterrows():
        values = [clean_column_name(value) for value in row.tolist()]
        score = score_n4_columns(values)
        if score >= 3:
            header_index = int(idx)
            break

    header = [clean_column_name(value) or f"Column {pos + 1}" for pos, value in enumerate(raw.iloc[header_index].tolist())]
    data = raw.iloc[header_index + 1 :].copy()
    data.columns = header
    data = data.dropna(how="all").reset_index(drop=True)
    return data


def score_n4_columns(columns: Any) -> int:
    normalized = {clean_column_name(col).lower() for col in columns}
    expected = {
        "unit nbr",
        "move kind",
        "carrier visit",
        "sts quay",
        "time sts quay",
        "time completed",
        "time of fetch",
    }
    return len(normalized & expected)


def normalize_n4_columns(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df.columns = [clean_column_name(col) for col in clean_df.columns]
    clean_df = clean_df.loc[:, [bool(col and not col.startswith("Column ")) or clean_df[col].notna().any() for col in clean_df.columns]]
    for column in clean_df.columns:
        if clean_df[column].dtype == object:
            clean_df[column] = clean_df[column].apply(lambda value: value.strip() if isinstance(value, str) else value)
    if "Unit Nbr" in clean_df.columns:
        clean_df = clean_df[clean_df["Unit Nbr"].astype(str).str.upper().ne("UNIT NBR")]
    return clean_df.dropna(how="all").reset_index(drop=True)


def clean_column_name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def build_dashboard_bundle(df: pd.DataFrame, report_date: date) -> dict[str, Any]:
    work = prepare_dashboard_frame(df, report_date)
    total_moves = len(work)
    productive = int(work["_activity"].isin(["LOAD", "DISCHARGE"]).sum())
    vessel_moves = int(work["_type"].eq("VESSEL").sum())
    barge_moves = int(work["_type"].eq("BARGE").sum())
    gate_moves = int(work["_activity"].eq("GATE").sum())
    yard_moves = int(work["_activity"].eq("YARD").sum())
    active_sts = int(work.loc[work["_crane"].str.startswith("QC", na=False), "_crane"].nunique())
    gap_delay = int((work["_gap_delay"] > 3).sum())
    gross_hours = calculate_gross_crane_hours(work)
    gmph = productive / gross_hours if gross_hours else 0

    return {
        "source_rows": total_moves,
        "productive": productive,
        "vessel_moves": vessel_moves,
        "barge_moves": barge_moves,
        "gate_moves": gate_moves,
        "yard_moves": yard_moves,
        "active_sts": active_sts,
        "gap_delay": gap_delay,
        "gross_hours": gross_hours,
        "gmph": gmph,
        "first_move": format_time_value(work["_time"].min()),
        "last_move": format_time_value(work["_time"].max()),
        "hourly": make_hourly_chart_data(work),
        "mix": make_activity_mix(work),
        "delay_watch": make_delay_watch(work),
        "crane_stats": make_crane_stats(work),
        "carrier_stats": make_carrier_stats(work),
    }


def prepare_dashboard_frame(df: pd.DataFrame, report_date: date) -> pd.DataFrame:
    work = df.copy()
    work["_move_kind"] = get_series(work, "Move Kind").astype(str).str.upper().str.strip()
    work["_carrier"] = get_series(work, "Carrier Visit").astype(str).str.strip().replace({"": "UNKNOWN", "nan": "UNKNOWN"})
    work["_type"] = get_series(work, "LOAI PTVT").astype(str).str.upper().str.strip()
    berth_type = get_series(work, "LOAI CAU BEN").astype(str).str.upper().str.strip()
    work.loc[work["_type"].isin(["", "NAN"]) & berth_type.eq("GATE"), "_type"] = "GATE"
    work.loc[work["_type"].isin(["", "NAN"]) & work["_move_kind"].isin(["GATE IN", "GATE OUT", "DELIVERY", "RECEIVAL"]), "_type"] = "GATE"
    work["_type"] = work["_type"].replace({"": "OTHER", "NAN": "OTHER"})
    work["_crane"] = get_series(work, "STS QUAY").astype(str).str.upper().str.strip().replace({"NAN": ""})
    work["_crane"] = work.apply(infer_crane_from_row, axis=1)
    time_source = get_first_available_series(work, ["Time STS QUAY", "Time Completed", "Time of Fetch"])
    work["_time"] = time_source.apply(lambda value: parse_n4_timestamp(value, report_date))
    work["_gap_delay"] = pd.to_numeric(get_series(work, "Gap Delay"), errors="coerce").fillna(0)
    work["_activity"] = work.apply(classify_activity, axis=1)
    work["_hour"] = work["_time"].dt.strftime("%H:00").fillna("NO TIME")
    return work


def get_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([""] * len(df), index=df.index)


def get_first_available_series(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series([pd.NA] * len(df), index=df.index, dtype=object)
    for column in columns:
        if column in df.columns:
            result = result.where(result.notna(), df[column])
    return result


def infer_crane_from_row(row: pd.Series) -> str:
    if row["_crane"]:
        return row["_crane"]
    for column in ["Put CHE Name", "Fetch CHE Name", "Carry CHE Name", "STS Yard", "STS Carry"]:
        value = str(row.get(column, "") or "").upper().strip()
        if value.startswith("QC"):
            return value
    return ""


def classify_activity(row: pd.Series) -> str:
    kind = row["_move_kind"]
    if "DISCH" in kind:
        return "DISCHARGE"
    if "LOAD" in kind:
        return "LOAD"
    if kind in {"GATE IN", "GATE OUT", "DELIVERY", "RECEIVAL"} or row["_type"] == "GATE":
        return "GATE"
    if "YARD" in kind or "SHIFT" in kind:
        return "YARD"
    return "OTHER"


def parse_n4_timestamp(value: Any, report_date: date) -> pd.Timestamp:
    if value is None or pd.isna(value):
        return pd.NaT
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value)
    text = str(value).strip()
    match = re.match(r"^(\d{1,2})/(\d{1,2}):(\d{2})$", text)
    if match:
        day, hour, minute = map(int, match.groups())
        try:
            return pd.Timestamp(datetime(report_date.year, report_date.month, day, hour, minute))
        except ValueError:
            return pd.NaT
    return pd.to_datetime(text, errors="coerce")


def calculate_gross_crane_hours(work: pd.DataFrame) -> float:
    qc = work[work["_crane"].str.startswith("QC", na=False) & work["_time"].notna()].copy()
    if qc.empty:
        return 0.0
    hours = []
    for _, group in qc.groupby("_crane"):
        span = (group["_time"].max() - group["_time"].min()).total_seconds() / 3600
        hours.append(max(span, 1 / 60))
    return round(float(sum(hours)), 2)


def make_hourly_chart_data(work: pd.DataFrame) -> pd.DataFrame:
    chart_work = work[work["_time"].notna()].copy()
    if chart_work.empty:
        return pd.DataFrame()
    chart_work["_hour_sort"] = chart_work["_time"].dt.floor("h")
    pivot = (
        chart_work.groupby(["_hour_sort", "_activity"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
        .rename_axis(None, axis=1)
    )
    pivot.index = pivot.index.strftime("%H:00")
    return pivot.reindex(columns=["LOAD", "DISCHARGE", "GATE", "YARD", "OTHER"], fill_value=0)


def make_activity_mix(work: pd.DataFrame) -> list[dict[str, Any]]:
    total = max(len(work), 1)
    labels = [("LOAD", "Load"), ("DISCHARGE", "Discharge"), ("GATE", "Gate"), ("YARD", "Yard"), ("OTHER", "Other")]
    return [
        {"key": key, "label": label, "value": int(work["_activity"].eq(key).sum()), "pct": int(work["_activity"].eq(key).sum() / total * 100)}
        for key, label in labels
    ]


def make_delay_watch(work: pd.DataFrame) -> dict[str, Any]:
    delayed = work[work["_gap_delay"] > 3].copy()
    if delayed.empty:
        top = pd.DataFrame(columns=["STS", "Gap >3P"])
    else:
        top = (
            delayed.groupby("_crane")
            .size()
            .reset_index(name="Gap >3P")
            .rename(columns={"_crane": "STS"})
            .sort_values("Gap >3P", ascending=False)
            .head(5)
        )
    return {
        "rows": int(len(delayed)),
        "max_gap": float(delayed["_gap_delay"].max()) if not delayed.empty else 0,
        "manual": len(st.session_state.delay_markers),
        "top": top,
    }


def make_crane_stats(work: pd.DataFrame) -> pd.DataFrame:
    qc = work[work["_crane"].str.startswith("QC", na=False)].copy()
    if qc.empty:
        return pd.DataFrame(columns=["STS", "Moves", "Load", "Disch", "Gap >3P", "Carrier", "First", "Last", "GMPH"])
    rows = []
    for crane, group in qc.groupby("_crane"):
        productive = int(group["_activity"].isin(["LOAD", "DISCHARGE"]).sum())
        span = 0.0
        if group["_time"].notna().any():
            span = max((group["_time"].max() - group["_time"].min()).total_seconds() / 3600, 1 / 60)
        rows.append(
            {
                "STS": crane,
                "Moves": int(len(group)),
                "Load": int(group["_activity"].eq("LOAD").sum()),
                "Disch": int(group["_activity"].eq("DISCHARGE").sum()),
                "Gap >3P": int((group["_gap_delay"] > 3).sum()),
                "Carrier": int(group["_carrier"].nunique()),
                "First": format_time_value(group["_time"].min()),
                "Last": format_time_value(group["_time"].max()),
                "GMPH": round(productive / span, 1) if span else 0,
            }
        )
    return pd.DataFrame(rows).sort_values(["Moves", "STS"], ascending=[False, True])


def make_carrier_stats(work: pd.DataFrame) -> pd.DataFrame:
    carrier_work = work[work["_carrier"].ne("UNKNOWN")].copy()
    if carrier_work.empty:
        return pd.DataFrame(columns=["Carrier", "Type", "Moves", "Load", "Disch", "STS", "Gap >3P", "First", "Last", "Status"])
    max_time = carrier_work["_time"].max()
    rows = []
    for (carrier, transport_type), group in carrier_work.groupby(["_carrier", "_type"]):
        last_time = group["_time"].max()
        active = pd.notna(max_time) and pd.notna(last_time) and (max_time - last_time) <= pd.Timedelta(minutes=30)
        rows.append(
            {
                "Carrier": carrier,
                "Type": transport_type,
                "Moves": int(len(group)),
                "Load": int(group["_activity"].eq("LOAD").sum()),
                "Disch": int(group["_activity"].eq("DISCHARGE").sum()),
                "STS": ", ".join(sorted(crane for crane in group["_crane"].dropna().unique() if crane)[:3]),
                "Gap >3P": int((group["_gap_delay"] > 3).sum()),
                "First": format_time_value(group["_time"].min()),
                "Last": format_time_value(last_time),
                "Status": "ACTIVE" if active else "DONE",
            }
        )
    return pd.DataFrame(rows).sort_values(["Status", "Moves"], ascending=[True, False]).head(18)


def render_dashboard_header(source_label: str, dashboard: dict[str, Any]) -> None:
    st.markdown(
        f"""
        <div class="dashboard-hero">
            <div>
                <div class="dashboard-eyebrow">REALTIME OPERATIONS</div>
                <div class="dashboard-title">DASHBOARD</div>
                <div class="dashboard-subtitle">{escape(source_label)} · {dashboard["first_move"]} → {dashboard["last_move"]}</div>
            </div>
            <div class="dashboard-hero-actions">
                <span>CA {escape(st.session_state.shift_code)}</span>
                <span>{escape(format_date(st.session_state.report_date))}</span>
                <span>{dashboard["active_sts"]} STS</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_kpis(dashboard: dict[str, Any]) -> None:
    cards = [
        ("TOTAL MOVES", format_int(dashboard["source_rows"]), "Dòng dữ liệu N4", "blue"),
        ("PRODUCTIVE", format_int(dashboard["productive"]), "Load + Discharge", "green"),
        ("VESSEL / BARGE", f"{format_int(dashboard['vessel_moves'])} / {format_int(dashboard['barge_moves'])}", "Moves theo loại PTVT", "purple"),
        ("GATE / YARD", f"{format_int(dashboard['gate_moves'])} / {format_int(dashboard['yard_moves'])}", "Cổng và bãi", "cyan"),
        ("GAP > 3P", format_int(dashboard["gap_delay"]), "Delay tiềm năng", "red"),
        ("GMPH", f"{dashboard['gmph']:.1f}", f"Gross crane hours {dashboard['gross_hours']:.1f}", "yellow"),
    ]
    html = ['<div class="dashboard-kpi-grid">']
    for title, value, note, color in cards:
        html.append(
            f"""
            <div class="dashboard-kpi-card {color}">
                <div class="kpi-title">{escape(title)}</div>
                <div class="kpi-value">{escape(value)}</div>
                <div class="kpi-note">{escape(note)}</div>
            </div>
            """
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_mix_panel(dashboard: dict[str, Any]) -> None:
    rows = []
    for item in dashboard["mix"]:
        label = escape(item["label"])
        value = escape(format_int(item["value"]))
        pct = max(0, min(100, int(item["pct"])))
        rows.append(
            f'<div class="mix-row"><div class="mix-label"><span>{label}</span><strong>{value}</strong></div>'
            f'<div class="mix-track"><div style="width:{pct}%"></div></div></div>'
        )
    st.markdown(f'<div class="dashboard-panel">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_delay_watch_panel(dashboard: dict[str, Any]) -> None:
    delay = dashboard["delay_watch"]
    st.markdown(
        f"""
        <div class="dashboard-panel delay-watch">
            <div class="delay-watch-number">{format_int(delay["rows"])}</div>
            <div class="delay-watch-label">mốc gap > 3 phút</div>
            <div class="delay-watch-meta">Max gap: {delay["max_gap"]:.0f} phút · Manual: {delay["manual"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not delay["top"].empty:
        st.dataframe(delay["top"], use_container_width=True, hide_index=True, height=160)


def format_time_value(value: Any) -> str:
    if pd.isna(value):
        return "-"
    return pd.Timestamp(value).strftime("%H:%M")


def format_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return "-"


def render_raw_data() -> None:
    st.markdown('<section class="tab-shell">', unsafe_allow_html=True)
    st.subheader("Data gốc (List)")
    uploaded = st.session_state.uploaded_file_meta
    df, source_label = get_active_n4_data()
    if uploaded:
        st.success(f"File đang chọn: {uploaded['name']} | {format_bytes(uploaded['size'])} | {uploaded['type']}")
    elif not df.empty:
        st.info(f"Đang dùng dữ liệu giả định: {source_label}")
    else:
        st.warning("Chưa có file N4. Nhấn UPLOAD ở thanh công cụ để chọn file.")

    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Tìm kiếm", placeholder="Container, carrier, STS, vị trí...")
    only_delay = c2.checkbox("DELAY > 3P")
    c3.checkbox("HIỆN GIẢM TRỪ (5X)")
    if not df.empty:
        view_df = df.copy()
        if only_delay and "Gap Delay" in view_df.columns:
            view_df = view_df[pd.to_numeric(view_df["Gap Delay"], errors="coerce").fillna(0) > 3]
        if query:
            mask = view_df.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
            view_df = view_df[mask]
        st.dataframe(view_df.head(1000), use_container_width=True, hide_index=True, height=520)
    else:
        st.info("Bước sau sẽ parse Excel/CSV N4 và hiển thị bảng raw list tại đây.")
    st.markdown("</section>", unsafe_allow_html=True)


def render_carriers() -> None:
    st.markdown('<section class="tab-shell">', unsafe_allow_html=True)
    st.subheader("Tàu & Sà lan")
    vessel_tab, barge_tab = st.tabs(["TÀU (VESSELS)", "SÀ LAN (BARGES)"])
    with vessel_tab:
        st.info("Bước sau sẽ dựng bảng tàu: Carrier, cầu bến, total, first/last, GMPH, PMPH, BMPH, status.")
    with barge_tab:
        st.info("Bước sau sẽ dựng bảng sà lan và berth planning.")
    st.markdown("</section>", unsafe_allow_html=True)


def render_report() -> None:
    st.markdown('<section class="tab-shell">', unsafe_allow_html=True)
    st.subheader("Report")
    st.info("Bước sau sẽ dựng Shift Operation Report preview và form nhập personnel/gate/CHE/notes.")
    st.markdown("</section>", unsafe_allow_html=True)


def render_settings() -> None:
    st.markdown('<section class="tab-shell">', unsafe_allow_html=True)
    st.subheader("Cài đặt")
    cols = st.columns(6)
    for col, (label, _default_value) in zip(cols, KPI_DEFAULTS.items()):
        with col:
            st.number_input(
                label,
                min_value=0,
                step=1,
                key=f"kpi_{label}",
                on_change=on_kpi_changed,
                args=(label,),
            )
    st.info("Bước sau sẽ lưu KPI targets, staff list, quyền thao tác và cấu hình hệ thống.")
    st.markdown("</section>", unsafe_allow_html=True)


def render_logs() -> None:
    st.markdown('<section class="tab-shell">', unsafe_allow_html=True)
    st.subheader("Nhật ký (Logs)")
    if st.session_state.audit_logs:
        st.dataframe(pd.DataFrame(st.session_state.audit_logs), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có hoạt động nào được ghi nhận trong phiên này.")
    st.markdown("</section>", unsafe_allow_html=True)


def render_delay() -> None:
    st.markdown('<section class="tab-shell">', unsafe_allow_html=True)
    st.subheader("Delay")
    c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
    c1.selectbox("STS Quay", ["ALL"] + all_cranes())
    c2.selectbox("Filter", ["TẤT CẢ DELAY", "ẨN WAITING", "CHỈ CODE 5X"])
    c3.text_input("Lý do / ghi chú")
    with c4:
        st.write("")
        if st.button("NHẬP MỐC DELAY", key="delay_tab_open", use_container_width=True):
            render_delay_dialog()

    if st.session_state.delay_markers:
        st.dataframe(pd.DataFrame(st.session_state.delay_markers), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có mốc delay nào. Nhấn nút DELAY trên header để nhập mốc theo STS Quay.")
    st.markdown("</section>", unsafe_allow_html=True)


@st.dialog("💾 XÁC NHẬN LƯU THAY ĐỔI", width="small")
def render_save_changes_dialog() -> None:
    pending = st.session_state.pending_changes
    if not pending:
        st.markdown(
            '<div class="dialog-empty">CHƯA CÓ THAY ĐỔI THỦ CÔNG NÀO ĐÁNG CHÚ Ý.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("Danh sách thay đổi đang chờ lưu:")
        st.dataframe(pd.DataFrame(pending), use_container_width=True, hide_index=True)

    cancel_col, save_col = st.columns([1, 1])
    with cancel_col:
        if st.button("HỦY", key="save_dialog_cancel", use_container_width=True):
            st.rerun()
    with save_col:
        if st.button("XÁC NHẬN LƯU", key="save_dialog_confirm", type="primary", use_container_width=True):
            count = len(st.session_state.pending_changes)
            st.session_state.pending_changes = []
            st.session_state.last_save_time = datetime.now()
            add_audit_log("save_changes", f"Đã xác nhận lưu {count} thay đổi.")
            st.toast("Đã lưu thay đổi mới nhất.")
            st.rerun()


@st.dialog("⏱ DELAY", width="large")
def render_delay_dialog() -> None:
    marker_tab, login_tab, code_tab = st.tabs(["Nhập mốc delay", "Đăng nhập DWC", "Danh sách code"])
    with marker_tab:
        st.markdown('<div class="delay-modal-title">NHẬP MỐC DELAY THEO STS QUAY</div>', unsafe_allow_html=True)
        st.caption("Chọn cẩu, thời điểm và một dòng code trong danh sách cuộn bên dưới để gán delay.")

        top_cols = st.columns([1.15, 0.72, 0.35, 0.35, 1.0, 0.35, 0.35, 0.4])
        with top_cols[0]:
            st.selectbox("Cẩu", all_cranes(), key="delay_marker_crane")
        with top_cols[1]:
            st.time_input("Giờ", step=60, key="delay_time_widget", on_change=on_delay_time_changed)
        with top_cols[2]:
            st.write("")
            if st.button("+1'", key="delay_plus_minute", use_container_width=True):
                adjust_delay_time(1)
                st.rerun()
        with top_cols[3]:
            st.write("")
            if st.button("-1'", key="delay_minus_minute", use_container_width=True):
                adjust_delay_time(-1)
                st.rerun()
        with top_cols[4]:
            st.date_input("Ngày", format="DD/MM/YYYY", key="delay_date_widget", on_change=on_delay_date_changed)
        with top_cols[5]:
            st.write("")
            if st.button("+1D", key="delay_plus_day", use_container_width=True):
                adjust_delay_date(1)
                st.rerun()
        with top_cols[6]:
            st.write("")
            if st.button("-1D", key="delay_minus_day", use_container_width=True):
                adjust_delay_date(-1)
                st.rerun()
        with top_cols[7]:
            st.write("")
            st.markdown(
                f'<div class="delay-shift-badge">{delay_shift_label(st.session_state.delay_marker_time)}</div>',
                unsafe_allow_html=True,
            )

        search_cols = st.columns([1.45, 0.8])
        with search_cols[0]:
            query = st.text_input("Lý do delay", placeholder="Gõ code, nhóm hoặc từ khóa...", key="delay_code_query")
        with search_cols[1]:
            st.text_input("Hashtag", key="delay_hashtag")

        filtered_codes = filter_delay_codes(query)

        if filtered_codes:
            code_df = pd.DataFrame(filtered_codes)
            code_df = code_df[["code", "mode", "group", "name", "deduct"]].rename(
                columns={"code": "Code", "mode": "Mode", "group": "Nhóm", "name": "Lý do", "deduct": "Deduct"}
            )
            st.caption(f"Danh sách code ({len(filtered_codes)}). Chọn một dòng để gán cho {st.session_state.delay_marker_crane}.")
            code_event = st.dataframe(
                code_df,
                key="delay_code_scroll_list",
                height=220,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Code": st.column_config.TextColumn("Code", width="small"),
                    "Mode": st.column_config.TextColumn("Mode", width="small"),
                    "Nhóm": st.column_config.TextColumn("Nhóm", width="medium"),
                    "Lý do": st.column_config.TextColumn("Lý do", width="large"),
                    "Deduct": st.column_config.CheckboxColumn("Deduct", width="small", disabled=True),
                },
            )
            selected_rows = list(getattr(getattr(code_event, "selection", None), "rows", []) or [])
            selected_code = filtered_codes[selected_rows[0]] if selected_rows else None
            if selected_code:
                st.markdown(
                    f"""
                    <div class="delay-selected-code">
                        <strong>Đang chọn:</strong> CODE {selected_code["code"]} - {selected_code["name"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="delay-selected-code muted">Chưa chọn code. Click một dòng trong danh sách cuộn.</div>',
                    unsafe_allow_html=True,
                )

            bottom_cols = st.columns([1.6, 0.75])
            with bottom_cols[0]:
                st.text_area("Ghi chú thêm", key="delay_remark", height=68, label_visibility="collapsed")
            with bottom_cols[1]:
                st.write("")
                if st.button(
                    "✓ GÁN LÝ DO DELAY",
                    key="assign_delay_reason",
                    type="primary",
                    use_container_width=True,
                    disabled=selected_code is None,
                ):
                    if selected_code is None:
                        st.warning("Hãy chọn một code trong danh sách trước khi gán.")
                        return
                    add_delay_marker(selected_code)
                    st.toast("Đã gán lý do delay.")
                    st.rerun()
                if st.button("ĐÓNG", key="delay_marker_close", use_container_width=True):
                    st.rerun()
        else:
            st.warning("Không tìm thấy code phù hợp. Hãy thử từ khóa khác.")

    with login_tab:
        render_dwc_login_panel()

    with code_tab:
        st.caption("Quy ước bước đầu: chỉ CODE 5X được tính deduct; các nhóm còn lại ghi nhận vào gross/non-deduct.")
        st.dataframe(pd.DataFrame(DEFAULT_DELAY_CODES), use_container_width=True, hide_index=True)


def render_dwc_login_panel() -> None:
    st.markdown("### ĐĂNG NHẬP DWC THEO STS QUAY")
    st.caption("Chọn 1 STS Quay để hệ thống xác định bạn là DWC của cẩu đó trong phiên hiện tại.")
    selected = st.session_state.selected_dwc_crane
    cols = st.columns(3)
    for col, (group, cranes) in zip(cols, CRANE_GROUPS.items()):
        with col:
            st.markdown(f"#### {group}")
            for crane in cranes:
                label = f"✓ {crane}" if crane == selected else crane
                if st.button(label, key=f"dwc_login_{crane}", use_container_width=True):
                    st.session_state.selected_dwc_crane = crane
                    mark_change("Đăng nhập DWC", f"Đã chọn {crane}.")
                    add_audit_log("dwc_login", f"Chọn {crane}.")
                    st.rerun()
    if selected:
        st.success(f"DWC hiện tại: {selected}")


@st.dialog("📚 HƯỚNG DẪN SỬ DỤNG HỆ THỐNG SHIFT REPORT (TOÀN TẬP)", width="large")
def render_guide_dialog() -> None:
    section_0, section_1, section_2, section_3 = st.tabs(
        ["Workflow", "Dữ liệu đầu vào", "Quy trình", "Chỉ số & Delay"]
    )
    with section_0:
        st.markdown(
            """
            ### 0. QUY TRÌNH HỆ THỐNG

            **File Excel từ TOS/N4** → **lọc ca** → **phân loại tàu/sà lan/gate/yard**
            → **tính GMPH, AIT, DIT, BOE** → **người dùng bổ sung delay, thông số tàu, nhân sự**
            → **xuất Excel/PDF/Sync Cloud**.

            Người dùng chỉ cần upload file N4, kiểm tra khung giờ, nhập các thông tin vận hành còn thiếu,
            rồi bấm **Lưu thay đổi** trước khi xuất báo cáo.
            """
        )
    with section_1:
        st.markdown("### 1. QUY TẮC CA TRỰC & DỮ LIỆU ĐẦU VÀO")
        left, right = st.columns([1, 1])
        with left:
            st.info(
                "Ca D1: 06:00:01 đến 18:00:00 cùng ngày.\n\n"
                "Ca D2: 18:00:01 đến 06:00:00 sáng hôm sau.\n\n"
                "Khi bật AUTO, hệ thống tự điền ngày/ca dựa trên file upload hoặc thời điểm hiện tại."
            )
        with right:
            st.markdown("**Yêu cầu cột N4 tối thiểu:**")
            for col_name, desc in REQUIRED_N4_COLUMNS:
                st.markdown(f"- `{col_name}`: {desc}")
    with section_2:
        st.markdown(
            """
            ### 2. QUY TRÌNH XỬ LÝ DỮ LIỆU

            1. **Upload dữ liệu & kiểm tra delay**: nạp file N4, quét khoảng trống giữa các move cùng cẩu.
            2. **Nhập thông số tàu**: first line, all line fast, gangway, lashing finish, last line.
            3. **Tính BOE & cập nhật report**: ghép cặp tàu/sà lan và kiểm tra gate/yard/housekeeping.
            4. **Lưu & xuất báo cáo**: xem danh sách thay đổi thủ công trước khi xác nhận lưu.
            """
        )
    with section_3:
        st.markdown(
            """
            ### 3. GIẢI NGHĨA CHỈ SỐ & DELAY

            - **GMPH** = Tổng moves / (Tổng giờ gross - giờ deduct).
            - **PMPH** = Tổng moves / (Last line - All line fast).
            - **BMPH** = Tổng moves / (khung giờ khai thác - gangway secure).
            - **AIT** = First lift - All line fast.
            - **DIT** = Last line - Last lift.
            - **BOE** = khoảng trống cầu bến trung bình giữa tàu trước và tàu sau.
            - **CODE 5X**: giảm trừ net crane hours.
            - **Các nhóm code khác**: ghi nhận sự kiện vào gross/non-deduct, không giảm trừ năng suất.
            """
        )

    if st.button("ĐÃ HIỂU & ĐÓNG", key="guide_close", type="primary"):
        st.rerun()


@st.dialog(f"PHIÊN BẢN {APP_VERSION}", width="small")
def render_version_dialog() -> None:
    st.caption("Định dạng: dd.mm.yyyy lúc hh:mm và ghi chú thay đổi.")
    for item in DEFAULT_VERSION_LOG:
        st.markdown(f"**{item['time']}** — {item['detail']}")
        st.divider()
    if st.button("ĐÓNG", key="version_close", type="primary"):
        st.rerun()


def on_report_date_changed() -> None:
    new_date = st.session_state.report_date_widget
    if new_date != st.session_state.report_date:
        st.session_state.report_date = new_date
        st.session_state.delay_marker_date = new_date
        st.session_state.delay_date_widget = new_date
        mark_change("Đổi ngày báo cáo", f"Ngày mới: {format_date(new_date)}.")


def on_shift_changed() -> None:
    new_shift = st.session_state.shift_code_widget
    if new_shift != st.session_state.shift_code:
        st.session_state.shift_code = new_shift
        mark_change("Đổi ca báo cáo", f"Ca mới: {new_shift}.")


def toggle_report_shift() -> None:
    current_shift = st.session_state.shift_code
    new_shift = "D2" if current_shift == "D1" else "D1"
    st.session_state.shift_code = new_shift
    st.session_state.shift_code_widget = new_shift
    mark_change("Đổi ca báo cáo", f"{current_shift} → {new_shift}.")


def on_delay_date_changed() -> None:
    st.session_state.delay_marker_date = st.session_state.delay_date_widget


def on_delay_time_changed() -> None:
    st.session_state.delay_marker_time = st.session_state.delay_time_widget


def on_kpi_changed(label: str) -> None:
    new_value = int(st.session_state[f"kpi_{label}"])
    old_value = int(st.session_state.kpi_targets.get(label, KPI_DEFAULTS[label]))
    if new_value != old_value:
        st.session_state.kpi_targets[label] = new_value
        mark_change("Cập nhật KPI target", f"{label}: {old_value} → {new_value}.")


def handle_uploaded_file(uploaded_file: Any) -> None:
    meta = {
        "name": uploaded_file.name,
        "size": int(getattr(uploaded_file, "size", 0) or 0),
        "type": getattr(uploaded_file, "type", "") or "unknown",
    }
    if meta == st.session_state.uploaded_file_meta and st.session_state.raw_data is not None:
        return

    file_bytes = uploaded_file.getvalue()
    try:
        parsed = read_n4_file_bytes(uploaded_file.name, file_bytes)
        st.session_state.raw_data = parsed
        st.session_state.upload_error = ""
        meta["rows"] = len(parsed)
    except Exception as exc:
        st.session_state.raw_data = None
        st.session_state.upload_error = str(exc)
        meta["rows"] = 0

    st.session_state.uploaded_file_meta = meta
    mark_change("Upload dữ liệu N4", f"{meta['name']} ({format_bytes(meta['size'])}, {meta['rows']:,} dòng).")
    add_audit_log("upload", f"Nhận file {meta['name']} ({format_bytes(meta['size'])}, {meta['rows']:,} dòng).")

    if st.session_state.auto_shift:
        apply_auto_report_context("Auto sau upload")
    else:
        inferred = infer_date_from_filename(meta["name"])
        if inferred:
            set_report_date(inferred, "Auto nhận ngày từ tên file upload")


def apply_auto_report_context(reason: str) -> None:
    uploaded = st.session_state.uploaded_file_meta
    file_date = infer_date_from_filename(uploaded["name"]) if uploaded else None
    inferred_date, inferred_shift = infer_report_context_from_clock(datetime.now())
    final_date = file_date or inferred_date

    changed_parts = []
    if st.session_state.report_date != final_date:
        st.session_state.report_date = final_date
        st.session_state.report_date_widget = final_date
        st.session_state.delay_marker_date = final_date
        st.session_state.delay_date_widget = final_date
        changed_parts.append(f"ngày {format_date(final_date)}")
    if st.session_state.shift_code != inferred_shift:
        st.session_state.shift_code = inferred_shift
        st.session_state.shift_code_widget = inferred_shift
        changed_parts.append(f"ca {inferred_shift}")

    detail = ", ".join(changed_parts) if changed_parts else "ngày/ca đã đúng theo ngữ cảnh hiện tại"
    mark_change(reason, detail)
    add_audit_log("auto_context", detail)


def set_report_date(new_date: date, reason: str) -> None:
    if new_date == st.session_state.report_date:
        return
    st.session_state.report_date = new_date
    st.session_state.report_date_widget = new_date
    st.session_state.delay_marker_date = new_date
    st.session_state.delay_date_widget = new_date
    mark_change(reason, f"Ngày: {format_date(new_date)}.")


def adjust_delay_time(minutes: int) -> None:
    marker_dt = datetime.combine(st.session_state.delay_marker_date, st.session_state.delay_marker_time)
    marker_dt += timedelta(minutes=minutes)
    st.session_state.delay_marker_time = marker_dt.time().replace(second=0, microsecond=0)
    st.session_state.delay_time_widget = st.session_state.delay_marker_time


def adjust_delay_date(days: int) -> None:
    new_date = st.session_state.delay_marker_date + timedelta(days=days)
    st.session_state.delay_marker_date = new_date
    st.session_state.delay_date_widget = new_date


def add_delay_marker(selected_code: dict[str, Any]) -> None:
    marker = {
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "crane": st.session_state.delay_marker_crane,
        "date": format_date(st.session_state.delay_marker_date),
        "time": st.session_state.delay_marker_time.strftime("%H:%M"),
        "shift": delay_shift_label(st.session_state.delay_marker_time),
        "code": selected_code["code"],
        "mode": selected_code["mode"],
        "deduct": "YES" if selected_code["deduct"] else "NO",
        "reason": selected_code["name"],
        "hashtag": st.session_state.delay_hashtag,
        "remark": st.session_state.delay_remark,
    }
    st.session_state.delay_markers.insert(0, marker)
    st.session_state.delay_markers = st.session_state.delay_markers[:100]
    mark_change("Gán lý do delay", f"{marker['crane']} {marker['time']} code {marker['code']} - {marker['reason']}.")
    add_audit_log("save_delay", f"{marker['crane']} {marker['date']} {marker['time']} code {marker['code']}.")


def mark_change(action: str, detail: str) -> None:
    st.session_state.pending_changes.insert(
        0,
        {
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "action": action,
            "detail": detail,
        },
    )
    st.session_state.pending_changes = st.session_state.pending_changes[:50]


def add_audit_log(action: str, detail: str) -> None:
    st.session_state.audit_logs.insert(
        0,
        {
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "action": action,
            "detail": detail,
        },
    )
    st.session_state.audit_logs = st.session_state.audit_logs[:100]


def infer_report_context_from_clock(now: datetime) -> tuple[date, str]:
    if now.time() < time(6, 0):
        return now.date() - timedelta(days=1), "D2"
    if now.time() >= time(18, 0):
        return now.date(), "D2"
    return now.date(), "D1"


def infer_date_from_filename(filename: str) -> date | None:
    match = re.search(r"(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)", filename)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def all_cranes() -> list[str]:
    cranes: list[str] = []
    for group_cranes in CRANE_GROUPS.values():
        cranes.extend(group_cranes)
    return cranes


def filter_delay_codes(query: str) -> list[dict[str, Any]]:
    cleaned = query.strip().lower()
    if not cleaned:
        return DEFAULT_DELAY_CODES
    return [
        item
        for item in DEFAULT_DELAY_CODES
        if cleaned in item["code"].lower()
        or cleaned in item["name"].lower()
        or cleaned in item["mode"].lower()
        or cleaned in item["group"].lower()
    ]


def delay_shift_label(marker_time: time) -> str:
    return "NIGHT" if marker_time >= time(18, 0) or marker_time < time(6, 0) else "DAY"


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def format_bytes(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-0: #0b1220;
            --bg-1: #111827;
            --bg-2: #1b2638;
            --line: #2d3b51;
            --text: #e5edf7;
            --muted: #93a4b8;
            --blue: #3b82f6;
            --green: #22c55e;
            --yellow: #eab308;
            --orange: #f97316;
            --purple: #8b5cf6;
        }
        .stApp {
            background: var(--bg-0);
            color: var(--text);
        }
        header[data-testid="stHeader"], div[data-testid="stToolbar"] {
            display: none;
        }
        .block-container {
            padding: 0 0 24px 0;
            max-width: 100%;
        }
        .top-status {
            height: 24px;
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 0 10px;
            background: #111827;
            border-bottom: 1px solid var(--line);
            color: #b7c5d8;
            font-family: Consolas, monospace;
            font-size: 11px;
        }
        .status-spacer {
            flex: 1;
        }
        .status-item strong {
            color: #ffffff;
        }
        .status-sep {
            height: 14px;
            width: 1px;
            background: #55657a;
        }
        .dot {
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 999px;
            margin-right: 5px;
        }
        .dot-blue {
            background: #bfdbfe;
        }
        .dot-green, .live-dot {
            background: #22c55e;
        }
        .toolbar-band {
            background: linear-gradient(180deg, #111b2b 0%, #0c1422 100%);
            border-bottom: 1px solid var(--line);
            padding: 3px 8px 0 8px;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] {
            background: linear-gradient(180deg, #111b2b 0%, #0c1422 100%);
            border-bottom: 1px solid var(--line);
            box-shadow: inset 0 1px 0 rgba(96, 165, 250, .18);
            min-height: 48px;
            min-width: 1180px;
            overflow-x: auto;
            padding: 5px 8px 6px 8px;
            align-items: center;
            flex-wrap: nowrap;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stHorizontalBlock"] {
            background: linear-gradient(180deg, #111b2b 0%, #0c1422 100%) !important;
            border-bottom: 1px solid var(--line);
            box-shadow: inset 0 1px 0 rgba(96, 165, 250, .18);
            min-height: 48px;
            min-width: 1180px;
            overflow-x: auto;
            padding: 5px 8px 6px 8px;
            align-items: center;
            flex-wrap: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"] .stButton > button,
        div[data-testid="stPopover"] button {
            min-height: 30px;
            border-radius: 7px;
            border: 1px solid #34445d;
            background: #111827;
            color: #e5edf7;
            font-size: 11px;
            font-weight: 900;
            padding: 0 9px;
            white-space: nowrap;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 6px 16px rgba(0,0,0,.16);
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) button {
            background: linear-gradient(135deg, #ef4444 0%, #f97316 100%) !important;
            border-color: #fb923c !important;
            color: #ffffff !important;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(1) button {
            background: linear-gradient(135deg, #ef4444 0%, #f97316 100%) !important;
            border-color: #fb923c !important;
            color: #ffffff !important;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) button {
            background: linear-gradient(135deg, #111827 0%, #172554 100%) !important;
            border-color: #eab308 !important;
            color: #fde68a !important;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(2) button {
            background: linear-gradient(135deg, #111827 0%, #172554 100%) !important;
            border-color: #eab308 !important;
            color: #fde68a !important;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) button,
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(7) button {
            background: #0f172a !important;
            border-color: #334155 !important;
            color: #93c5fd !important;
            min-width: 28px;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(4) button,
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(7) button {
            background: #0f172a !important;
            border-color: #334155 !important;
            color: #93c5fd !important;
            min-width: 28px;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(8) button {
            background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%) !important;
            border-color: #60a5fa !important;
            color: #ffffff !important;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(8) button {
            background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%) !important;
            border-color: #60a5fa !important;
            color: #ffffff !important;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(9) button {
            background: linear-gradient(135deg, #15803d 0%, #22c55e 100%) !important;
            border-color: #4ade80 !important;
            color: #ffffff !important;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(9) button {
            background: linear-gradient(135deg, #15803d 0%, #22c55e 100%) !important;
            border-color: #4ade80 !important;
            color: #ffffff !important;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(10) button {
            background: linear-gradient(135deg, #6d28d9 0%, #a855f7 100%) !important;
            border-color: #c084fc !important;
            color: #ffffff !important;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(10) button {
            background: linear-gradient(135deg, #6d28d9 0%, #a855f7 100%) !important;
            border-color: #c084fc !important;
            color: #ffffff !important;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(11) button {
            background: linear-gradient(135deg, #92400e 0%, #f59e0b 100%) !important;
            border-color: #fbbf24 !important;
            color: #ffffff !important;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"]:nth-child(11) button {
            background: linear-gradient(135deg, #92400e 0%, #f59e0b 100%) !important;
            border-color: #fbbf24 !important;
            color: #ffffff !important;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            display: flex;
            align-items: center;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stColumn"] {
            display: flex;
            align-items: center;
        }
        div[data-testid="stDateInput"] label,
        div[data-testid="stSelectbox"] label {
            color: #b7c5d8;
            font-size: 11px;
            font-weight: 900;
        }
        .toolbar-mini-label {
            color: #93c5fd;
            font-family: Consolas, monospace;
            font-size: 10px;
            font-weight: 900;
            letter-spacing: .03em;
            line-height: 11px;
            margin: -2px 0 2px 1px;
        }
        .toolbar-mini-label.accent {
            color: #fde047;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] div[data-testid="stDateInput"] input,
        .toolbar-band + div[data-testid="stHorizontalBlock"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 31px;
            height: 31px;
            border-radius: 7px;
            border-color: #334155;
            background: #111827;
            color: #ffffff;
            font-size: 12px;
            font-weight: 850;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stDateInput"] input,
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 31px;
            height: 31px;
            border-radius: 7px;
            border-color: #334155;
            background: #111827;
            color: #ffffff;
            font-size: 12px;
            font-weight: 850;
        }
        .toolbar-band + div[data-testid="stHorizontalBlock"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            color: #fde047;
        }
        div[data-testid="stElementContainer"]:has(.toolbar-band) + div[data-testid="stLayoutWrapper"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            color: #fde047;
        }
        .brand {
            padding-top: 0;
            min-width: 130px;
        }
        .brand-title {
            color: #ffffff;
            font-size: 17px;
            font-weight: 950;
            line-height: 17px;
            letter-spacing: .04em;
            text-shadow: 0 0 14px rgba(96, 165, 250, .25);
        }
        .brand-subtitle {
            color: #93c5fd;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: .08em;
        }
        .toolbar-right {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            color: var(--muted);
            font-family: Consolas, monospace;
            font-size: 10px;
            min-height: 32px;
        }
        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            display: inline-block;
        }
        .linked-pill {
            border: 1px solid #60a5fa;
            background: linear-gradient(135deg, #10244a 0%, #172554 100%);
            color: #dbeafe;
            border-radius: 5px;
            padding: 2px 8px;
            line-height: 12px;
            text-align: center;
        }
        .linked-pill small {
            text-decoration: underline;
            font-size: 9px;
        }
        div[data-testid="stTabs"] {
            background: #101827;
        }
        div[data-testid="stTabs"] button {
            color: #b7c5d8;
            font-weight: 900;
            font-size: 12px;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #60a5fa;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: #3b82f6;
        }
        .tab-shell {
            padding: 20px 22px;
        }
        .dashboard-shell {
            padding-top: 16px;
        }
        .dashboard-hero {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 14px;
            padding: 16px 18px;
            border: 1px solid #243955;
            border-radius: 8px;
            background:
                radial-gradient(circle at 12% 0%, rgba(59,130,246,.18), transparent 34%),
                linear-gradient(135deg, #101827 0%, #111827 55%, #0b1220 100%);
        }
        .dashboard-eyebrow {
            color: #60a5fa;
            font-family: Consolas, monospace;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: .08em;
        }
        .dashboard-title {
            color: #ffffff;
            font-size: 28px;
            font-weight: 950;
            line-height: 30px;
            letter-spacing: .04em;
        }
        .dashboard-subtitle {
            color: #9fb0c8;
            font-size: 12px;
            font-weight: 750;
            margin-top: 4px;
        }
        .dashboard-hero-actions {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
        }
        .dashboard-hero-actions span {
            border: 1px solid #334155;
            border-radius: 999px;
            background: #0f172a;
            color: #dbeafe;
            font-family: Consolas, monospace;
            font-size: 11px;
            font-weight: 900;
            padding: 6px 10px;
        }
        .dashboard-kpi-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 14px;
        }
        .dashboard-kpi-card {
            min-height: 108px;
            border: 1px solid #2f4058;
            border-radius: 8px;
            background: #111827;
            padding: 12px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.05), 0 12px 28px rgba(0,0,0,.16);
        }
        .dashboard-kpi-card.blue { border-color: #2563eb; background: linear-gradient(135deg, rgba(37,99,235,.28), #111827 58%); }
        .dashboard-kpi-card.green { border-color: #16a34a; background: linear-gradient(135deg, rgba(22,163,74,.28), #111827 58%); }
        .dashboard-kpi-card.purple { border-color: #7c3aed; background: linear-gradient(135deg, rgba(124,58,237,.28), #111827 58%); }
        .dashboard-kpi-card.cyan { border-color: #0891b2; background: linear-gradient(135deg, rgba(8,145,178,.28), #111827 58%); }
        .dashboard-kpi-card.red { border-color: #ef4444; background: linear-gradient(135deg, rgba(239,68,68,.28), #111827 58%); }
        .dashboard-kpi-card.yellow { border-color: #eab308; background: linear-gradient(135deg, rgba(234,179,8,.28), #111827 58%); }
        .kpi-title {
            color: #93a4b8;
            font-family: Consolas, monospace;
            font-size: 11px;
            font-weight: 900;
        }
        .kpi-value {
            color: #ffffff;
            font-size: 26px;
            font-weight: 950;
            line-height: 34px;
            margin-top: 4px;
        }
        .kpi-note {
            color: #9fb0c8;
            font-size: 11px;
            font-weight: 750;
        }
        .dashboard-panel {
            border: 1px solid #2d3b51;
            border-radius: 8px;
            background: #111827;
            padding: 12px;
            min-height: 280px;
        }
        .mix-row {
            margin-bottom: 13px;
        }
        .mix-label {
            display: flex;
            justify-content: space-between;
            color: #dbeafe;
            font-size: 12px;
            font-weight: 850;
            margin-bottom: 5px;
        }
        .mix-label strong {
            color: #ffffff;
        }
        .mix-track {
            height: 8px;
            border-radius: 999px;
            background: #0b1220;
            overflow: hidden;
            border: 1px solid #1f2f46;
        }
        .mix-track div {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #3b82f6, #22c55e);
        }
        .delay-watch {
            min-height: 116px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, rgba(239,68,68,.18), #111827 64%);
            border-color: #ef4444;
        }
        .delay-watch-number {
            color: #ffffff;
            font-size: 36px;
            font-weight: 950;
            line-height: 38px;
        }
        .delay-watch-label {
            color: #fecaca;
            font-size: 12px;
            font-weight: 900;
        }
        .delay-watch-meta {
            color: #9fb0c8;
            font-size: 11px;
            margin-top: 6px;
        }
        @media (max-width: 1300px) {
            .dashboard-kpi-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }
        }
        @media (max-width: 760px) {
            .dashboard-kpi-grid {
                grid-template-columns: repeat(1, minmax(0, 1fr));
            }
            .dashboard-hero {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        div[data-testid="stMetric"] {
            background: #111827;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px;
        }
        .dialog-empty {
            min-height: 84px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #8492a7;
            font-weight: 800;
            font-style: italic;
            border-top: 1px solid var(--line);
            border-bottom: 1px solid var(--line);
            margin: 6px 0 12px 0;
        }
        div[role="dialog"] {
            background: #0b1220;
            border: 1px solid #2b3a52;
            width: min(96vw, 1240px) !important;
            max-width: 1240px !important;
        }
        div[role="dialog"] [data-testid="stVerticalBlock"] {
            gap: .48rem;
        }
        div[role="dialog"] h2 {
            font-size: 22px;
            margin-bottom: 4px;
        }
        div[role="dialog"] label {
            font-size: 12px;
            font-weight: 850;
        }
        .delay-modal-title {
            color: #ffffff;
            font-size: 17px;
            font-weight: 950;
            margin: 2px 0 2px 0;
        }
        .delay-shift-badge {
            height: 38px;
            border: 1px solid #334155;
            border-radius: 6px;
            background: #121c2d;
            color: #facc15;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 950;
            letter-spacing: .02em;
        }
        .delay-selected-code {
            border: 1px solid #334155;
            border-radius: 6px;
            background: #111827;
            color: #dbeafe;
            padding: 8px 10px;
            font-size: 12px;
            margin-top: -2px;
        }
        .delay-selected-code.muted {
            color: #93a4b8;
            font-style: italic;
        }
        h2, h3, h4 {
            color: var(--text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
