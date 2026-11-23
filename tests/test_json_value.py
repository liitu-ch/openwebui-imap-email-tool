import os
import sys
from datetime import datetime, timezone

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import _json_value


class TestJsonValue:
    """Tests for _json_value helper."""

    def test_bytes_to_string(self):
        """Test bytes are decoded to string."""
        result = _json_value(b"hello")
        assert result == "hello"

    def test_datetime_isoformat(self):
        """Test datetime is converted to ISO format."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _json_value(dt)
        assert "2024-01-15T10:30:00+00:00" in result

    def test_list_recursion(self):
        """Test list recursion."""
        result = _json_value([1, 2, 3])
        assert result == [1, 2, 3]

    def test_dict_recursion(self):
        """Test dict recursion with byte keys."""
        result = _json_value({b"key": "value"})
        assert result == {"key": "value"}

    def test_plain_value(self):
        """Test plain values pass through."""
        result = _json_value(42)
        assert result == 42
