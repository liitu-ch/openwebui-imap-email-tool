import os
import sys

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Determine project root relative to this test file's location
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)

from openwebui_tool import _message_body


class TestMessageBody:
    """Tests for _message_body function."""

    def test_plain_text_part(self):
        """Test extracting plain text part from multipart message."""
        msg = MIMEText("Plain body text", "plain")
        body, body_html = _message_body(msg)
        assert body == "Plain body text"
        assert body_html == ""

    def test_html_part(self):
        """Test extracting HTML part from multipart message.
        
        When only HTML part exists (no plain), the function extracts
        visible text from the HTML.
        """
        msg = MIMEText("<p>HTML body</p>", "html")
        body, body_html = _message_body(msg)
        # When no plain part, HTML text is extracted as body
        assert "HTML body" in body

    def test_mixed_parts(self):
        """Test message with both plain and HTML parts."""
        msg = MIMEMultipart()
        msg.attach(MIMEText("Plain text", "plain"))
        msg.attach(MIMEText("<p>HTML</p>", "html"))
        body, body_html = _message_body(msg)
        assert "Plain text" in body
        assert "<p>HTML</p>" in body_html
