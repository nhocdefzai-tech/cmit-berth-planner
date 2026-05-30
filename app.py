from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from cmit.config import PROJECT_ROOT, ensure_runtime_dirs
from cmit.delay_codes import as_records as delay_code_records
from cmit.delay_codes import code_options, delay_group, describe_code, is_deductible_code, normalize_code
from cmit.email_draft import build_email_draft
from cmit.importer import read_move_file
from cmit.kpi import CHE_TYPES, PRODUCTIVE_KINDS, calculate_report
from cmit.report_exporter import export_shift_report
from cmit.shift import assign_shift, is_in_shift, make_shift
from cmit.storage import (
    get_manual_inputs,
    get_shift,
    get_shift_spec,
    init_db,
    latest_generated_report,
    list_shift_summaries,
    list_shifts,
    list_personnel_names,
    load_moves,
    replace_moves,
    save_generated_report,
    save_manual_inputs,
    save_source_file,
    update_carrier_classifications,
    upsert_shift,
)


st.set_page_config(layout="wide", page_title="CMIT Shift Report Control")
ensure_runtime_dirs()
init_db()


def main() -> None:
    st.title("CMIT SHIFT REPORT CONTROL")
    st.caption("Berth planning, N4 move review, manual shift inputs, and Shift Operation Report export.")

    selected_shift_id = render_sidebar()
    if not selected_shift_id:
        st.info("Create or select a shift in the sidebar to begin.")
        return

    shift_row = get_shift(selected_shift_id)
    shift = get_shift_spec(selected_shift_id)
    moves = load_moves(selected_shift_id)
    manual = get_manual_inputs(selected_shift_id)

    st.subheader(f"{shift.code} / {shift.work_date.isoformat()}")
    st.caption(f"Window: {shift.start:%Y-%m-%d %H:%M} to {shift.end:%Y-%m-%d %H:%M} | Status: {shift_row['status']}")

    tab_shift, tab_review, tab_report, tab_delay, tab_berth, tab_export = st.tabs(
        ["Create / Select Shift", "Data Review", "Shift Report", "Delay Codes", "Berth Planner", "Export"]
    )

    with tab_shift:
        render_shift_overview(selected_shift_id, moves)

    with tab_review:
        render_data_review(selected_shift_id, moves)

    with tab_report:
        render_shift_report(selected_shift_id, moves, manual)

    with tab_delay:
        render_delay_codes(selected_shift_id, moves, manual)

    with tab_berth:
        render_berth_planner(moves)

    with tab_export:
        render_export(selected_shift_id, moves)


def render_sidebar() -> int | None:
    st.sidebar.header("Shift Workspace")
    with st.sidebar.form("create_shift"):
        work_date = st.date_input("Work date", value=date.today())
        shift_code = st.selectbox("Shift", ["D1", "D2"], index=0)
        uploaded = st.file_uploader("Upload N4 / MoveEvent / Shift workbook", type=["xlsx", "xls"])
        sample_path = PROJECT_ROOT / "MoveEvent_20260526_2203.xlsx"
        use_sample = st.checkbox("Import sample MoveEvent file", value=False, disabled=not sample_path.exists())
        submitted = st.form_submit_button("Create / Import Shift")

    if submitted:
        shift_id = upsert_shift(work_date, shift_code)
        shift = make_shift(work_date, shift_code)
        source_path = None
        if uploaded is not None:
            source_path = save_source_file(shift_id, uploaded.name, uploaded.getvalue())
        elif use_sample and sample_path.exists():
            source_path = save_source_file(shift_id, sample_path.name, sample_path.read_bytes())

        if source_path:
            try:
                all_moves = read_move_file(source_path)
                normalized = _filter_moves_for_shift(all_moves, shift)
                import_shift_id = shift_id
                import_shift = shift
                if normalized.empty and not all_moves.empty:
                    import_shift = _dominant_shift_from_moves(all_moves)
                    import_shift_id = upsert_shift(import_shift.work_date, import_shift.code)
                    normalized = _filter_moves_for_shift(all_moves, import_shift)
                    st.sidebar.warning(
                        "Selected shift had no matching moves. "
                        f"Detected file data from {import_shift.label}, so it was imported there instead."
                    )
                replace_moves(import_shift_id, normalized)
                st.sidebar.success(f"Imported {len(normalized):,} moves into {import_shift.label}.")
                st.session_state["selected_shift_id"] = import_shift_id
            except Exception as exc:
                st.sidebar.error(f"Import failed: {exc}")
        else:
            st.sidebar.success(f"Created empty shift {shift.label}.")
            st.session_state["selected_shift_id"] = shift_id

    shifts = list_shifts()
    if not shifts:
        return None
    labels = [f"#{s['id']} - {s['work_date']} {s['shift_code']} ({s['status']})" for s in shifts]
    default_index = 0
    if "selected_shift_id" in st.session_state:
        for idx, row in enumerate(shifts):
            if row["id"] == st.session_state["selected_shift_id"]:
                default_index = idx
                break
    selected_label = st.sidebar.selectbox("Open shift", labels, index=default_index)
    selected_shift_id = shifts[labels.index(selected_label)]["id"]
    st.session_state["selected_shift_id"] = selected_shift_id
    return selected_shift_id


