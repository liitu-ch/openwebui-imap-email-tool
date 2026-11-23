import os
import sys

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import _addresses, parse_address, parse_address_list


class TestAddresses:
    """Tests for _addresses helper."""

    def test_single_address(self):
        """Test parsing single address."""
        result = _addresses("John Doe <john@example.com>")
        assert len(result) == 1
        assert result[0] == "john@example.com"

    def test_multiple_addresses(self):
        """Test parsing multiple addresses."""
        result = _addresses("Alice <alice@example.com>, Bob <bob@example.com>")
        assert len(result) == 2

    def test_empty_string(self):
        """Test empty string returns empty list."""
        result = _addresses("")
        assert result == []


class TestParseAddress:
    """Tests for parse_address function."""

    def test_parse_with_name(self):
        """Test parsing address with display name."""
        result = parse_address('"John Doe" <john@example.com>')
        assert result.name == "John Doe"
        assert result.email == "john@example.com"

    def test_parse_without_name(self):
        """Test parsing address without display name."""
        result = parse_address("john@example.com")
        assert result.name == ""
        assert result.email == "john@example.com"


class TestParseAddressList:
    """Tests for parse_address_list function."""

    def test_parse_with_quoted_comma(self):
        """Test parsing addresses with quoted names containing commas."""
        result = parse_address_list('"John, Doe" <john@example.com>')
        assert len(result) == 1
        assert result[0].name == "John, Doe"

    def test_parse_multiple(self):
        """Test parsing multiple addresses."""
        result = parse_address_list(
            '"John Doe" <john@example.com>, "Jane Smith" <jane@example.com>'
        )
        assert len(result) == 2
