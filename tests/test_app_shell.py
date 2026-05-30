import py_compile
import unittest
from pathlib import Path


class AppShellTest(unittest.TestCase):
    def test_app_py_compiles(self):
        py_compile.compile("app.py", doraise=True)

    def test_app_has_seven_main_tabs(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for label in [
            "DASHBOARD",
            "DATA GỐC (LIST)",
            "TÀU & SÀ LAN",
            "REPORT",
            "CÀI ĐẶT",
            "NHẬT KÝ (LOGS)",
            "DELAY",
        ]:
            self.assertIn(label, source)

    def test_header_modules_are_present(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for name in [
            "render_save_changes_dialog",
            "render_delay_dialog",
            "render_guide_dialog",
            "render_version_dialog",
            "handle_uploaded_file",
            "apply_auto_report_context",
        ]:
            self.assertIn(name, source)

    def test_delay_and_version_seed_data_exist(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("DEFAULT_DELAY_CODES", source)
        self.assertIn("DEFAULT_VERSION_LOG", source)
        self.assertIn("CODE 5X", source)

    def test_delay_codes_match_source_sheet_shape(self):
        import app

        codes = [item["code"] for item in app.DEFAULT_DELAY_CODES]
        self.assertEqual(43, len(codes))
        self.assertEqual(len(codes), len(set(codes)))
        for expected in ["00", "03", "21", "27", "32A", "49B", "51", "55", "64", "71"]:
            self.assertIn(expected, codes)

        for item in app.DEFAULT_DELAY_CODES:
            self.assertEqual(item["code"].startswith("5"), item["deduct"])

    def test_delay_popup_uses_scrollable_selectable_code_list(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('key="delay_code_scroll_list"', source)
        self.assertIn("selection_mode=\"single-row\"", source)
        self.assertIn("height=220", source)
        self.assertIn("disabled=selected_code is None", source)

    def test_right_arrow_toggles_shift(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('key="report_toggle_shift"', source)
        self.assertIn("def toggle_report_shift", source)
        self.assertIn('new_shift = "D2" if current_shift == "D1" else "D1"', source)
        self.assertIn("toggle_report_shift()", source)

    def test_right_arrow_toggles_shift_in_app_state(self):
        from streamlit.testing.v1 import AppTest

        app_test = AppTest.from_file("app.py")
        app_test.run(timeout=10)
        before = app_test.selectbox(key="shift_code_widget").value

        app_test.button(key="report_toggle_shift").click().run(timeout=10)
        after_first_click = app_test.selectbox(key="shift_code_widget").value

        app_test.button(key="report_toggle_shift").click().run(timeout=10)
        after_second_click = app_test.selectbox(key="shift_code_widget").value

        self.assertEqual(0, len(app_test.exception))
        self.assertNotEqual(before, after_first_click)
        self.assertEqual(before, after_second_click)

    def test_dashboard_mix_panel_uses_compact_html(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('f\'<div class="mix-row"><div class="mix-label"', source)
        self.assertIn('f\'<div class="dashboard-panel">{"".join(rows)}</div>\'', source)

    def test_dashboard_kpi_cards_use_compact_html(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('f\'<div class="dashboard-kpi-card {safe_color}"><div class="kpi-title">{safe_title}</div>\'', source)
        self.assertIn('f\'<div class="kpi-value">{safe_value}</div><div class="kpi-note">{safe_note}</div></div>\'', source)


if __name__ == "__main__":
    unittest.main()
