from __future__ import annotations

from .kpi import ReportBundle


def build_email_draft(bundle: ReportBundle, file_name: str) -> tuple[str, str]:
    shift = bundle.shift
    subject = f"SHIFT REPORT {shift.work_date.isoformat()} {shift.code}"
    cmit = bundle.summary_rows[0] if bundle.summary_rows else {}
    body = "\n".join(
        [
            "Dear Sirs,",
            "",
            f"Please find attached Shift Operation Report {shift.code}_May {shift.work_date.day}, {shift.work_date.year} as below:",
            "",
            f"- Vessel volume: {cmit.get('vessel_total', 0)} moves",
            f"- Barge volume: {cmit.get('barge_total', 0)} moves",
            f"- Overall volume: {cmit.get('overall_volume', 0)} moves",
            f"- Overall GMPH: {cmit.get('overall_gmph', '0.00')}",
            f"- Gate in/out: {bundle.gate.get('gate_in', 0)} / {bundle.gate.get('gate_out', 0)}",
            f"- Incident: {bundle.manual.get('other', {}).get('incident', 'NONE')}",
            "",
            f"Attachment: {file_name}",
            "",
            "Best Regards,",
        ]
    )
    return subject, body

