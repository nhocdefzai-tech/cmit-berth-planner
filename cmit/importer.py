from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from .shift import ShiftSpec, assign_shift, is_in_shift


DATA_COLUMNS = [
    "UNIT NBR",
    "MOVE KIND",
    "CARRIER VISIT",
    "CA",
    "LOAI PTVT",
    "LOAI CAU BEN",
    "STS QUAY",
    "TIME STS QUAY",
    "GAP DELAY",
    "REASON",
    "TIME COMPLETED",
    "PUT CHE NAME",
    "TIME OF FETCH",
    "FETCH CHE NAME",
    "CARRY CHE NAME",
    "FROM POSITION",
    "TO POSITION",
    "UNIT TYPE ISO",
    "UNIT VGM VERIFIED",
    "LINE OP",
    "STS YARD",
    "STS YARD TIME",
    "STS CARRY",
    "STS CARRY START TIME",
    "STS CARRY END TIME",
    "RESTOW REASON",
    "TEU",
]

MOVE_KIND_MAP = {
    "LOAD": "LOAD",
    "DISCHARGE": "DISCHARGE",
    "RESTOW": "RESTOW",
    "RESTOW DISCHARGE": "RESTOW",
    "RESTOW LOAD": "RESTOW",
    "SLING": "RESTOW",
    "RECEIVAL": "GATE IN",
    "RECEIVE": "GATE IN",
    "DELIVERY": "GATE OUT",
    "YARD MOVE": "HOUSE KEEPING",
    "HOUSE KEEPING": "HOUSE KEEPING",
    "SHIFTING": "SHIFTING",
    "GATE IN": "GATE IN",
    "GATE OUT": "GATE OUT",
}

VESSEL_PATTERN = re.compile(r"^[A-Z]{2,5}\d{2,4}[A-Z]?$")
BARGE_PATTERN = re.compile(r"^(CM|TN|SW|SG|SPC|DL|PL|DN|HG|HT)\d", re.IGNORECASE)


def read_move_file(path: str | Path, shift: ShiftSpec | None = None) -> pd.DataFrame:
    """Read either a raw N4 MoveEvent export or an already-normalized DATA sheet."""
    path = Path(path)
    data_df = _try_read_data_sheet(path)
    if data_df is not None:
        normalized = normalize_data_sheet(data_df)
    else:
        raw_df = _read_raw_n4(path)
        normalized = normalize_raw_n4(raw_df)

    normalized = _coerce_datetime_columns(normalized)
    if shift is not None and not normalized.empty:
        normalized = normalized[
            normalized["TIME STS QUAY"].apply(lambda x: pd.notna(x) and is_in_shift(x.to_pydatetime(), shift))
        ].copy()
        normalized["CA"] = shift.label
    return normalized.reset_index(drop=True)


def normalize_move_kind(value: object) -> str:
    key = str(value or "").strip().upper()
    return MOVE_KIND_MAP.get(key, key)


