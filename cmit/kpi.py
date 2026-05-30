from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from .delay_codes import describe_code, is_deductible_code, normalize_code
from .shift import ShiftSpec, clip_to_shift


PRODUCTIVE_KINDS = {"DISCHARGE", "LOAD", "RESTOW"}
REPORT_LOCATIONS = [
    "CMIT QUAY (CẦU BẾN CMIT)",
    "OCC - TCTT QUAY (CẦU TCTT LÀM HÀNG CHO CMIT)",
    "OCC - CMIT QUAY (CẨU CMIT LÀM HÀNG CHO TCTT)",
    "B3 - CMIT VESSEL (LOCKED)",
    "B3 - TCTT VESSEL (LOCKED)",
    "HUNG THAI (CẦU BẾN HƯNG THÁI)",
]
CHE_TYPES = ["QC", "RTG", "UNI", "EH", "RS", "TT"]


@dataclass
class ReportBundle:
    shift: ShiftSpec
    summary_rows: list[dict[str, Any]]
    crane_stats: dict[str, dict[str, float]]
    vessel_rows: list[dict[str, Any]]
    barge_rows: list[dict[str, Any]]
    vessel_notes: list[dict[str, Any]]
    gate: dict[str, Any]
    che: dict[str, Any]
    equipment_breakdowns: list[dict[str, Any]]
    manual: dict[str, Any]
    moves: pd.DataFrame


def calculate_report(moves: pd.DataFrame, manual: dict[str, Any], shift: ShiftSpec) -> ReportBundle:
    moves = _clean_moves(moves)
    cmit = moves[moves["LOAI CAU BEN"].eq("CMIT QUAY")].copy()
    productive = cmit[cmit["MOVE KIND"].isin(PRODUCTIVE_KINDS)].copy()

    vessel_moves = productive[productive["LOAI PTVT"].eq("VESSEL")]
    barge_moves = productive[productive["LOAI PTVT"].eq("BARGE")]
    vessel_rows = build_carrier_rows(vessel_moves, "VESSEL", manual, shift)
    barge_rows = build_carrier_rows(barge_moves, "BARGE", manual, shift)
    summary_rows = build_summary_rows(vessel_moves, barge_moves, vessel_rows, barge_rows)
    crane_stats = build_crane_stats(vessel_rows, barge_rows, manual)
    gate = build_gate_summary(moves, manual)
    che = build_che_summary(moves, manual, shift)
    vessel_notes = build_vessel_notes(vessel_rows, manual)

    return ReportBundle(
        shift=shift,
        summary_rows=summary_rows,
        crane_stats=crane_stats,
        vessel_rows=vessel_rows,
        barge_rows=barge_rows,
        vessel_notes=vessel_notes,
        gate=gate,
        che=che,
        equipment_breakdowns=manual.get("equipment_breakdowns", []),
        manual=manual,
        moves=moves,
    )


def build_carrier_rows(moves: pd.DataFrame, transport_type: str, manual: dict[str, Any], shift: ShiftSpec) -> list[dict[str, Any]]:
    if moves.empty:
        return []
    rows: list[dict[str, Any]] = []
    delay_minutes = _delay_minutes(manual)
    call_map = {str(v.get("carrier_visit", "")).strip(): v for v in manual.get("vessel_calls", [])}

    for carrier, carrier_df in moves.groupby("CARRIER VISIT", dropna=False):
        carrier = str(carrier or "").strip()
        if not carrier:
            continue
        crane_rows = []
        for crane, crane_df in carrier_df.groupby("STS QUAY", dropna=False):
            crane = str(crane or "").strip() or "NO QC"
            row = _stats_row(carrier, crane, crane_df, shift)
            row["net_hours"] = max(row["gross_hours"] - delay_minutes.get((carrier, crane), 0) / 60, 0)
            row["gmph"] = _rate(row["moves"], row["net_hours"])
            row["remarks"] = _delay_remarks(manual, carrier, crane)
            row["is_all"] = False
            crane_rows.append(row)

        all_row = _stats_row(carrier, "ALL", carrier_df, shift)
        all_row["gross_hours"] = round(sum(r["gross_hours"] for r in crane_rows), 2)
        all_row["net_hours"] = max(all_row["gross_hours"] - delay_minutes.get((carrier, "ALL"), 0) / 60, 0)
        all_row["gmph"] = _rate(all_row["moves"], all_row["net_hours"])
        all_row["remarks"] = _delay_remarks(manual, carrier, "ALL")
        all_row["is_all"] = True
        all_row["transport_type"] = transport_type
        call = call_map.get(carrier, {})
        all_row["carrier_name"] = _display_carrier(carrier, call, transport_type)
        all_row["pmph"] = call.get("pmph") or "--"
        all_row["bmph"] = call.get("bmph") or "--"
        rows.append(all_row)

        for row in sorted(crane_rows, key=lambda r: r["crane"]):
            row["transport_type"] = transport_type
            row["carrier_name"] = ""
            row["pmph"] = "--"
            row["bmph"] = "--"
            rows.append(row)

    return sorted(rows, key=lambda r: (r["first_lift"] or datetime.max, not r["is_all"], r["carrier_visit"], r["crane"]))


