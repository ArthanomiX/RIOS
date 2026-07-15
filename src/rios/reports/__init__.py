"""Report generation: Word (.docx) and JSON exports of an accepted gap."""

from rios.reports.docx_report import build_gap_report_docx
from rios.reports.json_report import build_gap_report_json

__all__ = ["build_gap_report_docx", "build_gap_report_json"]