def _filter_moves_for_shift(moves: pd.DataFrame, shift) -> pd.DataFrame:
    if moves.empty:
        return moves.copy()
    times = pd.to_datetime(moves["TIME STS QUAY"], errors="coerce")
    filtered = moves[times.apply(lambda x: pd.notna(x) and is_in_shift(x.to_pydatetime(), shift))].copy()
    filtered["CA"] = shift.label
    return filtered.reset_index(drop=True)


def _dominant_shift_from_moves(moves: pd.DataFrame):
    times = pd.to_datetime(moves["TIME STS QUAY"], errors="coerce").dropna()
    if times.empty:
        return make_shift(date.today(), "D1")
    shift_keys = times.apply(lambda x: assign_shift(x.to_pydatetime())).apply(lambda s: (s.work_date, s.code))
    work_date, code = shift_keys.value_counts().index[0]
    return make_shift(work_date, code)


def render_shift_overview(shift_id: int, moves: pd.DataFrame) -> None:
    st.markdown("#### Shift Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(moves):,}")
    c2.metric("Carrier visits", _nunique(moves, "CARRIER VISIT"))
    c3.metric("QC", _qc_count(moves))
    c4.metric("Productive moves", int(moves["MOVE KIND"].isin(PRODUCTIVE_KINDS).sum()) if not moves.empty else 0)

    if moves.empty:
        st.info("No move data imported yet. Use the sidebar to upload a source file for this shift.")
        populated = [s for s in list_shift_summaries() if int(s.get("move_count") or 0) > 0]
        if populated:
            hint = "\n".join(
                f"- #{s['id']} - {s['work_date']} {s['shift_code']}: {int(s['move_count']):,} moves"
                for s in populated[:5]
            )
            st.warning(
                "Other shifts already contain imported data. "
                "Open one of these shifts from the sidebar if this upload belonged to another date/shift:\n\n"
                f"{hint}"
            )
        return
    st.dataframe(
        moves.head(200),
        width="stretch",
        hide_index=True,
    )


