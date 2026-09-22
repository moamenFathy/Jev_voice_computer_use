"""
Unit Tests for Autonomous Web Navigator & Link Detection.
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.accessibility_scanner import accessibility_scanner, UIElement
from src.tools.web_tool import WebNavigationTool


class TestWebNavigator(unittest.TestCase):
    def test_find_search_result_links(self):
        # Create mock elements representing a Google search result page
        mock_elements = [
            UIElement(
                id=1,
                name="Google Apps",
                control_type="Button",
                automation_id="gbwa",
                class_name="",
                left=1700,
                top=20,
                right=1750,
                bottom=60,
                width=50,
                height=40,
                center_x=1725,
                center_y=40,
                is_enabled=True,
                is_visible=True,
                value=None,
                raw_control=None,
            ),
            UIElement(
                id=2,
                name="National Bank of Egypt - البنك الأهلي المصري",
                control_type="Hyperlink",
                automation_id="rso_link_1",
                class_name="",
                left=180,
                top=220,
                right=600,
                bottom=260,
                width=420,
                height=40,
                center_x=390,
                center_y=240,
                is_enabled=True,
                is_visible=True,
                value=None,
                raw_control=None,
            ),
            UIElement(
                id=3,
                name="All",
                control_type="Hyperlink",
                automation_id="tab_all",
                class_name="",
                left=180,
                top=140,
                right=240,
                bottom=170,
                width=60,
                height=30,
                center_x=210,
                center_y=155,
                is_enabled=True,
                is_visible=True,
                value=None,
                raw_control=None,
            ),
        ]

        top_link = accessibility_scanner.find_search_result_links(mock_elements, query_hint="البنك الاهلي")
        self.assertIsNotNone(top_link)
        self.assertEqual(top_link.name, "National Bank of Egypt - البنك الأهلي المصري")
        self.assertEqual(top_link.control_type, "Hyperlink")


if __name__ == "__main__":
    unittest.main()
