from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class ShiftSpec:
    work_date: date
    code: str
    start: datetime
    end: datetime

    @property
    def label(self) -> str:
        return f"{self.code} {self.work_date.strftime('%d/%m/%Y')}"

    @property
    def file_label(self) -> str:
        return f"{self.work_date.isoformat()}_{self.code}"


def make_shift(work_date: date, code: str) -> ShiftSpec:
    code = code.upper().strip()
    if code == "D1":
        start = datetime.combine(work_date, time(6, 0))
        end = datetime.combine(work_date, time(18, 0))
    elif code == "D2":
        start = datetime.combine(work_date, time(18, 0))
        end = datetime.combine(work_date + timedelta(days=1), time(6, 0))
    else:
        raise ValueError("Shift code must be D1 or D2.")
    return ShiftSpec(work_date=work_date, code=code, start=start, end=end)


def assign_shift(dt: datetime) -> ShiftSpec:
    if dt.time() >= time(18, 0):
        return make_shift(dt.date(), "D2")
    if dt.time() < time(6, 0):
        return make_shift(dt.date() - timedelta(days=1), "D2")
    return make_shift(dt.date(), "D1")


def is_in_shift(dt: datetime, shift: ShiftSpec) -> bool:
    return shift.start <= dt < shift.end


def clip_to_shift(dt: datetime, shift: ShiftSpec) -> datetime:
    if dt < shift.start:
        return shift.start
    if dt > shift.end:
        return shift.end
    return dt

