"""
title: IMAP Email Tool
author:
 - Sandro Scalco - liitu consulting gmbh
 - Patrik Gfeller, Code-Omega Solutions
description: Access and manage emails via IMAP/SMTP. Search, read, compose, and send emails.
version: 0.3.0
required_open_webui_version: 0.4.0
requirements: imapclient
"""

import json
import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import BytesParser
from email.policy import default
from email.utils import (
    formataddr,
    formatdate,
    getaddresses,
    make_msgid,
    parseaddr,
    parsedate_to_datetime,
)
from html.parser import HTMLParser
from typing import Optional

from imapclient import IMAPClient
from pydantic import BaseModel, Field


@dataclass
class EmailAddress:
    """Parsed email address."""

    name: str
    email: str

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email

    def to_dict(self) -> dict:
        return {"name": self.name, "email": self.email}


def decode_mime_header(header: Optional[str]) -> str:
    """Decode MIME header fragments, replacing invalid characters."""
    if not header:
        return ""

    decoded_parts = []
    for part, charset in decode_header(header):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            except LookupError:
                decoded_parts.append(part.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(part)

    return "".join(decoded_parts)


def parse_address(addr_str: Optional[str]) -> EmailAddress:
    """Parse a single display name and email address."""
    if not addr_str:
        return EmailAddress("", "")

    name, email_addr = parseaddr(addr_str)
    return EmailAddress(decode_mime_header(name), email_addr)


def parse_address_list(addr_str: Optional[str]) -> list[EmailAddress]:
    """Parse addresses, including quoted names containing commas."""
    if not addr_str:
        return []

    return [
        EmailAddress(decode_mime_header(name), address)
        for name, address in getaddresses([addr_str])
        if name or address
    ]


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in ("script", "style"):
            self._hidden_depth += 1
        elif tag.lower() in ("br", "p", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style") and self._hidden_depth:
            self._hidden_depth -= 1
        elif tag.lower() in ("p", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


def _decode_bytes(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _addresses(value: str) -> list[str]:
    return [address for _, address in getaddresses([value]) if address]


def _message_body(message) -> tuple[str, str]:
    """Extract plain text and HTML body from an email message."""
    plain_parts = []
    html_parts = []

    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue

        content_type = part.get_content_type().lower()
        if content_type not in ("text/plain", "text/html"):
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            content = part.get_payload()
            text = content if isinstance(content, str) else ""
        else:
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")

        target = plain_parts if content_type == "text/plain" else html_parts
        target.append(text)

    html_body = "\n".join(html_parts)

    if plain_parts:
        body = "\n".join(plain_parts)
    elif html_body:
        parser = _HTMLTextParser()
        parser.feed(html_body)
        # Improved text extraction: normalize whitespace
        text = "".join(parser.parts)
        # Replace multiple spaces/tabs on newlines with single newline
        text = re.sub(r"[ \t]+\n", "\n", text)
        # Collapse 3+ consecutive newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        body = text
    else:
        body = ""

    return body, html_body


def _json_value(value):
    if isinstance(value, bytes):
        return _decode_bytes(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {_decode_bytes(key): _json_value(item) for key, item in value.items()}
    return value


def _status_value(status: dict, key: str, default_value: int = 0) -> int:
    value = status.get(
        key,
        status.get(key.encode(), default_value),
    )
    if isinstance(value, (list, tuple)) and value:
        value = value[0]

    try:
        return int(value)
    except (TypeError, ValueError):
        return default_value


class Tools:
    """IMAP Email Tool for Open WebUI."""

    class Valves(BaseModel):
        imap_host: str = Field(default="")
        imap_port: int = Field(default=993, ge=1, le=65535)
        imap_username: str = Field(default="")
        imap_password: str = Field(default="")
        use_ssl: bool = Field(default=True)

        accept_self_signed_certificates: bool = Field(
            default=False,
            title="Accept self signed certificates",
            description=(
                "Allow unverified TLS certificates for IMAP and SMTP. "
                "Disables certificate-chain and hostname verification; "
                "enable only for trusted servers."
            ),
        )

        smtp_use_imap_credentials: bool = Field(
            default=False,
            title="Use IMAP credentials for SMTP",
            description=(
                "Fallback to IMAP password for SMTP authentication "
                "if SMTP password is not explicitly configured."
            ),
        )

        smtp_host: str = Field(default="")
        smtp_port: int = Field(default=465, ge=1, le=65535)
        smtp_username: str = Field(default="")
        smtp_password: str = Field(default="")
        smtp_use_ssl: bool = Field(default=True)
        smtp_starttls: bool = Field(default=False)

        timeout: int = Field(default=30, ge=1, le=300)

    def __init__(self):
        self.valves = self.Valves()

    def _get_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        if self.valves.accept_self_signed_certificates:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _get_smtp_host(self) -> str:
        if self.valves.smtp_host:
            return self.valves.smtp_host
        if self.valves.imap_host.startswith("imap."):
            return "smtp." + self.valves.imap_host[5:]
        return self.valves.imap_host

    def _get_sender_email(self) -> str:
        _, address = parseaddr(self.valves.imap_username)
        return address or self.valves.imap_username

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        in_reply_to: str = "",
        references: str = "",
        html_body: str = "",
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        sender = parse_address(self._get_sender_email())

        msg["From"] = (
            formataddr((sender.name, sender.email)) if sender.name else sender.email
        )
        msg["To"] = to

        if cc:
            msg["Cc"] = cc

        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=False)
        msg["Message-ID"] = make_msgid()

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        msg.attach(MIMEText(body or "", "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        return msg

    def _get_client(self) -> IMAPClient:
        if (
            not self.valves.imap_host
            or not self.valves.imap_username
            or not self.valves.imap_password
        ):
            raise ValueError("IMAP not configured.")

        client = IMAPClient(
            self.valves.imap_host,
            port=self.valves.imap_port,
            ssl=self.valves.use_ssl,
            ssl_context=self._get_ssl_context(),
            timeout=self.valves.timeout,
        )

        try:
            client.login(
                self.valves.imap_username,
                self.valves.imap_password,
            )
            return client
        except Exception:
            try:
                client.logout()
            except Exception:
                pass
            raise

        return client

    def list_folders(self) -> str:
        """List email folders with message and unread counts."""
        try:
            client = self._get_client()
            try:
                folders = []

                for flags, delimiter, name in client.list_folders():
                    folder_name = _decode_bytes(name)
                    status = client.folder_status(
                        folder_name,
                        ["MESSAGES", "UNSEEN"],
                    )

                    folders.append(
                        {
                            "name": folder_name,
                            "delimiter": (
                                _decode_bytes(delimiter)
                                if delimiter is not None
                                else None
                            ),
                            "flags": [_decode_bytes(flag) for flag in (flags or [])],
                            "messages": _status_value(status, "MESSAGES"),
                            "unseen": _status_value(status, "UNSEEN"),
                        }
                    )

                return json.dumps(
                    {"folders": folders},
                    ensure_ascii=False,
                )
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"error": str(e)})

    def search_emails(
        self,
        query: str = "ALL",
        folder: str = "INBOX",
        limit: int = 10,
    ) -> str:
        """Search using a single IMAP flag or a supported field prefix."""
        try:
            if limit < 1:
                raise ValueError("limit must be greater than zero.")

            query_text = (query or "ALL").strip()
            prefix_match = re.match(
                r"^(FROM|TO|CC|BCC|SUBJECT|BODY|TEXT):\s*(.*)$",
                query_text,
                re.I,
            )

            if prefix_match:
                criterion = [
                    prefix_match.group(1).upper(),
                    prefix_match.group(2).strip(),
                ]
                if not criterion[1]:
                    raise ValueError("Search value must not be empty.")
            else:
                criterion = query_text.split()
                if not criterion:
                    criterion = ["ALL"]
                allowed = {
                    "ALL",
                    "ANSWERED",
                    "DELETED",
                    "DRAFT",
                    "FLAGGED",
                    "NEW",
                    "OLD",
                    "RECENT",
                    "SEEN",
                    "UNANSWERED",
                    "UNDELETED",
                    "UNDRAFT",
                    "UNFLAGGED",
                    "UNSEEN",
                }
                if criterion == ["ALL"] or criterion[0].upper() not in allowed:
                    if criterion == ["ALL"]:
                        pass  # ALL is always valid
                    else:
                        raise ValueError(
                            "Use a supported IMAP flag or a FROM:, TO:, "
                            "CC:, BCC:, SUBJECT:, BODY: or TEXT: query."
                        )

                criterion = [criterion[0].upper()]

            client = self._get_client()
            try:
                client.select_folder(folder, readonly=True)
                uids = sorted(
                    client.search(criterion),
                    reverse=True,
                )[:limit]

                fetched = (
                    client.fetch(
                        uids,
                        [
                            "BODY.PEEK[HEADER]",
                            "FLAGS",
                            "INTERNALDATE",
                            "RFC822.SIZE",
                        ],
                    )
                    if uids
                    else {}
                )

                results = []

                for uid in uids:
                    item = fetched[uid]
                    raw_header = (
                        item.get(b"BODY[HEADER]") or item.get("BODY[HEADER]") or b""
                    )
                    headers = BytesParser(policy=default).parsebytes(raw_header)

                    results.append(
                        {
                            "uid": int(uid),
                            "subject": decode_mime_header(headers.get("Subject")),
                            "from": [
                                address.to_dict()
                                for address in parse_address_list(headers.get("From"))
                            ],
                            "to": [
                                address.to_dict()
                                for address in parse_address_list(headers.get("To"))
                            ],
                            "date": _json_value(
                                item.get(
                                    b"INTERNALDATE",
                                    item.get("INTERNALDATE"),
                                )
                            ),
                            "flags": _json_value(
                                item.get(
                                    b"FLAGS",
                                    item.get("FLAGS", []),
                                )
                            ),
                            "size": _status_value(
                                {
                                    "size": item.get(
                                        b"RFC822.SIZE",
                                        item.get("RFC822.SIZE", 0),
                                    )
                                },
                                "size",
                            ),
                        }
                    )

                return json.dumps(
                    {
                        "emails": results,
                        "count": len(results),
                    },
                    ensure_ascii=False,
                )
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_email(self, uid: int, folder: str = "INBOX") -> str:
        """Read a full email without automatically marking it as read."""
        try:
            client = self._get_client()
            try:
                client.select_folder(folder, readonly=True)
                fetched = client.fetch(
                    [uid],
                    ["BODY.PEEK[]", "FLAGS", "INTERNALDATE"],
                )

                if uid not in fetched:
                    raise ValueError(f"No email found with UID {uid}.")

                item = fetched[uid]
                raw = item.get(b"BODY[]") or item.get("BODY[]")
                if raw is None:
                    raise ValueError(
                        f"Email UID {uid} did not contain " "a message body."
                    )

                message = BytesParser(policy=default).parsebytes(raw)
                body, body_html = _message_body(message)

                date_value = message.get("Date")
                try:
                    parsed_date = (
                        parsedate_to_datetime(date_value).isoformat()
                        if date_value
                        else None
                    )
                except (TypeError, ValueError, OverflowError):
                    parsed_date = None

                result = {
                    "uid": int(uid),
                    "subject": decode_mime_header(message.get("Subject")),
                    "from": [
                        address.to_dict()
                        for address in parse_address_list(message.get("From"))
                    ],
                    "to": [
                        address.to_dict()
                        for address in parse_address_list(message.get("To"))
                    ],
                    "cc": [
                        address.to_dict()
                        for address in parse_address_list(message.get("Cc"))
                    ],
                    "date": parsed_date
                    or _json_value(
                        item.get(
                            b"INTERNALDATE",
                            item.get("INTERNALDATE"),
                        )
                    ),
                    "message_id": message.get("Message-ID", ""),
                    "body": body,
                    "body_html": body_html,
                    "flags": _json_value(
                        item.get(
                            b"FLAGS",
                            item.get("FLAGS", []),
                        )
                    ),
                }

                return json.dumps(result, ensure_ascii=False)
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"error": str(e)})

    def list_unread(
        self,
        folder: str = "INBOX",
        limit: int = 10,
    ) -> str:
        """List unread messages."""
        return self.search_emails(
            query="UNSEEN",
            folder=folder,
            limit=limit,
        )

    def get_folder_stats(self, folder: str = "INBOX") -> str:
        """Return message and unread counts for a folder."""
        try:
            client = self._get_client()
            try:
                status = client.folder_status(
                    folder,
                    ["MESSAGES", "UNSEEN"],
                )

                return json.dumps(
                    {
                        "folder": folder,
                        "messages": _status_value(status, "MESSAGES"),
                        "unseen": _status_value(status, "UNSEEN"),
                    }
                )
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"error": str(e)})

    def mark_as_read(self, uid: int, folder: str = "INBOX") -> str:
        """Mark an email as read."""
        try:
            client = self._get_client()
            try:
                client.select_folder(folder)
                client.add_flags([uid], ["\\Seen"])

                return json.dumps(
                    {
                        "success": True,
                        "uid": uid,
                        "folder": folder,
                    }
                )
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def move_email(
        self,
        uid: int,
        source_folder: str,
        dest_folder: str,
    ) -> str:
        """Move an email, falling back to copy-and-delete."""
        try:
            client = self._get_client()
            try:
                client.select_folder(source_folder)

                try:
                    client.move([uid], dest_folder)
                except Exception:
                    client.copy([uid], dest_folder)
                    client.delete_messages([uid])
                    client.expunge([uid])

                return json.dumps(
                    {
                        "success": True,
                        "uid": uid,
                        "source_folder": source_folder,
                        "dest_folder": dest_folder,
                    }
                )
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
    ) -> str:
        """Save a draft in the detected Drafts folder."""
        try:
            client = self._get_client()
            try:
                msg = self._create_message(
                    to=to,
                    cc=cc,
                    subject=subject,
                    body=body,
                )

                draft_folder = None

                for flags, _, name in client.list_folders():
                    folder_name = _decode_bytes(name)
                    normalized_flags = [
                        _decode_bytes(flag).lower() for flag in (flags or [])
                    ]

                    # Check for draft folder by flag first
                    if any("\\drafts" in flag for flag in normalized_flags):
                        draft_folder = folder_name
                        break

                    # Check for draft folder by name (various conventions)
                    folder_lower = folder_name.lower().rstrip("/")
                    if folder_lower.endswith("\\drafts") or folder_lower.endswith("/drafts") or folder_lower.endswith("drafts"):
                        draft_folder = draft_folder or folder_name

                # If multiple draft folders found, pick the first one with \\drafts flag
                if draft_folder:
                    has_draft_flag = False
                    for flags, _, name in client.list_folders():
                        normalized_flags = [
                            _decode_bytes(flag).lower() for flag in (flags or [])
                        ]
                        if any("\\drafts" in flag for flag in normalized_flags):
                            has_draft_flag = True
                            break
                    if not has_draft_flag:
                        # Already handled above, but as fallback
                        pass

                target_folder = draft_folder or "Drafts"
                client.append(
                    target_folder,
                    msg.as_bytes(),
                    flags=["\\Draft"],
                    msg_time=datetime.now(timezone.utc),
                )

                return json.dumps(
                    {
                        "success": True,
                        "folder": target_folder,
                    }
                )
            finally:
                client.logout()
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _send_smtp(
        self,
        msg: MIMEMultipart,
        recipients: list[str],
    ) -> dict:
        smtp_host = self._get_smtp_host()
        if not smtp_host:
            raise ValueError("SMTP host is not configured.")

        smtp_username = self.valves.smtp_username or self.valves.imap_username
        # Only fallback to imap password if smtp password not explicitly set
        smtp_password = self.valves.smtp_password or (
            self.valves.imap_password if self.valves.smtp_use_imap_credentials else ""
        )

        context = self._get_ssl_context()

        if self.valves.smtp_use_ssl:
            server = smtplib.SMTP_SSL(
                smtp_host,
                self.valves.smtp_port,
                timeout=self.valves.timeout,
                context=context,
            )
        else:
            server = smtplib.SMTP(
                smtp_host,
                self.valves.smtp_port,
                timeout=self.valves.timeout,
            )

        try:
            server.ehlo()

            if self.valves.smtp_starttls and not self.valves.smtp_use_ssl:
                server.starttls(context=context)
                server.ehlo()

            if smtp_username:
                if not smtp_password:
                    raise ValueError("SMTP password is not configured.")
                server.login(smtp_username, smtp_password)

            refused = server.sendmail(
                self._get_sender_email(),
                recipients,
                msg.as_string(),
            )
        except Exception:
            try:
                server.quit()
            except Exception:
                pass
            raise

        result = {
            "success": not bool(refused),
            "message_id": msg["Message-ID"],
            "refused": _json_value(refused),
        }

        try:
            server.quit()
        except Exception as e:
            result["warning"] = (
                "Email was submitted, but closing the SMTP " f"connection failed: {e}"
            )

        return result

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
    ) -> str:
        """Send an email immediately using SMTP."""
        try:
            recipients = list(
                dict.fromkeys(
                    address.lower()
                    for address in (_addresses(to) + _addresses(cc) + _addresses(bcc))
                )
            )

            if not recipients:
                raise ValueError("At least one valid recipient is required.")

            msg = self._create_message(
                to=to,
                cc=cc,
                subject=subject,
                body=body,
            )

            return json.dumps(
                self._send_smtp(msg, recipients),
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def reply_to_email(
        self,
        uid: int,
        body: str,
        folder: str = "INBOX",
        reply_all: bool = False,
    ) -> str:
        """Send a threaded reply, optionally including all recipients."""
        try:
            client = self._get_client()
            try:
                client.select_folder(folder, readonly=True)
                fetched = client.fetch([uid], ["BODY.PEEK[]"])

                if uid not in fetched:
                    raise ValueError(f"No email found with UID {uid}.")

                raw = fetched[uid].get(b"BODY[]") or fetched[uid].get("BODY[]")
                if raw is None:
                    raise ValueError(
                        f"Email UID {uid} did not contain " "a message body."
                    )

                original = BytesParser(policy=default).parsebytes(raw)

                own_address = self._get_sender_email().strip().lower()
                reply_to = _addresses(original.get("Reply-To", "")) or _addresses(
                    original.get("From", "")
                )

                if not reply_to:
                    raise ValueError(
                        "The original email has no valid " "reply address."
                    )

                to_addresses = []
                cc_addresses = []

                for address in reply_to:
                    if address.lower() != own_address and address.lower() not in [
                        item.lower() for item in to_addresses
                    ]:
                        to_addresses.append(address)

                if reply_all:
                    for address in _addresses(original.get("To", "")):
                        if address.lower() != own_address and address.lower() not in [
                            item.lower() for item in to_addresses
                        ]:
                            to_addresses.append(address)

                    for address in _addresses(original.get("Cc", "")):
                        if (
                            address.lower() != own_address
                            and address.lower()
                            not in [item.lower() for item in to_addresses]
                            and address.lower()
                            not in [item.lower() for item in cc_addresses]
                        ):
                            cc_addresses.append(address)

                if not to_addresses:
                    raise ValueError(
                        "No reply recipient remains after "
                        "excluding the sender account."
                    )

                subject = decode_mime_header(original.get("Subject"))
                if not re.match(r"^\s*re\s*:", subject, re.I):
                    subject = "Re: " + subject

                references = " ".join(
                    value
                    for value in (
                        original.get("References", "").strip(),
                        original.get("Message-ID", "").strip(),
                    )
                    if value
                )

                msg = self._create_message(
                    to=", ".join(to_addresses),
                    cc=", ".join(cc_addresses),
                    subject=subject,
                    body=body,
                    in_reply_to=original.get("Message-ID", ""),
                    references=references,
                )

                recipients = list(
                    dict.fromkeys(
                        address.lower() for address in (to_addresses + cc_addresses)
                    )
                )
            finally:
                client.logout()

            result = self._send_smtp(msg, recipients)
            result.update(
                {
                    "in_reply_to": original.get("Message-ID", ""),
                    "reply_all": reply_all,
                }
            )

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
