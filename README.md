# IMAP Email Tool for Open WebUI

Access and manage emails via IMAP/SMTP directly from Open WebUI. Search, read, compose, and send emails through an AI assistant.

## Features

### Reading & Searching

- **List Folders** - View all email folders with message counts and unread stats
- **Search Emails** - Flexible search with multiple criteria (ALL, UNSEEN, FLAGGED, FROM, SUBJECT, TEXT, SINCE)
- **Get Email** - Read full email content including headers and body
- **List Unread** - Quick access to unread messages
- **Folder Stats** - Get total and unread message counts for any folder

### Managing

- **Mark as Read** - Update email read status
- **Move Email** - Move messages between folders (with automatic fallback to copy+delete)

### Composing & Sending

- **Create Draft** - Save drafts to the Drafts folder
- **Send Email** - Send messages immediately via SMTP with CC/BCC support
- **Reply to Email** - Reply or reply-all with proper threading (In-Reply-To, References headers)

## Requirements

- Open WebUI 0.4.0 or later
- Python package: `imapclient`

## Installation

### Step 1: Add the Tool

1. Open **Open WebUI** in your browser
2. Go to **Workspace** → **Tools** (in the left sidebar)
3. Click the **+** button to create a new tool
4. Copy the entire contents of `openwebui_tool.py` and paste it into the code editor
5. Click **Save**
6. The tool "IMAP Email Tool" should now appear in your tools list

### Step 2: Configure the Tool (Valves)