def render_data_review(shift_id: int, moves: pd.DataFrame) -> None:
    st.markdown("#### Data Quality & Classification")
    if moves.empty:
        st.info("No data available for review.")
        return

    time_min = pd.to_datetime(moves["TIME STS QUAY"], errors="coerce").min()
    time_max = pd.to_datetime(moves["TIME STS QUAY"], errors="coerce").max()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("First move", "" if pd.isna(time_min) else time_min.strftime("%H:%M"))
    c2.metric("Last move", "" if pd.isna(time_max) else time_max.strftime("%H:%M"))
    c3.metric("Move kinds", _nunique(moves, "MOVE KIND"))
    c4.metric("Quay/Yard/Gate", _nunique(moves, "LOAI CAU BEN"))

    st.markdown("##### Carrier classification")
    grouped = (
        moves.groupby("CARRIER VISIT", dropna=False)
        .agg(
            moves=("UNIT NBR", "count"),
            first_move=("TIME STS QUAY", "min"),
            last_move=("TIME STS QUAY", "max"),
            loai_ptvt=("LOAI PTVT", "first"),
            loai_cau_ben=("LOAI CAU BEN", "first"),
        )
        .reset_index()
        .sort_values(["loai_cau_ben", "loai_ptvt", "moves"], ascending=[True, True, False])
    )
    grouped["first_move"] = pd.to_datetime(grouped["first_move"], errors="coerce").dt.strftime("%H:%M")
    grouped["last_move"] = pd.to_datetime(grouped["last_move"], errors="coerce").dt.strftime("%H:%M")
    edited = st.data_editor(
        grouped,
        width="stretch",
        hide_index=True,
        disabled=["CARRIER VISIT", "moves", "first_move", "last_move"],
        column_config={
            "loai_ptvt": st.column_config.SelectboxColumn("LOAI PTVT", options=["", "VESSEL", "BARGE"]),
            "loai_cau_ben": st.column_config.SelectboxColumn("LOAI CAU BEN", options=["", "CMIT QUAY", "YARD", "GATE"]),
        },
        key=f"classification_editor_{shift_id}",
    )
    if st.button("Save carrier classifications", key=f"save_classifications_{shift_id}"):
        update_carrier_classifications(
            shift_id,
            [
                {
                    "carrier_visit": row["CARRIER VISIT"],
                    "loai_ptvt": row["loai_ptvt"],
                    "loai_cau_ben": row["loai_cau_ben"],
                }
                for _, row in edited.iterrows()
            ],
        )
        st.success("Carrier classifications saved.")
        st.rerun()

    st.markdown("##### Move-kind summary")
    st.dataframe(moves["MOVE KIND"].value_counts().rename_axis("MOVE KIND").reset_index(name="COUNT"), width="stretch", hide_index=True)