def build_summary_rows(vessel_moves: pd.DataFrame, barge_moves: pd.DataFrame, vessel_rows: list[dict[str, Any]], barge_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cmit = _summary_row("CMIT QUAY (CẦU BẾN CMIT)", vessel_moves, barge_moves, vessel_rows, barge_rows)
    rows = [cmit]
    for name in REPORT_LOCATIONS[1:]:
        rows.append(
            {
                "location": name,
                "cranes": "-",
                "vessel_disch": "-",
                "vessel_load": "-",
                "vessel_restow": "-",
                "vessel_total": "-",
                "vessel_gmph": "0.00",
                "barge_disch": "-",
                "barge_load": "-",
                "barge_total": "-",
                "barge_gmph": "0.00",
                "overall_volume": "-",
                "overall_gmph": "0.00",
            }
        )
    return rows


def build_crane_stats(vessel_rows: list[dict[str, Any]], barge_rows: list[dict[str, Any]], manual: dict[str, Any]) -> dict[str, dict[str, float]]:
    all_rows = [r for r in vessel_rows + barge_rows if r["is_all"]]
    vessel_all = [r for r in vessel_rows if r["is_all"]]
    barge_all = [r for r in barge_rows if r["is_all"]]
    total_moves = sum(int(r["moves"]) for r in all_rows)
    gross = round(sum(float(r["gross_hours"]) for r in all_rows), 2)
    delays = round(sum(float(r["gross_hours"]) - float(r["net_hours"]) for r in all_rows), 2)
    net = round(sum(float(r["net_hours"]) for r in all_rows), 2)
    return {
        "CMIT QUAY (CẦU BẾN CMIT)": {
            "total_moves": total_moves,
            "gross_hours": gross,
            "delay_hours": delays,
            "net_hours": net,
            "shift_all": _rate(total_moves, net),
            "shift_vessel": _rate(sum(int(r["moves"]) for r in vessel_all), sum(float(r["net_hours"]) for r in vessel_all)),
            "shift_barge": _rate(sum(int(r["moves"]) for r in barge_all), sum(float(r["net_hours"]) for r in barge_all)),
        }
    }


def build_gate_summary(moves: pd.DataFrame, manual: dict[str, Any]) -> dict[str, Any]:
    gate_manual = manual.get("gate", {})
    auto_in = int(moves["MOVE KIND"].eq("GATE IN").sum()) if not moves.empty else 0
    auto_out = int(moves["MOVE KIND"].eq("GATE OUT").sum()) if not moves.empty else 0
    gate_in = _int_or_default(gate_manual.get("gate_in"), auto_in)
    gate_out = _int_or_default(gate_manual.get("gate_out"), auto_out)
    total = _int_or_default(gate_manual.get("total"), gate_in + gate_out)
    return {
        **gate_manual,
        "gate_in": gate_in,
        "gate_out": gate_out,
        "total": total,
        "ttt": gate_manual.get("ttt", ""),
    }


def build_che_summary(moves: pd.DataFrame, manual: dict[str, Any], shift: ShiftSpec) -> dict[str, Any]:
    manual_che = manual.get("che", {})
    demand = {k: _safe_float(manual_che.get("demand", {}).get(k, 0)) for k in CHE_TYPES}
    bd_time = {k: _safe_float(manual_che.get("bd_time", {}).get(k, 0)) for k in CHE_TYPES}
    if not any(demand.values()) and not moves.empty:
        demand["QC"] = float(moves["STS QUAY"].astype(str).str.startswith("QC").sum() > 0) * moves["STS QUAY"].astype(str).str.extract(r"^(QC\d+)")[0].nunique()
        demand["RTG"] = moves["STS YARD"].astype(str).str.extract(r"^(RTG\d+)")[0].nunique()
        demand["UNI"] = moves["STS YARD"].astype(str).str.extract(r"^(UN\d+)")[0].nunique()
        demand["RS"] = moves["STS YARD"].astype(str).str.extract(r"^(RS\d+)")[0].nunique()
        demand["TT"] = moves["CARRY CHE NAME"].astype(str).str.extract(r"^(TT\d+)")[0].nunique()
    shift_minutes = max((shift.end - shift.start).total_seconds() / 60, 1)
    actual = {}
    availability = {}
    for kind in CHE_TYPES:
        if demand[kind] > 0:
            actual[kind] = round(max(demand[kind] - bd_time[kind] / shift_minutes, 0), 2)
            availability[kind] = round(actual[kind] / demand[kind], 4)
        else:
            actual[kind] = 0
            availability[kind] = 1.0
    return {
        "demand": demand,
        "bd_time": bd_time,
        "actual": actual,
        "availability": availability,
        "notes": manual_che.get("notes", ""),
    }


def build_vessel_notes(vessel_rows: list[dict[str, Any]], manual: dict[str, Any]) -> list[dict[str, Any]]:
    calls = {str(v.get("carrier_visit", "")).strip(): v for v in manual.get("vessel_calls", [])}
    notes = []
    for row in [r for r in vessel_rows if r["is_all"]]:
        carrier = row["carrier_visit"]
        call = calls.get(carrier, {})
        notes.append(
            {
                "carrier_visit": carrier,
                "header": _display_carrier(carrier, call, "VESSEL").replace(" (TRONG CA)", ""),
                "service": call.get("service", ""),
                "vessel_name": call.get("vessel_name", carrier),
                "first_line": call.get("first_line", ""),
                "all_line_fast": call.get("all_line_fast", ""),
                "gangway_secure": call.get("gangway_secure", ""),
                "etc": call.get("etc", ""),
                "etd": call.get("etd", ""),
                "first_lift": row["first_lift"],
                "last_lift": row["last_lift"],
                "lashing_finish": call.get("lashing_finish", ""),
                "last_line": call.get("last_line", ""),
                "total_volume": f"TOTAL:{row['moves']}   [ D:{row['disch']} / L:{row['load']} / R:{row['restow']} ]",
                "ait": call.get("ait", ""),
                "ait2": call.get("ait2", ""),
                "dit": call.get("dit", ""),
                "gmph": row["gmph"],
                "bmph": call.get("bmph", "--"),
                "pmph": call.get("pmph", "--"),
                "moves_completed": f"TOTAL:{row['moves']}   [ D:{row['disch']} / L:{row['load']} / R:{row['restow']} ]",
                "remaining_moves": call.get("remaining_moves", "TOTAL:0   [ D:0 / L:0 / R:0 ]"),
                "shift_productivity": row["gmph"],
                "operation_notes": call.get("operation_notes", manual.get("other", {}).get("operation_notes", "Safe operation")),
                "challenges": call.get("challenges", "NIL"),
                "resolution": call.get("resolution", "NIL"),
                "further_remarks": call.get("further_remarks", ""),
            }
        )
    return notes


def _summary_row(location: str, vessel_moves: pd.DataFrame, barge_moves: pd.DataFrame, vessel_rows: list[dict[str, Any]], barge_rows: list[dict[str, Any]]) -> dict[str, Any]:
    vessel_all = [r for r in vessel_rows if r["is_all"]]
    barge_all = [r for r in barge_rows if r["is_all"]]
    vessel_net = sum(float(r["net_hours"]) for r in vessel_all)
    barge_net = sum(float(r["net_hours"]) for r in barge_all)
    vessel_total = _move_total(vessel_moves)
    barge_total = _move_total(barge_moves)
    cranes = pd.concat([vessel_moves, barge_moves])["STS QUAY"].astype(str).str.extract(r"^(QC\d+)")[0].dropna().nunique() if (not vessel_moves.empty or not barge_moves.empty) else 0
    return {
        "location": location,
        "cranes": cranes or "-",
        "vessel_disch": _move_count(vessel_moves, "DISCHARGE"),
        "vessel_load": _move_count(vessel_moves, "LOAD"),
        "vessel_restow": _move_count(vessel_moves, "RESTOW"),
        "vessel_total": vessel_total,
        "vessel_gmph": _fmt_rate(_rate(vessel_total, vessel_net)),
        "barge_disch": _move_count(barge_moves, "DISCHARGE"),
        "barge_load": _move_count(barge_moves, "LOAD"),
        "barge_total": barge_total,
        "barge_gmph": _fmt_rate(_rate(barge_total, barge_net)),
        "overall_volume": vessel_total + barge_total,
        "overall_gmph": _fmt_rate(_rate(vessel_total + barge_total, vessel_net + barge_net)),
    }


def _stats_row(carrier: str, crane: str, df: pd.DataFrame, shift: ShiftSpec) -> dict[str, Any]:
    first = min(clip_to_shift(x.to_pydatetime(), shift) for x in pd.to_datetime(df["TIME STS QUAY"]).dropna())
    last = max(clip_to_shift(x.to_pydatetime(), shift) for x in pd.to_datetime(df["TIME STS QUAY"]).dropna())
    gross = _span_hours(first, last)
    moves = _move_total(df)
    return {
        "carrier_visit": carrier,
        "carrier_name": carrier,
        "crane": crane,
        "first_lift": first,
        "last_lift": last,
        "gross_hours": gross,
        "net_hours": gross,
        "moves": moves,
        "disch": _move_count(df, "DISCHARGE"),
        "load": _move_count(df, "LOAD"),
        "restow": _move_count(df, "RESTOW"),
        "gmph": _rate(moves, gross),
        "pmph": "--",
        "bmph": "--",
        "remarks": "",
        "is_all": False,
    }


def _clean_moves(moves: pd.DataFrame) -> pd.DataFrame:
    if moves is None or moves.empty:
        return pd.DataFrame(columns=["MOVE KIND", "LOAI PTVT", "LOAI CAU BEN", "STS QUAY", "STS YARD", "CARRY CHE NAME", "TIME STS QUAY", "CARRIER VISIT"])
    out = moves.copy()
    for col in ["MOVE KIND", "LOAI PTVT", "LOAI CAU BEN", "STS QUAY", "STS YARD", "CARRY CHE NAME", "CARRIER VISIT"]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str).str.strip().str.upper()
    out["TIME STS QUAY"] = pd.to_datetime(out["TIME STS QUAY"], errors="coerce")
    return out.dropna(subset=["TIME STS QUAY"])