def normalize_data_sheet(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    rename = {c: c for c in df.columns}
    df = df.rename(columns=rename)
    for col in DATA_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df["MOVE KIND"] = df["MOVE KIND"].apply(normalize_move_kind)
    df["TEU"] = df["TEU"].fillna(df["UNIT TYPE ISO"].apply(iso_to_teu))
    return df[DATA_COLUMNS]


def normalize_raw_n4(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for required in ["Move Kind", "Time Completed"]:
        if required not in df.columns:
            raise ValueError(f"Missing required N4 column: {required}")

    completed = parse_n4_datetime(df["Time Completed"])
    fetched = parse_n4_datetime(df["Time of Fetch"]) if "Time of Fetch" in df.columns else pd.NaT
    carrier = _series(df, "Carrier Visit").astype(str).str.strip().replace({"nan": ""})
    move_kind = _series(df, "Move Kind").apply(normalize_move_kind)
    put_che = _series(df, "Put CHE Name")
    fetch_che = _series(df, "Fetch CHE Name")
    carry_che = _series(df, "Carry CHE Name")
    unit_iso = _series(df, "Unit Type ISO")
    unit_nbr = _series(df, "Unit Nbr")

    out = pd.DataFrame()
    out["UNIT NBR"] = unit_nbr
    out["MOVE KIND"] = move_kind
    out["CARRIER VISIT"] = carrier
    out["CA"] = completed.apply(lambda x: assign_shift(x.to_pydatetime()).label if pd.notna(x) else "")
    out["LOAI PTVT"] = [
        classify_transport(mk, cv, fp, tp)
        for mk, cv, fp, tp in zip(move_kind, carrier, _series(df, "From Position"), _series(df, "To Position"))
    ]
    out["LOAI CAU BEN"] = [classify_location(mk, lp) for mk, lp in zip(move_kind, out["LOAI PTVT"])]
    out["STS QUAY"] = [
        choose_quay_che(mk, put, fetch) for mk, put, fetch in zip(move_kind, put_che, fetch_che)
    ]
    out["TIME STS QUAY"] = completed
    out["GAP DELAY"] = None
    out["REASON"] = None
    out["TIME COMPLETED"] = completed
    out["PUT CHE NAME"] = put_che
    out["TIME OF FETCH"] = fetched
    out["FETCH CHE NAME"] = fetch_che
    out["CARRY CHE NAME"] = carry_che
    out["FROM POSITION"] = _series(df, "From Position")
    out["TO POSITION"] = _series(df, "To Position")
    out["UNIT TYPE ISO"] = unit_iso
    out["UNIT VGM VERIFIED"] = _series(df, "Unit VGM Verified ?")
    out["LINE OP"] = _series(df, "Line Op")
    out["STS YARD"] = [choose_yard_che(put, fetch) for put, fetch in zip(put_che, fetch_che)]
    out["STS YARD TIME"] = completed
    out["STS CARRY"] = carry_che
    out["STS CARRY START TIME"] = fetched
    out["STS CARRY END TIME"] = completed
    out["RESTOW REASON"] = _series(df, "Restow Reason")
    out["TEU"] = unit_iso.apply(iso_to_teu)
    return out[DATA_COLUMNS].dropna(subset=["TIME STS QUAY"]).reset_index(drop=True)


def parse_n4_datetime(series: Iterable[object]) -> pd.Series:
    s = pd.Series(series).astype(str).str.strip()
    cleaned = s.str.replace(":", "", regex=False)
    parsed = pd.to_datetime(cleaned, format="%d-%b-%y %H%M", errors="coerce")
    fallback = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%b-%y %H:%M"):
        mask = parsed.isna() & fallback.isna() & ~s.str.lower().isin(["", "nan", "none"])
        if not mask.any():
            break
        fallback.loc[mask] = pd.to_datetime(s.loc[mask], format=fmt, errors="coerce")
    return parsed.fillna(fallback)


def iso_to_teu(value: object) -> int:
    text = str(value or "").strip()
    return 1 if text.startswith("2") else 2


def classify_transport(move_kind: str, carrier_visit: str, from_pos: object, to_pos: object) -> str:
    if move_kind in {"GATE IN", "GATE OUT", "HOUSE KEEPING", "SHIFTING"}:
        return ""
    cv = str(carrier_visit or "").strip().upper()
    if not cv or cv.startswith("GATE") or cv.startswith("INFO"):
        return ""
    if cv[0].isdigit():
        return ""
    if BARGE_PATTERN.match(cv) or "W22A" in cv or "C3" in cv:
        return "BARGE"
    if VESSEL_PATTERN.match(cv):
        return "VESSEL"
    # Conservative default for long N4 carrier visits common in barge operations.
    return "BARGE" if len(cv) > 8 else "VESSEL"


def classify_location(move_kind: str, transport_type: str) -> str:
    if move_kind in {"GATE IN", "GATE OUT"}:
        return "GATE"
    if move_kind in {"HOUSE KEEPING", "SHIFTING"}:
        return "YARD"
    if transport_type in {"VESSEL", "BARGE"}:
        return "CMIT QUAY"
    return ""


def choose_quay_che(move_kind: str, put_che: object, fetch_che: object) -> str:
    for value in (put_che, fetch_che):
        text = str(value or "").strip().upper()
        if text.startswith("QC"):
            return text
    return ""


def choose_yard_che(put_che: object, fetch_che: object) -> str:
    for value in (put_che, fetch_che):
        text = str(value or "").strip().upper()
        if text and not text.startswith("QC") and text != "NAN":
            return text
    return ""


def _try_read_data_sheet(path: Path) -> pd.DataFrame | None:
    try:
        xls = pd.ExcelFile(path)
        if "DATA" not in xls.sheet_names:
            return None
        df = pd.read_excel(path, sheet_name="DATA")
        headers = {str(c).strip().upper() for c in df.columns}
        return df if {"MOVE KIND", "TIME COMPLETED"}.issubset(headers) else None
    except Exception:
        return None


def _read_raw_n4(path: Path) -> pd.DataFrame:
    for skiprows in (4, 0):
        df = pd.read_excel(path, skiprows=skiprows)
        headers = {str(c).strip() for c in df.columns}
        if {"Move Kind", "Time Completed"}.issubset(headers):
            return df
    raise ValueError("File is not recognized as a raw N4 MoveEvent file or normalized DATA workbook.")


def _series(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series([None] * len(df))


def _coerce_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["TIME STS QUAY", "TIME COMPLETED", "TIME OF FETCH", "STS YARD TIME", "STS CARRY START TIME", "STS CARRY END TIME"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df