def render_shift_report(shift_id: int, moves: pd.DataFrame, manual: dict) -> None:
    shift = get_shift_spec(shift_id)
    payload = _copy_payload(manual)
    auto_payload = _manual_with_auto_che(payload)
    auto_bundle = calculate_report(moves, auto_payload, shift)
    bundle = calculate_report(moves, payload, shift)

    st.markdown(
        f"<h3 style='text-align:center;margin-bottom:0'>SHIFT OPERATION REPORT</h3>"
        f"<div style='text-align:center;font-weight:700'>DATE: {shift.work_date.isoformat()} / SHIFT: {shift.code}</div>",
        unsafe_allow_html=True,
    )

    render_report_preview(bundle)

    st.markdown("#### Update Shift Report")
    st.caption("Personnel names are saved after each update and will be available for later shifts.")
    personnel = payload.get("personnel", {})
    gate = payload.get("gate", {})
    other = payload.get("other", {})
    che = payload.get("che", {})

    with st.form(f"shift_report_form_{shift_id}"):
        st.markdown("##### Personnel on duty")
        personnel["shift_manager"] = _personnel_picker("SHIFT MANAGER (SM)", "shift_manager", personnel.get("shift_manager", ""))
        personnel["vessel_supervisors"] = _personnel_picker("VESSEL SUPERVISORS", "vessel_supervisors", personnel.get("vessel_supervisors", ""))
        personnel["yard_supervisors"] = _personnel_picker("YARD SUPERVISORS", "yard_supervisors", personnel.get("yard_supervisors", ""))

        st.markdown("##### Gate & Yard / Others")
        g1, g2, g3, g4 = st.columns(4)
        gate["gate_in"] = g1.number_input("Gate In", min_value=0, value=int(gate.get("gate_in") or _auto_gate(moves, "GATE IN")), step=1)
        gate["gate_out"] = g2.number_input("Gate Out", min_value=0, value=int(gate.get("gate_out") or _auto_gate(moves, "GATE OUT")), step=1)
        gate["total"] = g3.number_input("Gate Total", min_value=0, value=int(gate.get("total") or (gate["gate_in"] + gate["gate_out"])), step=1)
        gate["ttt"] = g4.text_input("TTT", value=str(gate.get("ttt", "")), placeholder="19.30")
        o1, o2, o3 = st.columns([1, 1, 4])
        other["hk_moves"] = o1.number_input("HK Moves", min_value=0, value=int(other.get("hk_moves") or _auto_hk(moves)), step=1)
        other["boe"] = o2.text_input("BOE", value=other.get("boe", "--"))
        other["vessel_sequence"] = o3.text_area("Vessel sequence", value=other.get("vessel_sequence", ""), height=82)
        other["incident"] = st.text_input("Incident", value=other.get("incident", "NONE"))
        other["operation_notes"] = st.text_area("Operation notes", value=other.get("operation_notes", "Safe operation"), height=70)

        st.markdown("##### CHE Availability")
        st.caption("Demand is calculated from imported DATA when no manual value exists. Adjust with arrows or type values when reality changes.")
        demand = che.get("demand", {})
        bd_time = che.get("bd_time", {})
        auto_demand = auto_bundle.che["demand"]
        auto_bd = auto_bundle.che["bd_time"]
        demand_cols = st.columns(len(CHE_TYPES))
        for idx, kind in enumerate(CHE_TYPES):
            default = float(demand.get(kind) or auto_demand.get(kind, 0))
            demand[kind] = demand_cols[idx].number_input(f"{kind} demand", min_value=0.0, value=default, step=1.0, format="%.2f")
        bd_cols = st.columns(len(CHE_TYPES))
        for idx, kind in enumerate(CHE_TYPES):
            default = float(bd_time.get(kind) or auto_bd.get(kind, 0))
            bd_time[kind] = bd_cols[idx].number_input(f"{kind} BD min", min_value=0.0, value=default, step=1.0, format="%.0f")
        che["notes"] = st.text_area("CHE notes", value=che.get("notes", ""), height=70)

        payload["personnel"] = personnel
        payload["gate"] = gate
        payload["other"] = other
        payload["che"] = {"demand": demand, "bd_time": bd_time, "notes": che.get("notes", "")}
        submitted = st.form_submit_button("Save Shift Report")

    st.markdown("##### Vessel Calls")
    vessel_df = st.data_editor(
        pd.DataFrame(_vessel_call_rows(moves, payload)),
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key=f"vessel_calls_{shift_id}",
    )

    st.markdown("##### Equipment Breakdown")
    breakdown_df = st.data_editor(
        pd.DataFrame(
            payload.get("equipment_breakdowns", [])
            or [{"che": "", "type": "BD", "fault_description": "", "start": "", "end": "", "duration_min": 0, "remarks": ""}]
        ),
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key=f"breakdowns_{shift_id}",
    )

    if submitted or st.button("Save Vessel/Equipment Tables", key=f"save_shift_report_tables_{shift_id}"):
        payload["vessel_calls"] = _records_without_blank_keys(vessel_df, "carrier_visit")
        payload["equipment_breakdowns"] = _records_without_blank_keys(breakdown_df, "che")
        save_manual_inputs(shift_id, payload)
        st.success("Shift Report updated.")
        st.rerun()


def render_report_preview(bundle) -> None:
    personnel = bundle.manual.get("personnel", {})
    st.dataframe(
        pd.DataFrame(
            [
                {"ROLE": "SHIFT MANAGER (SM)", "NAME": personnel.get("shift_manager", "")},
                {"ROLE": "VESSEL SUPERVISORS", "NAME": personnel.get("vessel_supervisors", "")},
                {"ROLE": "YARD SUPERVISORS", "NAME": personnel.get("yard_supervisors", "")},
            ]
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("##### Operation Performance")
    st.dataframe(pd.DataFrame(bundle.summary_rows).astype(str), width="stretch", hide_index=True)

    st.markdown("##### Gate & Yard / Others")
    gate = bundle.gate
    other = bundle.manual.get("other", {})
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "INFO": "INFO",
                    "GATE IN": gate.get("gate_in", 0),
                    "GATE OUT": gate.get("gate_out", 0),
                    "TOTAL": gate.get("total", 0),
                    "TTT": gate.get("ttt", ""),
                    "HK MOVES": other.get("hk_moves") or _auto_hk(bundle.moves),
                    "VESSEL SEQUENCE": other.get("vessel_sequence", ""),
                    "BOE": other.get("boe", "--"),
                    "INCIDENT": other.get("incident", "NONE"),
                }
            ]
        ).astype(str),
        width="stretch",
        hide_index=True,
    )

    st.markdown("##### CHE Availability")
    che_rows = []
    che = bundle.che
    for row_name, key in [("DEMAND", "demand"), ("BD TIME (MIN)", "bd_time"), ("ACTUAL (UNIT)", "actual")]:
        row = {"CHE AVAILABILITY": row_name}
        for kind in CHE_TYPES:
            value = che[key].get(kind, 0)
            row[kind] = "-" if row_name == "BD TIME (MIN)" and not value else value
        row["NOTES"] = che.get("notes", "") if row_name == "DEMAND" else ""
        che_rows.append(row)
    avail = {"CHE AVAILABILITY": "% AVAIL"}
    for kind in CHE_TYPES:
        avail[kind] = f"{che['availability'].get(kind, 1) * 100:.2f}%"
    avail["NOTES"] = ""
    che_rows.append(avail)
    st.dataframe(pd.DataFrame(che_rows).astype(str), width="stretch", hide_index=True)