1. In **Workspace** → **Tools**, find "IMAP Email Tool"
2. Click the **gear icon** (⚙️) to open Valves settings
3. Fill in your email server credentials (see [Configuration](#configuration) below)
4. Click **Save**

### Step 3: Create a Model with the Email Tool

1. Go to **Workspace** → **Models**
2. Click **+** to create a new model
3. Configure the model:
   - **Name**: Give it a descriptive name (e.g., "Email Assistant")
   - **Base Model**: Select your preferred LLM (GPT-4, Claude, Llama, etc.)
   - **System Prompt**: Copy and paste the system prompt from [system_prompt_en.md](system_prompt_en.md) for English or [system_prompt_de.md](system_prompt_de.md) for German
     - Use the **English** or **German** version depending on your preference
   - **Tools**: Enable the **IMAP Email Tool** by selecting it from the available tools
4. Click **Save**

### Step 4: Start Using

1. Go to **New Chat**
2. Select your newly created "Email Assistant" model from the model dropdown
3. Start chatting! Try commands like:
   - "Show me my unread emails"
   - "Search for emails from <john@example.com>"
   - "Read the latest email"

## Configuration

Configure the tool via **Valves** (tool settings):

### IMAP Settings

| Setting | Default | Description |
| --------- | --------- | ------------- |
| `imap_host` | - | IMAP server hostname (e.g., `imap.gmail.com`) |
| `imap_port` | 993 | IMAP port (993 for SSL, 143 for plain) |
| `imap_username` | - | Email address / username |
| `imap_password` | - | Password or app-specific password |
| `use_ssl` | true | Use SSL/TLS connection |

### SMTP Settings

| Setting | Default | Description |
| --------- | --------- | ------------- |
| `smtp_host` | - | SMTP server (auto-derived from IMAP if empty) |
| `smtp_port` | 587 | SMTP port (587 for STARTTLS, 465 for SSL) |
| `smtp_use_tls` | true | Use STARTTLS (port 587) |
| `smtp_use_ssl` | false | Use SSL (port 465, overrides TLS) |
| `smtp_use_imap_credentials` | false | Fallback to IMAP password for SMTP auth if SMTP password not set |
| `smtp_starttls` | false | Use STARTTLS (port 587) when not using SSL |

### Advanced Settings

| Setting | Default | Description |
| --------- | --------- | ------------- |
| `accept_self_signed_certificates` | false | Allow unverified TLS certificates for IMAP and SMTP |
| `timeout` | 30 | Connection timeout in seconds (1-300) |

### Sender Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `sender_name` | - | Display name for sent emails (e.g., "John Doe") |

### Example Configurations

**Gmail:**

```
imap_host: imap.gmail.com
imap_port: 993
smtp_host: smtp.gmail.com
smtp_port: 587
smtp_use_tls: true
```

> Note: Gmail requires an [App Password](https://support.google.com/accounts/answer/185833)

**Microsoft 365 / Outlook:**

```
imap_host: outlook.office365.com
imap_port: 993
smtp_host: smtp.office365.com
smtp_port: 587
smtp_use_tls: true
```

## System Prompt

The system prompt teaches the AI how to effectively use the email tool with enhanced functionality. It includes:

- All available functions and their complete parameters
- Best practices (confirm before sending, use drafts for complex emails)
- Optimized example workflows for common tasks
- Advanced formatting guidelines
- New capabilities for better email management

See [system_prompt_en.md](system_prompt_en.md) for the English version or [system_prompt_de.md](system_prompt_de.md) for the German version that incorporate these enhancements.

## Available Functions

| Function | Parameters | Description |
| ---------- | ------------ | ------------- |
| `list_folders()` | - | List all folders with message counts |
| `search_emails()` | `query`, `folder`, `limit` | Search emails |
| `get_email()` | `uid`, `folder` | Get full email content |
| `list_unread()` | `folder`, `limit` | List unread emails |
| `get_folder_stats()` | `folder` | Get folder statistics |
| `mark_as_read()` | `uid`, `folder` | Mark email as read |
| `move_email()` | `uid`, `source_folder`, `dest_folder` | Move email |
| `create_draft()` | `to`, `subject`, `body`, `cc` | Create draft |
| `send_email()` | `to`, `subject`, `body`, `cc`, `bcc` | Send email |
| `reply_to_email()` | `uid`, `body`, `folder`, `reply_all` | Reply to email |

### Search Query Syntax

| Query | Description |
| ------- | ------------- |
| `ALL` | All emails |
| `UNSEEN` | Unread emails |
| `FLAGGED` | Flagged/starred emails |
| `FROM:email` | Emails from specific sender |
| `SUBJECT:text` | Emails with subject containing text |
| `TEXT:content` | Full-text search |
| `SINCE:date` | Emails since date |

## Test Environment Setup

For developers wanting to run the regression tests:

### Prerequisites

- Python 3.11+
- `uv` package manager (or pip)

### Setup Steps

```bash
# 1. Clone/repo the project
git clone <repository-url>
cd openwebui-imap-email-tool

# 2. Create virtual environment with uv
uv venv --python 3.11
source .venv/bin/activate

# 3. Install dependencies
uv pip install imapclient pydantic pytest email-validator

# 4. Run the regression tests
python -m pytest tests/test_tool.py -v
```

### Test Coverage

The test suite (`tests/test_tool.py`) covers:

- `EmailAddress` dataclass functionality
- `_decode_bytes()` helper
- `_addresses()` helper  
- `parse_address()` and `parse_address_list()`
- `_status_value()` with various key types
- `_json_value()` for bytes/datetime/list/dict handling
- `_message_body()` for plain text, HTML, and mixed parts
- Tools class initialization and valve fields
- Search query validation logic
- SMTP credential handling

### Portability

The test environment is designed to work across different workspace checkouts. The test file uses `__file__`-relative path resolution:

```python
test_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_file_dir)
sys.path.insert(0, project_root)
```

This means the tests can be placed anywhere in the project and will automatically find the project root relative to the test file's location.

### Running Specific Tests

```bash
# Run all tests
python -m pytest tests/test_tool.py

# Run with verbose output
python -m pytest tests/test_tool.py -v

# Run with detailed tracebacks
python -m pytest tests/test_tool.py --tb=long
```

## Example Usage

**User:** "Show me my unread emails"

- AI calls `list_unread()` and presents results

**User:** "Read the email from John"

- AI calls `search_emails("FROM:john")` to find UIDs
- AI calls `get_email(uid)` to fetch content

**User:** "Reply with 'Thanks for the update'"

- AI calls `reply_to_email(uid, "Thanks for the update")`

**User:** "Send an email to <team@company.com> about the meeting"

- AI asks for details, creates draft with `create_draft()`
- Shows draft for confirmation
- Sends with `send_email()` upon approval

## Security Notes

- Use app-specific passwords when available (Gmail, Microsoft, etc.)
- Credentials are stored in Open WebUI's valve configuration
- The tool uses secure connections (SSL/TLS) by default
- Sent emails are automatically saved to the Sent folder

## Author

**Sandro Scalco** - [liitu consulting gmbh](https://liitu.ch)

## Contributors

**Patrik Gfeller** - [Code-Omega](https://www.code-omega.ch)

## License

MIT License

## Version

0.2.0
