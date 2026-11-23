import os
import sys

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import _status_value


class TestStatusValue:
    """Tests for _status_value helper."""

    def test_normal_value(self):
        """Test normal integer value extraction."""
        status = {"MESSAGES": 100}
        result = _status_value(status, "MESSAGES")
        assert result == 100

    def test_missing_key(self):
        """Test missing key returns default."""
        status = {}
        result = _status_value(status, "NONEXISTENT", default_value=0)
        assert result == 0

    def test_encoded_key(self):
        """Test lookup with encoded key."""
        status = {b"MESSAGES": 50}
        result = _status_value(status, "MESSAGES")
        assert result == 50

    def test_list_value(self):
        """Test list value extraction takes first element."""
        status = {"MESSAGES": [100, 200]}
        result = _status_value(status, "MESSAGES")
        assert result == 100

    def test_default_value(self):
        """Test default value when conversion fails."""
        status = {"MESSAGES": "invalid"}
        result = _status_value(status, "MESSAGES", default_value=-1)
        assert result == -1
