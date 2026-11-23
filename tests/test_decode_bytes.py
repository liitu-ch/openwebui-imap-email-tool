import os
import sys

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import _decode_bytes


class TestDecodeBytes:
    """Tests for _decode_bytes helper."""

    def test_bytes_decode(self):
        """Test decoding bytes to string."""
        result = _decode_bytes(b"hello")
        assert result == "hello"

    def test_string_return(self):
        """Test string is returned as-is."""
        result = _decode_bytes("hello")
        assert result == "hello"