def render_delay_codes(shift_id: int, moves: pd.DataFrame, manual: dict) -> None:
    st.markdown("#### Delay Codes")
    st.caption("Only Code 5X records are deducted from net crane hours and GMPH. Other codes remain reportable delay notes.")

    col_ref, col_input = st.columns([1, 2])
    with col_ref:
        group_filter = st.selectbox(
            "Delay code group",
            ["All", "0X Milestone", "2X Crane Breakdown", "3X/4X Operational", "5X Deduction", "6X Emergency", "7X Other"],
            index=4,
        )
        ref_df = pd.DataFrame(delay_code_records())
        if group_filter != "All":
            ref_df = ref_df[ref_df["Group"].eq(group_filter)]
        st.dataframe(ref_df, width="stretch", hide_index=True, height=430)

    with col_input:
        st.markdown("##### QC work summary")
        work_df = _qc_work_summary(moves)
        st.dataframe(work_df, width="stretch", hide_index=True, height=220)

        st.markdown("##### Delay input by Carrier / QC")
        carrier_type_map = _carrier_type_map(work_df)
        delays = _enrich_delay_rows(manual.get("delays", []), carrier_type_map)
        if not delays:
            delays = [
                {
                    "carrier_visit": "",
                    "transport_type": "",
                    "crane": "ALL",
                    "code": "CODE 52",
                    "group": "5X Deduction",
                    "deduct_gmph": "YES",
                    "start": "",
                    "end": "",
                    "minutes": 0,
                    "remark": describe_code("CODE 52"),
                }
            ]
        carrier_options = [""] + sorted(work_df["carrier_visit"].dropna().astype(str).unique().tolist()) if not work_df.empty else [""]
        crane_options = ["ALL"] + sorted(work_df["crane"].dropna().astype(str).unique().tolist()) if not work_df.empty else ["ALL"]
        delay_df = st.data_editor(
            pd.DataFrame(delays),
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "carrier_visit": st.column_config.SelectboxColumn("Carrier", options=carrier_options),
                "transport_type": st.column_config.TextColumn("Type"),
                "crane": st.column_config.SelectboxColumn("QC", options=crane_options),
                "code": st.column_config.SelectboxColumn("Code", options=code_options()),
                "group": st.column_config.TextColumn("Group"),
                "deduct_gmph": st.column_config.TextColumn("Deduct GMPH"),
                "minutes": st.column_config.NumberColumn("Minutes", min_value=0, step=1),
                "remark": st.column_config.TextColumn("Remark / editable content"),
            },
            disabled=["transport_type", "group", "deduct_gmph"],
            key=f"delay_editor_{shift_id}",
        )
        if st.button("Save Delay Codes", type="primary", key=f"save_delays_{shift_id}"):
            payload = _copy_payload(manual)
            payload["delays"] = _enrich_delay_rows(_records_without_blank_keys(delay_df, "carrier_visit"), carrier_type_map)
            save_manual_inputs(shift_id, payload)
            st.success("Delay records saved and Shift Report recalculated.")
            st.rerun()

        st.markdown("##### Deduction summary")
        st.dataframe(_delay_deduction_summary(_enrich_delay_rows(_records_without_blank_keys(delay_df, "carrier_visit"), carrier_type_map)), width="stretch", hide_index=True)


