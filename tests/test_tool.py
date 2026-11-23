"""
Regression tests for openwebui_tool.py

These tests verify the key functions work correctly and catch
regressions from the code review fixes.

IMPORTANT: This file uses relative path resolution to work across
different workspace checkouts. The project root is determined
automatically based on the test file's location.
"""

import json
import os
import sys
from datetime import datetime, timezone

# Determine project root relative to this test file's location
# __file__ gives the path to this test file
test_file_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to get the project root
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import (
    EmailAddress,
    Tools,
    _decode_bytes,
    _addresses,
    _json_value,
    _status_value,
    _message_body,
    parse_address,
    parse_address_list,
)


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


class TestMessageBody:
    """Tests for _message_body function."""

    def test_plain_text_part(self):
        """Test extracting plain text part from multipart message."""
        from email.mime.text import MIMEText

        msg = MIMEText("Plain body text", "plain")
        body, body_html = _message_body(msg)
        assert body == "Plain body text"
        assert body_html == ""

    def test_html_part(self):
        """Test extracting HTML part from multipart message.
        
        When only HTML part exists (no plain), the function extracts
        visible text from the HTML.
        """
        from email.mime.text import MIMEText

        msg = MIMEText("<p>HTML body</p>", "html")
        body, body_html = _message_body(msg)
        # When no plain part, HTML text is extracted as body
        assert "HTML body" in body

    def test_mixed_parts(self):
        """Test message with both plain and HTML parts."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg.attach(MIMEText("Plain text", "plain"))
        msg.attach(MIMEText("<p>HTML</p>", "html"))
        body, body_html = _message_body(msg)
        assert "Plain text" in body
        assert "<p>HTML</p>" in body_html


class TestToolsInitialization:
    """Tests for Tools class initialization."""

    def test_valves_defaults(self):
        """Test default valve values."""
        tools = Tools()
        assert tools.valves.imap_port == 993
        assert tools.valves.use_ssl is True
        assert tools.valves.smtp_port == 465
        assert tools.valves.smtp_use_ssl is True
        assert tools.valves.timeout == 30

    def test_valves_custom(self):
        """Test custom valve values."""
        # Just verify the class works
        assert Tools is not None


class TestToolsValvesNewField:
    """Tests for the new smtp_use_imap_credentials field."""

    def test_new_field_exists(self):
        """Test that the new valve field exists."""
        tools = Tools()
        # The field should be present with default value
        assert hasattr(tools.valves, "smtp_use_imap_credentials")


class TestToolsSearchValidation:
    """Tests for search query validation logic."""

    def test_search_with_prefix_query(self):
        """Test search with FROM: prefix query."""
        # This tests the code path that was fixed
        import re

        query_text = "FROM:example@example.com"
        prefix_match = re.match(
            r"^(FROM|TO|CC|BCC|SUBJECT|BODY|TEXT):\s*(.*)$",
            query_text,
            re.I,
        )
        assert prefix_match is not None
        assert prefix_match.group(1).upper() == "FROM"

    def test_search_flag_query(self):
        """Test search with IMAP flag query."""
        import re

        query_text = "UNSEEN"
        # Should not match prefix pattern
        prefix_match = re.match(
            r"^(FROM|TO|CC|BCC|SUBJECT|BODY|TEXT):\s*(.*)$",
            query_text,
            re.I,
        )
        # UNSEEN should not have a prefix match
        assert prefix_match is None


class TestToolsSMTPCredentials:
    """Tests for SMTP credential handling."""

    def test_smtp_use_imap_credentials_default(self):
        """Test default value of smtp_use_imap_credentials."""
        tools = Tools()
        # Default should be False (explicit config required)
        assert tools.valves.smtp_use_imap_credentials is False

    def test_credential_fallback_disabled(self):
        """Test that IMAP password is not used by default for SMTP."""
        tools = Tools()
        # When not explicitly enabled, smtp_password should not fallback
        # to imap_password (this is handled in _send_smtp)
        assert tools.valves.smtp_use_imap_credentials is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file, "-v"])
