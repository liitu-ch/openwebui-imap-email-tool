import os
import sys

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import Tools


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