def render_berth_planner(moves: pd.DataFrame) -> None:
    st.markdown("#### Berth Planner")
    st.caption("Static berth visualization for Inner / Outer barge planning. Classification corrections from Data Review are reflected here.")
    barge_df = moves[(moves["LOAI PTVT"].eq("BARGE")) & (moves["LOAI CAU BEN"].eq("CMIT QUAY"))].copy() if not moves.empty else pd.DataFrame()
    if barge_df.empty:
        st.info("No barge moves found. Check Data Review if a carrier needs to be classified as BARGE.")
        return
    summary = (
        barge_df.groupby("CARRIER VISIT")
        .agg(moves=("UNIT NBR", "count"), first=("TIME STS QUAY", "min"), last=("TIME STS QUAY", "max"))
        .reset_index()
        .sort_values("moves", ascending=False)
    )
    options = summary["CARRIER VISIT"].tolist()
    c1, c2 = st.columns(2)
    inner = c1.multiselect("Inner / Cập cầu", options=options, key="berth_inner")
    outer = c2.multiselect("Outer / Cập mạn", options=[o for o in options if o not in inner], key="berth_outer")
    render_static_berth(inner, outer, summary)
    st.dataframe(summary, width="stretch", hide_index=True)


def render_export(shift_id: int, moves: pd.DataFrame) -> None:
    st.markdown("#### Export Shift Operation Report")
    if moves.empty:
        st.info("Import move data before exporting.")
        return
    shift = get_shift_spec(shift_id)
    manual = get_manual_inputs(shift_id)
    bundle = calculate_report(moves, manual, shift)
    cmit = bundle.summary_rows[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vessel moves", cmit["vessel_total"])
    c2.metric("Barge moves", cmit["barge_total"])
    c3.metric("Overall moves", cmit["overall_volume"])
    c4.metric("Overall GMPH", cmit["overall_gmph"])

    if st.button("Generate Excel + Email Draft", type="primary"):
        output_path = export_shift_report(bundle)
        subject, body = build_email_draft(bundle, output_path.name)
        save_generated_report(shift_id, output_path, subject, body)
        st.success(f"Generated {output_path.name}")
        st.rerun()

    latest = latest_generated_report(shift_id)
    if latest:
        path = Path(latest["file_path"])
        st.markdown(f"Latest report: [{path.name}]({path.resolve()})")
        if path.exists():
            st.download_button(
                "Download Excel report",
                data=path.read_bytes(),
                file_name=path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.text_input("Email subject", value=latest["email_subject"])
        st.text_area("Email draft", value=latest["email_body"], height=220)


def render_static_berth(inner: list[str], outer: list[str], summary: pd.DataFrame) -> None:
    lengths = {row["CARRIER VISIT"]: max(65, min(130, 50 + int(row["moves"]) // 2)) for _, row in summary.iterrows()}
    html = [
        "<div style='position:relative;width:100%;height:245px;border:2px solid #2c3e50;border-radius:8px;background:#f8f9fa;margin:10px 0 18px 0;'>",
        "<div style='position:absolute;left:0;right:0;top:122px;height:2px;background:#95a5a6;'></div>",
    ]
    for tick in range(35):
        left = tick / 34 * 100
        label = f"P{tick}" if tick % 2 == 0 or tick == 34 else "."
        html.append(
            f"<div style='position:absolute;left:{left:.2f}%;top:128px;transform:translateX(-50%);font-size:10px;text-align:center;color:#34495e;'>|<br>{label}</div>"
        )
    html.extend(_barge_blocks(outer, lengths, 24, "#7f8c8d", "MẠN"))
    html.extend(_barge_blocks(inner, lengths, 78, "#2980b9", "CẦU"))
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def _barge_blocks(names: list[str], lengths: dict[str, int], top: int, color: str, label: str) -> list[str]:
    blocks = []
    left_px = 28
    for name in names:
        width = lengths.get(name, 70) * 1.7
        blocks.append(
            "<div "
            f"style='position:absolute;left:{left_px}px;top:{top}px;width:{width}px;height:42px;background:{color};"
            "color:white;border-radius:5px;text-align:center;font-weight:bold;font-size:11px;display:flex;"
            "flex-direction:column;justify-content:center;box-shadow:0 3px 5px rgba(0,0,0,.18);'>"
            f"<span>{label} | {name}</span><span style='font-size:9px;opacity:.9'>{int(width/1.7)}m plan length</span></div>"
        )
        left_px += int(width) + 38
    return blocks


def _vessel_call_rows(moves: pd.DataFrame, payload: dict) -> list[dict]:
    existing = {str(r.get("carrier_visit", "")).strip(): r for r in payload.get("vessel_calls", [])}
    carriers = []
    if not moves.empty:
        carriers = (
            moves[(moves["LOAI PTVT"].eq("VESSEL")) & (moves["MOVE KIND"].isin(PRODUCTIVE_KINDS))]["CARRIER VISIT"]
            .dropna()
            .astype(str)
            .str.strip()
            .drop_duplicates()
            .tolist()
        )
    keys = list(dict.fromkeys([*carriers, *existing.keys()]))
    rows = []
    for carrier in keys:
        item = existing.get(carrier, {})
        rows.append(
            {
                "carrier_visit": carrier,
                "vessel_name": item.get("vessel_name", ""),
                "voyage": item.get("voyage", carrier),
                "service": item.get("service", ""),
                "first_line": item.get("first_line", ""),
                "all_line_fast": item.get("all_line_fast", ""),
                "gangway_secure": item.get("gangway_secure", ""),
                "etc": item.get("etc", ""),
                "etd": item.get("etd", ""),
                "lashing_finish": item.get("lashing_finish", ""),
                "last_line": item.get("last_line", ""),
                "ait": item.get("ait", ""),
                "ait2": item.get("ait2", ""),
                "dit": item.get("dit", ""),
                "pmph": item.get("pmph", ""),
                "bmph": item.get("bmph", ""),
                "operation_notes": item.get("operation_notes", payload.get("other", {}).get("operation_notes", "Safe operation")),
                "challenges": item.get("challenges", "NIL"),
                "resolution": item.get("resolution", "NIL"),
                "further_remarks": item.get("further_remarks", ""),
            }
        )
    return rows


def _copy_payload(manual: dict) -> dict:
    return deepcopy(manual)


def _manual_with_auto_che(manual: dict) -> dict:
    payload = _copy_payload(manual)
    payload["che"] = {"demand": {kind: 0 for kind in CHE_TYPES}, "bd_time": {kind: 0 for kind in CHE_TYPES}, "notes": payload.get("che", {}).get("notes", "")}
    return payload


def _personnel_picker(role_label: str, field: str, current_value: str) -> str:
    current_names = _split_names(current_value)
    options = sorted(set(list_personnel_names(role_label) + current_names))
    selected = st.multiselect(role_label, options=options, default=current_names, key=f"personnel_{field}_selected")
    extra = st.text_input(f"Add new {role_label}", value="", key=f"personnel_{field}_new", placeholder="Type one or more names, separated by commas")
    return _join_names([*selected, *_split_names(extra)])


def _qc_work_summary(moves: pd.DataFrame) -> pd.DataFrame:
    columns = ["carrier_visit", "transport_type", "crane", "moves", "first_lift", "last_lift", "gross_hours"]
    if moves.empty:
        return pd.DataFrame(columns=columns)
    productive = moves[moves["MOVE KIND"].isin(PRODUCTIVE_KINDS) & moves["STS QUAY"].astype(str).str.startswith("QC", na=False)].copy()
    if productive.empty:
        return pd.DataFrame(columns=columns)
    grouped = (
        productive.groupby(["CARRIER VISIT", "LOAI PTVT", "STS QUAY"], dropna=False)
        .agg(moves=("UNIT NBR", "count"), first_lift=("TIME STS QUAY", "min"), last_lift=("TIME STS QUAY", "max"))
        .reset_index()
        .rename(columns={"CARRIER VISIT": "carrier_visit", "LOAI PTVT": "transport_type", "STS QUAY": "crane"})
    )
    grouped["gross_hours"] = (
        (pd.to_datetime(grouped["last_lift"]) - pd.to_datetime(grouped["first_lift"])).dt.total_seconds().clip(lower=60) / 3600
    ).round(2)
    grouped["first_lift"] = pd.to_datetime(grouped["first_lift"]).dt.strftime("%H:%M")
    grouped["last_lift"] = pd.to_datetime(grouped["last_lift"]).dt.strftime("%H:%M")
    return grouped[columns].sort_values(["transport_type", "carrier_visit", "crane"])


def _carrier_type_map(work_df: pd.DataFrame) -> dict[str, str]:
    if work_df.empty:
        return {}
    return {
        str(row["carrier_visit"]): str(row["transport_type"])
        for _, row in work_df[["carrier_visit", "transport_type"]].drop_duplicates().iterrows()
    }


def _enrich_delay_rows(records: list[dict], carrier_type_map: dict[str, str] | None = None) -> list[dict]:
    carrier_type_map = carrier_type_map or {}
    enriched = []
    for record in records:
        code = normalize_code(record.get("code"))
        if not code:
            continue
        remark = str(record.get("remark", "") or "").strip() or describe_code(code)
        carrier = str(record.get("carrier_visit", "") or "").strip()
        enriched.append(
            {
                "carrier_visit": carrier,
                "transport_type": str(record.get("transport_type", "") or "").strip() or carrier_type_map.get(carrier, ""),
                "crane": str(record.get("crane", "ALL") or "ALL").strip() or "ALL",
                "code": code,
                "group": delay_group(code),
                "deduct_gmph": "YES" if is_deductible_code(code) else "NO",
                "start": str(record.get("start", "") or "").strip(),
                "end": str(record.get("end", "") or "").strip(),
                "minutes": int(float(record.get("minutes", 0) or 0)),
                "remark": remark,
            }
        )
    return enriched


def _delay_deduction_summary(records: list[dict]) -> pd.DataFrame:
    rows = [r for r in records if is_deductible_code(r.get("code"))]
    if not rows:
        return pd.DataFrame([{"carrier_visit": "-", "crane": "-", "deduct_minutes": 0}])
    df = pd.DataFrame(rows)
    return (
        df.groupby(["carrier_visit", "crane"], dropna=False)["minutes"]
        .sum()
        .reset_index()
        .rename(columns={"minutes": "deduct_minutes"})
        .sort_values(["carrier_visit", "crane"])
    )


def _records_without_blank_keys(df: pd.DataFrame, key: str) -> list[dict]:
    if df is None or df.empty or key not in df.columns:
        return []
    records = []
    for record in df.where(pd.notna(df), "").to_dict("records"):
        if str(record.get(key, "")).strip():
            records.append(record)
    return records


def _split_names(value: object) -> list[str]:
    names = []
    for chunk in str(value or "").replace(";", ",").split(","):
        clean = " ".join(chunk.strip().split())
        if clean and clean not in names:
            names.append(clean)
    return names


def _join_names(names: list[str]) -> str:
    clean = []
    for name in names:
        value = " ".join(str(name or "").strip().split())
        if value and value not in clean:
            clean.append(value)
    return ", ".join(clean)


def _nunique(df: pd.DataFrame, col: str) -> int:
    return int(df[col].nunique()) if col in df.columns and not df.empty else 0


def _qc_count(df: pd.DataFrame) -> int:
    if df.empty or "STS QUAY" not in df.columns:
        return 0
    return int(df["STS QUAY"].astype(str).str.extract(r"^(QC\d+)")[0].dropna().nunique())


def _auto_gate(moves: pd.DataFrame, kind: str) -> int:
    return int(moves["MOVE KIND"].eq(kind).sum()) if not moves.empty else 0


def _auto_hk(moves: pd.DataFrame) -> int:
    return int(moves["MOVE KIND"].isin(["HOUSE KEEPING", "SHIFTING"]).sum()) if not moves.empty else 0


if __name__ == "__main__":
    main()
