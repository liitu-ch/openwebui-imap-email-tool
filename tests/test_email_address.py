import os
import sys

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import EmailAddress


class TestEmailAddress:
    """Tests for EmailAddress dataclass."""

    def test_str_with_name(self):
        """Test EmailAddress __str__ with name."""
        addr = EmailAddress("John Doe", "john@example.com")
        assert str(addr) == "John Doe <john@example.com>"

    def test_str_without_name(self):
        """Test EmailAddress __str__ without name."""
        addr = EmailAddress("", "john@example.com")
        assert str(addr) == "john@example.com"

    def test_to_dict(self):
        """Test EmailAddress to_dict."""
        addr = EmailAddress("John", "john@example.com")
        assert addr.to_dict() == {"name": "John", "email": "john@example.com"}
