from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DelayCode:
    code: str
    description: str
    group: str

    @property
    def is_deductible(self) -> bool:
        return self.code.startswith("CODE 5")


DELAY_CODES: list[DelayCode] = [
    DelayCode("CODE 00", "First Move date/time (HC, gearbox) - ngay/thoi gian nap ham/thung gu dau tien do xuong", "0X Milestone"),
    DelayCode("CODE 01", "First Container (container dau tien)", "0X Milestone"),
    DelayCode("CODE 02", "Last Container (container cuoi cung)", "0X Milestone"),
    DelayCode("CODE 03", "Last Move date/time (HC, gearbox) - ngay/thoi gian nap ham/thung gu cuoi cung xep len tau", "0X Milestone"),
    DelayCode("CODE 21", "Gantry Fault (loi gantry)", "2X Crane Breakdown"),
    DelayCode("CODE 22", "Trolley Fault (loi trolley)", "2X Crane Breakdown"),
    DelayCode("CODE 23", "Hoist Fault (loi hoist)", "2X Crane Breakdown"),
    DelayCode("CODE 24", "Spreader Fault (loi ngang chup)", "2X Crane Breakdown"),
    DelayCode("CODE 25", "Boom Up/Down Fault (loi nang/ha boom)", "2X Crane Breakdown"),
    DelayCode("CODE 26", "Power Fault (loi nguon)", "2X Crane Breakdown"),
    DelayCode("CODE 27", "Spreader Replace (thay ngang chup)", "2X Crane Breakdown"),
    DelayCode("CODE 31", "Crane Sequence Changed (thay doi thu tu lam viec cua QC)", "3X/4X Operational"),
    DelayCode("CODE 32", "Lashing/Unlashing (chang/thao day chang buoc, thao day gu)", "3X/4X Operational"),
    DelayCode("CODE 32A", "Delay due to no lasher available for unlashing at high tiers", "3X/4X Operational"),
    DelayCode("CODE 33", "Crane Clash (QC choan vi tri lam viec)", "3X/4X Operational"),
    DelayCode("CODE 34", "Boom Up/Down across accommodation", "3X/4X Operational"),
    DelayCode("CODE 35", "Yard CHE breakdown (RTG/RS/FL bi hong)", "3X/4X Operational"),
    DelayCode("CODE 36", "Hatch Cover Move (nang ha nap ham)", "3X/4X Operational"),
    DelayCode("CODE 37", "Yard rehandle (sap xep lai trong bai container)", "3X/4X Operational"),
    DelayCode("CODE 38", "Yard clash (xe tai/RTG bi nghen trong bai container)", "3X/4X Operational"),
    DelayCode("CODE 39", "Jammed Twistlock (dinh gu khi do/xep container)", "3X/4X Operational"),
    DelayCode("CODE 40", "HHT / VMT Malfunction (Handheld/VMT bi loi)", "3X/4X Operational"),
    DelayCode("CODE 41", "Gear box move (doi thung gu khi dang discharge/load)", "3X/4X Operational"),
    DelayCode("CODE 42", "QC operator hot seat change (QCO thay ca nong)", "3X/4X Operational"),
    DelayCode("CODE 43", "Wrongly loaded/discharged container number or position", "3X/4X Operational"),
    DelayCode("CODE 44", "Wrong ISO Code, could not close HC properly", "3X/4X Operational"),
    DelayCode("CODE 45", "Improper stacking container on board, need correction", "3X/4X Operational"),
    DelayCode("CODE 46", "Containers sent to QCs in wrong sequence", "3X/4X Operational"),
    DelayCode("CODE 47", "Waiting for loading plan", "3X/4X Operational"),
    DelayCode("CODE 48", "Overload fault due to QCO skill", "3X/4X Operational"),
    DelayCode("CODE 49", "Twistlocks input error when loading", "3X/4X Operational"),
    DelayCode("CODE 49A", "Corner casting deformed, hard to put twistlock or sling required", "3X/4X Operational"),
    DelayCode("CODE 49B", "Other operational delay - explain", "3X/4X Operational"),
    DelayCode("CODE 51", "Gang at other vessel - actual time", "5X Deduction"),
    DelayCode("CODE 52", "Special Cargo Handling / OOG", "5X Deduction"),
    DelayCode("CODE 53", "Scheduled breaks / planned maintenance / test spreader / planned tech stop", "5X Deduction"),
    DelayCode("CODE 54", "Weather stop due to safety, wind alarm or heavy rain", "5X Deduction"),
    DelayCode("CODE 55", "Power Failure due to EVN", "5X Deduction"),
    DelayCode("CODE 61", "Accident", "6X Emergency"),
    DelayCode("CODE 62", "Power Failure due to CMIT", "6X Emergency"),
    DelayCode("CODE 63", "TOS failure", "6X Emergency"),
    DelayCode("CODE 64", "Other emergency stoppage - explain", "6X Emergency"),
    DelayCode("CODE 71", "Other delay such as vessel berthing/unberthing", "7X Other"),
]


DELAY_CODE_MAP = {item.code: item for item in DELAY_CODES}


def code_options() -> list[str]:
    return [item.code for item in DELAY_CODES]


def describe_code(code: str) -> str:
    item = DELAY_CODE_MAP.get(normalize_code(code))
    return item.description if item else ""


def delay_group(code: str) -> str:
    item = DELAY_CODE_MAP.get(normalize_code(code))
    return item.group if item else ""


def is_deductible_code(code: str) -> bool:
    item = DELAY_CODE_MAP.get(normalize_code(code))
    return bool(item and item.is_deductible)


def normalize_code(code: object) -> str:
    text = str(code or "").strip().upper()
    if not text:
        return ""
    return text if text.startswith("CODE ") else f"CODE {text}"


def as_records() -> list[dict[str, object]]:
    return [
        {
            "Code": item.code,
            "Group": item.group,
            "Deduct GMPH": "YES" if item.is_deductible else "NO",
            "Description": item.description,
        }
        for item in DELAY_CODES
    ]

