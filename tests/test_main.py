from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from meeting_summary.main import _ensure_supported_python


class MainTests(unittest.TestCase):
    def test_ensure_supported_python_allows_313(self) -> None:
        with patch("meeting_summary.main.sys.version_info", (3, 13, 2, "final", 0)):
            _ensure_supported_python()

    def test_ensure_supported_python_rejects_314(self) -> None:
        with patch("meeting_summary.main.sys.version_info", (3, 14, 0, "final", 0)):
            with self.assertRaises(SystemExit):
                _ensure_supported_python()


if __name__ == "__main__":
    unittest.main()