def _move_count(df: pd.DataFrame, kind: str) -> int:
    return int(df["MOVE KIND"].eq(kind).sum()) if not df.empty else 0


def _move_total(df: pd.DataFrame) -> int:
    return int(df["MOVE KIND"].isin(PRODUCTIVE_KINDS).sum()) if not df.empty else 0


def _span_hours(first: datetime, last: datetime) -> float:
    seconds = max((last - first).total_seconds(), 60)
    return round(seconds / 3600, 2)


def _rate(moves: float, hours: float) -> float:
    return round(float(moves) / float(hours), 2) if hours and hours > 0 else 0.0


def _fmt_rate(value: float) -> str:
    return f"{value:.2f}"


def _safe_float(value: Any) -> float:
    try:
        if value in (None, "", "-"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int_or_default(value: Any, default: int) -> int:
    try:
        if value in (None, "", 0, "0"):
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _display_carrier(carrier: str, call: dict[str, Any], transport_type: str) -> str:
    vessel_name = str(call.get("vessel_name", "")).strip()
    voyage = str(call.get("voyage", "")).strip() or carrier
    if vessel_name and vessel_name.upper() != carrier.upper():
        base = f"{vessel_name} / {voyage}"
    else:
        base = carrier
    return f"{base} (TRONG CA)" if transport_type == "VESSEL" else base


def _delay_minutes(manual: dict[str, Any]) -> dict[tuple[str, str], float]:
    delays: dict[tuple[str, str], float] = defaultdict(float)
    for delay in manual.get("delays", []):
        if not is_deductible_code(delay.get("code")):
            continue
        carrier = str(delay.get("carrier_visit", "")).strip().upper()
        crane = str(delay.get("crane", "ALL")).strip().upper() or "ALL"
        minutes = _safe_float(delay.get("minutes"))
        if carrier and minutes:
            delays[(carrier, crane)] += minutes
    return delays


def _delay_remarks(manual: dict[str, Any], carrier: str, crane: str) -> str:
    chunks = []
    for delay in manual.get("delays", []):
        if str(delay.get("carrier_visit", "")).strip().upper() != carrier.upper():
            continue
        d_crane = str(delay.get("crane", "ALL")).strip().upper() or "ALL"
        if d_crane not in {crane.upper(), "ALL"}:
            continue
        code = normalize_code(delay.get("code", ""))
        start = str(delay.get("start", "")).strip()
        end = str(delay.get("end", "")).strip()
        remark = str(delay.get("remark", "")).strip() or describe_code(code)
        minutes = str(delay.get("minutes", "")).strip()
        period = f"[{start} - {end}] " if start or end else ""
        tag = "DEDUCTION" if is_deductible_code(code) else "DELAY"
        chunks.append(f"{period}{tag}: {code} - {remark} ({minutes}')".strip())
    return "\n".join(chunks)
