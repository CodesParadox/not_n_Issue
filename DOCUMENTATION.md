# GitHub Issues Manager CLI - Complete Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Implementation Details](#implementation-details)
3. [Function Reference](#function-reference)
4. [Configuration Deep Dive](#configuration-deep-dive)
5. [GitHub Actions Integration](#github-actions-integration)
6. [Slack Integration](#slack-integration)
7. [API Integration](#api-integration)
8. [Error Handling](#error-handling)
9. [Development Guide](#development-guide)
10. [Advanced Usage Patterns](#advanced-usage-patterns)

## Architecture Overview

### Design Philosophy
The GitHub Issues Manager CLI is built as a **single-file application** to maximize portability and simplify deployment. This design choice enables:
- Easy distribution and version control
- Minimal dependency management
- Simple integration into CI/CD pipelines
- Quick setup in any Python environment

### Core Components
```
issues_manager.py
├── Configuration Layer (Environment Variables)
├── GitHub API Client (HTTP requests)
├── CLI Interface (Typer framework)
├── Slack Notification System (Webhooks)
├── Error Handling (Custom exceptions)
└── Utility Functions (Parsing, validation)
```

### Technology Stack
- **Python 3.9+**: Core runtime
- **Typer 0.12.3**: Modern CLI framework with rich help and validation
- **Requests 2.32.3**: HTTP client for GitHub API communication
- **python-dotenv 1.0.1**: Environment variable management
- **GitHub REST API v4**: Primary data source
- **Slack Incoming Webhooks**: Notification delivery

## Implementation Details

### Application Structure

The application follows a **layered architecture** pattern:

1. **CLI Layer**: Command parsing and user interaction
2. **Business Logic Layer**: Core issue management operations
3. **API Layer**: GitHub REST API communication
4. **Integration Layer**: Slack notifications and external services
5. **Configuration Layer**: Environment and runtime configuration

### Data Flow
```
User Input → CLI Parser → Business Logic → GitHub API → Response Processing → Output/Notifications
```

### Key Design Patterns

#### Command Pattern
Each CLI command is implemented as a separate function that:
- Validates input parameters
- Calls the appropriate business logic function
- Handles errors and user feedback
- Triggers notifications

#### Repository Pattern
GitHub API interactions are abstracted through dedicated functions:
- `create_issue()` - Issue creation
- `get_issue()` - Issue retrieval
- `patch_issue()` - Issue updates
- `list_issues()` - Issue querying

#### Observer Pattern
Slack notifications act as observers for all issue operations, providing non-blocking event notifications.

## Function Reference

### Core API Functions

#### `gh_headers() -> Dict[str, str]`
**Purpose**: Generates authentication headers for GitHub API requests

**Implementation Details**:
- Validates GitHub token presence
- Sets API version to `2022-11-28` for consistency
- Includes custom User-Agent for request tracking
- Raises `GitHubError` if token is missing

**Usage**:
```python
headers = gh_headers()
# Returns: {
#     "Accept": "application/vnd.github+json",
#     "Authorization": "token ghp_...",
#     "X-GitHub-Api-Version": "2022-11-28",
#     "User-Agent": "issues-manager-cli"
# }
```

#### `normalize_repo(repo: str) -> str`
**Purpose**: Converts repository input to standard `owner/repo` format

**Implementation Details**:
- Accepts both `owner/repo` and `repo` formats
- Uses `GITHUB_OWNER` environment variable for short format
- Validates input and provides clear error messages

**Examples**:
```python
normalize_repo("CodesParadox/not_n_Issue")  # → "CodesParadox/not_n_Issue"
normalize_repo("not_n_Issue")  # → "CodesParadox/not_n_Issue" (if GITHUB_OWNER set)
```

#### `create_issue(repo, title, body=None, labels=None, assignees=None, milestone=None) -> Dict[str, Any]`
**Purpose**: Creates a new GitHub issue

**Implementation Details**:
- Constructs POST request to `/repos/{owner}/{repo}/issues`
- Validates response status (201 for success)
- Automatically triggers Slack notification
- Returns full issue object from GitHub API

**Request Format**:
```json
{
  "title": "Issue title",
  "body": "Issue description",
  "labels": ["bug", "priority-high"],
  "assignees": ["username1", "username2"],
  "milestone": 1
}
```

#### `update_issue(repo, issue_number, **kwargs) -> Dict[str, Any]`
**Purpose**: Updates existing issue with flexible field modifications

**Implementation Details**:
- Supports partial updates (only specified fields)
- Handles label operations: add, remove, replace
- Manages assignee operations: add, remove, replace
- Processes state changes with reasons
- Validates state_reason values

**Label Operations Logic**:
```python
if set_labels:
    data["labels"] = set_labels  # Replace all
elif add_labels or remove_labels:
    current = get_issue(repo, issue_number)
    current_labels = {label["name"] for label in current.get("labels", [])}
    if add_labels:
        current_labels.update(add_labels)
    if remove_labels:
        current_labels.difference_update(remove_labels)
    data["labels"] = list(current_labels)
```

#### `list_issues(repo, state="open", **filters) -> List[Dict[str, Any]]`
**Purpose**: Retrieves filtered list of issues

**Implementation Details**:
- Constructs GitHub API query parameters
- Handles pagination automatically
- Filters out Pull Requests (issues with `pull_request` key)
- Supports complex time-based filtering

**Query Parameter Mapping**:
- `state`: `open`, `closed`, `all`
- `labels`: Comma-separated string
- `sort`: `created`, `updated`, `comments`
- `direction`: `asc`, `desc`
- `since`: ISO-8601 timestamp
- `per_page`: 1-100 (GitHub limit)

### Utility Functions

#### `parse_since(value: Optional[str]) -> Optional[str]`
**Purpose**: Converts relative time expressions to ISO-8601 timestamps

**Implementation Details**:
- Supports relative formats: `7d`, `12h`, `30m`
- Accepts ISO-8601 dates: `2024-01-01`, `2024-01-01T10:30:00Z`
- Uses UTC timezone for consistency
- Returns None for invalid input

**Parsing Logic**:
```python
def parse_since(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    
    # Try relative format first
    match = re.match(r'^(\d+)([dhm])$', value.lower())
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        delta_map = {'d': 'days', 'h': 'hours', 'm': 'minutes'}
        delta = timedelta(**{delta_map[unit]: amount})
        since_time = datetime.now(timezone.utc) - delta
        return since_time.isoformat()
    
    # Try ISO format
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.isoformat()
    except ValueError:
        return None
```

#### `notify_slack(text: str) -> None`
**Purpose**: Sends notifications to Slack webhook

**Implementation Details**:
- Non-blocking operation (errors don't fail main command)
- Uses simple webhook format with text payload
- 15-second timeout for reliability
- Silent failure to maintain CLI reliability

### CLI Command Functions

Each CLI command follows this pattern:
```python
@app.command("command_name")
def cmd_command_name(
    repo: str = typer.Argument(..., help="Repository"),
    # ... other parameters
):
    """Command description."""
    try:
        result = core_function(repo, ...)
        typer.echo(f"✅ Success message: {result['url']}")
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)
```

## Configuration Deep Dive

### Environment Variables

#### Required Configuration
- **`GITHUB_TOKEN`** or **`GH_TOKEN`**: Personal Access Token
  - Minimum scopes: `repo` (for private repos) or `public_repo` (for public repos)
  - Format: `ghp_` followed by 36 characters
  - Acquisition: GitHub Settings → Developer settings → Personal access tokens

#### Optional Configuration
- **`GITHUB_OWNER`**: Default repository owner/organization
  - Enables short repository format (`repo` instead of `owner/repo`)
  - Useful for teams working primarily on one organization's repositories
  
- **`GITHUB_API_URL`**: Custom GitHub API endpoint
  - Default: `https://api.github.com`
  - Used for GitHub Enterprise Server installations
  - Format: `https://your-github-enterprise.com/api/v3`

- **`SLACK_WEBHOOK_URL`**: Slack Incoming Webhook URL
  - Format: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`
  - Enables automatic Slack notifications for all operations

### Configuration Precedence
1. Environment variables
2. `.env` file (processed by python-dotenv)
3. System environment
4. Default values (where applicable)

### Security Considerations

#### Token Management
- Store tokens in `.env` file (not committed to version control)
- Use repository secrets for CI/CD environments
- Regularly rotate tokens (recommended: every 90 days)
- Use fine-grained personal access tokens when available

#### Webhook Security
- Slack webhooks are not authenticated by default
- Consider using Slack app tokens for production environments
- Restrict webhook URLs to internal documentation

## GitHub Actions Integration

### Workflow Architecture

The included workflow (`.github/workflows/notify-slack-on-issue.yml`) provides comprehensive issue event monitoring:

```yaml
name: Notify Slack on Issues
on:
  issues:
    types:
      - opened      # New issue created
      - reopened    # Closed issue reopened
      - closed      # Issue closed
      - edited      # Issue title/body modified
      - assigned    # User assigned to issue
      - unassigned  # User removed from issue
      - labeled     # Label added to issue
      - unlabeled   # Label removed from issue
      - milestoned  # Milestone assigned
      - demilestoned # Milestone removed
```

### Event Processing

#### Context Variables Available
- `${{ github.event.action }}`: Event type trigger
- `${{ github.repository }}`: Repository full name
- `${{ github.event.issue.number }}`: Issue number
- `${{ github.event.issue.title }}`: Issue title
- `${{ github.event.issue.state }}`: Issue state (open/closed)
- `${{ github.event.issue.html_url }}`: Issue URL
- `${{ github.actor }}`: User who triggered the event
- `${{ github.event.label.name }}`: Label name (for label events)
- `${{ github.event.assignee.login }}`: Assignee username
- `${{ github.event.issue.milestone.title }}`: Milestone name

#### Message Formatting Logic
```bash
# Escape quotes in title to keep JSON valid
ESCAPED_TITLE=$(printf '%s' "$TITLE" | sed 's/"/\\"/g')

# Build context based on action type
EXTRA=""
case "$ACTION" in
  labeled) EXTRA=" • label: *${LABEL}*";;
  unlabeled) EXTRA=" • label: *${LABEL}*";;
  assigned) EXTRA=" • assignee: *@${ASSIGNEE}*";;
  unassigned) EXTRA=" • assignee: *@${ASSIGNEE}*";;
  milestoned) EXTRA=" • milestone: *${MILESTONE}*";;
  demilestoned) EXTRA=" • milestone: *${MILESTONE}*";;
esac

TEXT="*[${REPO}]* Issue #${NUMBER} *${ACTION}*: \"${ESCAPED_TITLE}\" (${STATE}) by *${SENDER}*${EXTRA}\n${URL}"
```

### Setup Requirements

#### Repository Secrets
1. Navigate to repository Settings → Secrets and variables → Actions
2. Add secret: `SLACK_WEBHOOK_URL`
3. Value: Your Slack webhook URL

#### Webhook Creation Process
1. **Create Slack App**:
   - Visit https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Provide app name and select workspace

2. **Enable Incoming Webhooks**:
   - Navigate to app Features → Incoming Webhooks
   - Toggle "Activate Incoming Webhooks" to On
   - Click "Add New Webhook to Workspace"

3. **Configure Channel**:
   - Select target channel for notifications
   - Copy the generated webhook URL
   - Add URL to GitHub repository secrets

### Workflow Customization

#### Adding Custom Events
To monitor additional events, modify the `on.issues.types` array:
```yaml
on:
  issues:
    types:
      # Existing events...
      - transferred  # Issue transferred between repositories
      - pinned      # Issue pinned
      - unpinned    # Issue unpinned
```

#### Custom Message Formats
Modify the message format in the workflow:
```bash
# Custom format with emoji and additional context
TEXT="🔧 *[${REPO}]* Issue #${NUMBER} ${ACTION} by ${SENDER}\n📝 \"${ESCAPED_TITLE}\"\n🔗 ${URL}"
```

#### Conditional Notifications
Add conditions to filter notifications:
```yaml
steps:
  - name: Send notification
    if: contains(github.event.issue.labels.*.name, 'critical')
    # ... rest of step
```

## Slack Integration

### Webhook Anatomy

#### Request Format
```http
POST https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
Content-Type: application/json

{
  "text": "*[CodesParadox/not_n_Issue]* Issue #123 *opened*: \"Bug in login system\" (open) by *developer*\nhttps://github.com/CodesParadox/not_n_Issue/issues/123"
}
```

#### Message Formatting
Slack supports rich text formatting:
- `*bold*`: **bold text**
- `_italic_`: *italic text*
- `\n`: Line breaks
- Links: Automatically detected and formatted

### Advanced Slack Features

#### Custom Payloads
For more sophisticated notifications, extend the `notify_slack` function:
```python
def notify_slack_rich(title: str, url: str, action: str, details: dict) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    
    payload = {
        "attachments": [{
            "color": "good" if action in ["opened", "reopened"] else "warning",
            "title": title,
            "title_link": url,
            "fields": [
                {"title": "Action", "value": action, "short": True},
                {"title": "State", "value": details.get("state"), "short": True}
            ],
            "footer": "GitHub Issues Manager",
            "ts": int(datetime.now().timestamp())
        }]
    }
    
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=15)
    except Exception:
        pass
```

#### Channel Routing
Route different issue types to different channels:
```python
def get_webhook_for_labels(labels: List[str]) -> str:
    if "bug" in labels:
        return os.getenv("SLACK_WEBHOOK_BUGS")
    elif "feature" in labels:
        return os.getenv("SLACK_WEBHOOK_FEATURES")
    return SLACK_WEBHOOK_URL
```

### Error Handling and Reliability

#### Best Practices
- Always use timeouts (15 seconds recommended)
- Never let Slack failures affect core operations
- Log Slack errors for debugging (optional)
- Implement retry logic for critical notifications

#### Fallback Strategies
```python
def notify_slack_with_fallback(text: str) -> None:
    primary_webhook = os.getenv("SLACK_WEBHOOK_PRIMARY")
    fallback_webhook = os.getenv("SLACK_WEBHOOK_FALLBACK")
    
    for webhook in [primary_webhook, fallback_webhook]:
        if webhook and try_slack_notification(webhook, text):
            return
    
    # Log failure or use alternative notification method
    log_notification_failure(text)
```

## API Integration

### GitHub REST API v4

#### Rate Limiting
- **Authenticated requests**: 5,000 per hour
- **Search API**: 30 per minute
- **Secondary rate limits**: Vary by operation type

#### Rate Limit Handling
```python
def handle_rate_limit(response: requests.Response) -> None:
    if response.status_code == 403:
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
        if rate_limit_remaining == '0':
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_seconds = reset_time - int(time.time())
            raise GitHubError(f"Rate limit exceeded. Reset in {wait_seconds} seconds.")
```

#### Request Patterns

##### Pagination
GitHub API uses link-based pagination:
```python
def get_all_issues(repo: str) -> List[Dict[str, Any]]:
    issues = []
    url = f"{GITHUB_API_URL}/repos/{normalize_repo(repo)}/issues"
    
    while url:
        response = requests.get(url, headers=gh_headers())
        response.raise_for_status()
        issues.extend(response.json())
        
        # Parse Link header for next page
        link_header = response.headers.get('Link', '')
        url = extract_next_url(link_header)
    
    return issues
```

##### Conditional Requests
Use ETags for efficient polling:
```python
def get_issue_if_modified(repo: str, issue_number: int, etag: str = None) -> tuple:
    headers = gh_headers()
    if etag:
        headers['If-None-Match'] = etag
    
    response = requests.get(
        f"{GITHUB_API_URL}/repos/{normalize_repo(repo)}/issues/{issue_number}",
        headers=headers
    )
    
    if response.status_code == 304:  # Not Modified
        return None, etag
    
    new_etag = response.headers.get('ETag')
    return response.json(), new_etag
```

### Error Response Handling

#### GitHub API Error Codes
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized (invalid token)
- **403**: Forbidden (insufficient permissions or rate limit)
- **404**: Not Found (repository or issue doesn't exist)
- **422**: Unprocessable Entity (validation errors)

#### Error Processing
```python
def handle_github_error(response: requests.Response) -> None:
    if response.status_code == 404:
        error_data = response.json()
        if 'repository' in error_data.get('message', '').lower():
            raise GitHubError("Repository not found or access denied")
        else:
            raise GitHubError("Issue not found")
    
    elif response.status_code == 422:
        error_data = response.json()
        errors = error_data.get('errors', [])
        if errors:
            error_msg = '; '.join([err.get('message', 'Unknown error') for err in errors])
            raise GitHubError(f"Validation error: {error_msg}")
    
    response.raise_for_status()
```

## Error Handling

### Exception Hierarchy
```python
class GitHubError(Exception):
    """Base exception for GitHub API errors"""
    pass

class GitHubAuthError(GitHubError):
    """Authentication-related errors"""
    pass

class GitHubNotFoundError(GitHubError):
    """Resource not found errors"""
    pass

class GitHubValidationError(GitHubError):
    """Input validation errors"""
    pass
```

### Error Context Propagation
```python
def create_issue_with_context(repo: str, **kwargs) -> Dict[str, Any]:
    try:
        return create_issue(repo, **kwargs)
    except requests.exceptions.ConnectionError:
        raise GitHubError("Network connection failed. Check your internet connection.")
    except requests.exceptions.Timeout:
        raise GitHubError("Request timed out. GitHub API may be slow.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise GitHubAuthError("Invalid GitHub token. Check your GITHUB_TOKEN.")
        elif e.response.status_code == 404:
            raise GitHubNotFoundError(f"Repository '{repo}' not found or access denied.")
        else:
            raise GitHubError(f"GitHub API error: {e.response.status_code}")
```

### User-Friendly Error Messages
```python
ERROR_MESSAGES = {
    'invalid_token': "❌ Invalid GitHub token. Please check your GITHUB_TOKEN in .env file.",
    'repo_not_found': "❌ Repository not found. Verify the repository name and your access permissions.",
    'issue_not_found': "❌ Issue not found. Check the issue number.",
    'rate_limit': "❌ GitHub API rate limit exceeded. Please wait before making more requests.",
    'network_error': "❌ Network error. Check your internet connection and try again.",
    'validation_error': "❌ Invalid input. Please check your command parameters."
}

def get_user_friendly_error(error_type: str, details: str = "") -> str:
    base_message = ERROR_MESSAGES.get(error_type, f"❌ An error occurred: {details}")
    return f"{base_message}\n💡 For help, run: python issues_manager.py --help"
```

## Development Guide

### Setting Up Development Environment

#### 1. Clone and Setup
```bash
git clone https://github.com/CodesParadox/not_n_Issue.git
cd not_n_Issue
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Development Configuration
Create `.env.dev`:
```bash
GITHUB_TOKEN=ghp_your_development_token
GITHUB_OWNER=your-test-org
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TEST/WEBHOOK/URL
GITHUB_API_URL=https://api.github.com  # Use GitHub Enterprise for testing
```

#### 3. Testing Setup
```bash
# Install development dependencies
pip install pytest pytest-mock requests-mock

# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=issues_manager --cov-report=html
```

### Code Style and Standards

#### Type Hints
All functions should include type hints:
```python
from typing import Optional, List, Dict, Any, Union

def update_issue(
    repo: str,
    issue_number: int,
    title: Optional[str] = None,
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    # Implementation
```

#### Documentation Standards
```python
def complex_function(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """
    Brief description of the function.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (optional)
    
    Returns:
        Dictionary containing the result
    
    Raises:
        GitHubError: When GitHub API returns an error
        ValueError: When input parameters are invalid
    
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['status'])
        'success'
    """
```

#### Error Handling Patterns
```python
# Good: Specific error handling
try:
    issue = get_issue(repo, issue_number)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        raise GitHubError(f"Issue #{issue_number} not found in {repo}")
    else:
        raise GitHubError(f"Failed to get issue: {e}")

# Bad: Generic error handling
try:
    issue = get_issue(repo, issue_number)
except Exception as e:
    raise GitHubError(f"Error: {e}")
```

### Testing Strategies

#### Unit Tests
```python
import pytest
from unittest.mock import patch, Mock
import requests_mock

def test_create_issue_success():
    with requests_mock.Mocker() as m:
        m.post(
            'https://api.github.com/repos/owner/repo/issues',
            json={'number': 123, 'title': 'Test Issue'},
            status_code=201
        )
        
        result = create_issue('owner/repo', 'Test Issue')
        assert result['number'] == 123
        assert result['title'] == 'Test Issue'

def test_create_issue_auth_error():
    with requests_mock.Mocker() as m:
        m.post(
            'https://api.github.com/repos/owner/repo/issues',
            status_code=401
        )
        
        with pytest.raises(GitHubError, match="authentication"):
            create_issue('owner/repo', 'Test Issue')
```

#### Integration Tests
```python
@pytest.mark.integration
def test_full_issue_lifecycle():
    """Test creating, updating, and closing an issue"""
    # Requires real GitHub token and test repository
    repo = os.getenv('TEST_REPO', 'test-user/test-repo')
    
    # Create issue
    issue = create_issue(repo, 'Integration Test Issue')
    issue_number = issue['number']
    
    try:
        # Update issue
        updated = update_issue(repo, issue_number, title='Updated Title')
        assert updated['title'] == 'Updated Title'
        
        # Close issue
        closed = close_issue(repo, issue_number, 'completed')
        assert closed['state'] == 'closed'
        
    finally:
        # Cleanup: ensure issue is closed
        try:
            close_issue(repo, issue_number, 'completed')
        except:
            pass
```

### Performance Optimization

#### Batch Operations
```python
def update_multiple_issues(repo: str, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update multiple issues efficiently with rate limiting consideration"""
    results = []
    
    for i, update in enumerate(updates):
        if i > 0 and i % 30 == 0:  # Rate limiting
            time.sleep(60)  # Wait 1 minute every 30 requests
        
        result = update_issue(repo, **update)
        results.append(result)
    
    return results
```

#### Caching
```python
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def get_repo_info_cached(repo: str, cache_timeout: int = 300) -> Dict[str, Any]:
    """Cache repository information for 5 minutes"""
    cache_key = f"{repo}:{int(time.time() // cache_timeout)}"
    return get_repo_info(repo)
```

## Advanced Usage Patterns

### Bulk Operations

#### Mass Issue Creation from CSV
```python
import csv

def create_issues_from_csv(repo: str, csv_file: str) -> List[Dict[str, Any]]:
    """Create multiple issues from CSV file"""
    results = []
    
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                issue = create_issue(
                    repo=repo,
                    title=row['title'],
                    body=row.get('body', ''),
                    labels=row.get('labels', '').split(',') if row.get('labels') else None,
                    assignees=row.get('assignees', '').split(',') if row.get('assignees') else None
                )
                results.append(issue)
                print(f"✅ Created issue #{issue['number']}: {issue['title']}")
            except GitHubError as e:
                print(f"❌ Failed to create issue '{row['title']}': {e}")
    
    return results
```

#### Batch Label Management
```python
def standardize_labels(repo: str, label_mapping: Dict[str, str]) -> None:
    """Replace old labels with new standardized labels across all issues"""
    issues = list_issues(repo, state='all', limit=100)
    
    for issue in issues:
        current_labels = [label['name'] for label in issue.get('labels', [])]
        new_labels = []
        changed = False
        
        for label in current_labels:
            if label in label_mapping:
                new_labels.append(label_mapping[label])
                changed = True
            else:
                new_labels.append(label)
        
        if changed:
            update_issue(repo, issue['number'], set_labels=new_labels)
            print(f"Updated labels for issue #{issue['number']}")
```

### Automation Scripts

#### Daily Issue Summary
```python
def generate_daily_summary(repo: str) -> str:
    """Generate daily issue summary for team standup"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since = today.isoformat()
    
    # Get today's activity
    new_issues = list_issues(repo, state='open', since=since)
    closed_issues = list_issues(repo, state='closed', since=since)
    
    summary = f"📊 **Daily Issue Summary for {repo}**\n\n"
    summary += f"🆕 New issues: {len(new_issues)}\n"
    summary += f"✅ Closed issues: {len(closed_issues)}\n\n"
    
    if new_issues:
        summary += "**New Issues:**\n"
        for issue in new_issues[:5]:  # Show first 5
            summary += f"- #{issue['number']}: {issue['title']}\n"
    
    if closed_issues:
        summary += "\n**Closed Issues:**\n"
        for issue in closed_issues[:5]:  # Show first 5
            summary += f"- #{issue['number']}: {issue['title']}\n"
    
    return summary
```

#### Stale Issue Management
```python
def manage_stale_issues(repo: str, stale_days: int = 30) -> None:
    """Label and comment on stale issues"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=stale_days)
    since = cutoff_date.isoformat()
    
    issues = list_issues(repo, state='open', sort='updated', direction='asc')
    
    for issue in issues:
        updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
        
        if updated_at < cutoff_date:
            # Check if already marked as stale
            labels = [label['name'] for label in issue.get('labels', [])]
            
            if 'stale' not in labels:
                # Add stale label and comment
                update_issue(repo, issue['number'], add_labels=['stale'])
                comment_issue(
                    repo, 
                    issue['number'],
                    f"This issue has been automatically marked as stale because it has not had "
                    f"recent activity for {stale_days} days. It will be closed if no further "
                    f"activity occurs. Thank you for your contributions."
                )
                print(f"Marked issue #{issue['number']} as stale")
```

### CI/CD Integration Examples

#### GitHub Actions Workflow
```yaml
name: Issue Management

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM
  workflow_dispatch:

jobs:
  manage-issues:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Generate weekly summary
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          python issues_manager.py list ${{ github.repository }} \
            --since 7d --json > weekly_issues.json
          
          # Process and send summary
          python scripts/weekly_summary.py
```

#### Docker Integration
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY issues_manager.py .
COPY .env .

ENTRYPOINT ["python", "issues_manager.py"]
```

Usage:
```bash
docker build -t issues-manager .
docker run --rm issues-manager list CodesParadox/not_n_Issue --state open
```

### API Extensions

#### Custom Webhooks
```python
class IssueWebhookHandler:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_custom_notification(self, event_type: str, issue_data: Dict[str, Any]) -> None:
        payload = {
            'event': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'issue': {
                'number': issue_data['number'],
                'title': issue_data['title'],
                'state': issue_data['state'],
                'url': issue_data['html_url']
            }
        }
        
        requests.post(
            self.webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
```

#### Plugin System
```python
class IssuePlugin:
    def on_issue_created(self, issue: Dict[str, Any]) -> None:
        pass
    
    def on_issue_updated(self, issue: Dict[str, Any]) -> None:
        pass
    
    def on_issue_closed(self, issue: Dict[str, Any]) -> None:
        pass

class JiraIntegrationPlugin(IssuePlugin):
    def on_issue_created(self, issue: Dict[str, Any]) -> None:
        # Create corresponding Jira ticket
        jira_client.create_issue(
            summary=issue['title'],
            description=f"GitHub Issue: {issue['html_url']}"
        )

# Usage
plugins = [JiraIntegrationPlugin()]

def create_issue_with_plugins(repo: str, **kwargs) -> Dict[str, Any]:
    issue = create_issue(repo, **kwargs)
    
    for plugin in plugins:
        try:
            plugin.on_issue_created(issue)
        except Exception as e:
            print(f"Plugin error: {e}")
    
    return issue
```

This comprehensive documentation covers all aspects of the GitHub Issues Manager CLI, from basic usage to advanced integration patterns. It serves as both a user guide and developer reference for extending and maintaining the application.