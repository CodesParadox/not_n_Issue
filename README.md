# GitHub Issues Manager CLI

Single-file CLI to manage GitHub Issues with optional Slack notifications.

What it is
- A Python Typer-based command-line tool to create, update, close, reopen, comment, lock/unlock, and list GitHub Issues.
- Works with any repo you specify. Examples below use not_n_Issue, but you should substitute your own repository name (and owner) when running commands.
- Optional Slack integration via an Incoming Webhook to notify your team about changes.

Key features
- Create, get, update, close, complete (close with reason=completed), reopen issues
- Comment, lock/unlock issues
- Update labels/assignees: add, remove, or replace
- Set milestone
- List with rich filters: state (open|closed|all), labels, creator, assignee (username|none|*), mentioned, milestone (*|none|#), sort, direction, since (ISO or relative: 7d/12h/30m)
- Optional Slack notifications for create/update/close/reopen/comment/lock/unlock

* [Visit The Wiki](https://github.com/CodesParadox/not_n_Issue/wiki/Documentation)

## 🚀 Overview

This script provides a complete command-line interface for managing GitHub Issues in any repository. Built with Python and designed for simplicity, it offers full CRUD operations on issues, advanced filtering capabilities, and seamless integration with Slack and GitHub Actions workflows.

**Perfect for:**
- DevOps teams managing multiple repositories
- Project managers tracking issues across projects  
- Automated workflows and CI/CD pipelines
- Teams requiring Slack notifications for issue events

## ✨ Features

### Core Issue Management
- **Create** new issues with title, body, labels, and assignees
- **Get** detailed information about specific issues
- **Update** any issue field (title, body, state, labels, assignees, milestones)
- **Close** issues with completion reasons (`completed` or `not_planned`)
- **Complete** issues (shorthand for closing with `completed` reason)
- **Reopen** closed issues with optional reason
- **Comment** on existing issues
- **Lock/Unlock** issue conversations

### Advanced Features
- **Rich filtering** for issue listing: state, labels, creator, assignee, mentioned users, milestones
- **Flexible sorting** by creation date, update date, or comment count
- **Time-based filtering** with ISO-8601 dates or relative time (`7d`, `12h`, `30m`)
- **Batch operations** on labels and assignees (add, remove, or replace)
- **Repository shortcuts** - use just `repo` name if `GITHUB_OWNER` is configured
- **JSON output** for integration with other tools
- **Slack notifications** for all operations (optional)
- **GitHub Actions integration** for automated issue notifications

## 📋 Requirements

- **Python 3.9+**
- **Dependencies**: Install with `pip install -r requirements.txt`
  - `typer==0.12.3` - CLI framework
  - `requests==2.32.3` - HTTP client for GitHub API
  - `python-dotenv==1.0.1` - Environment variable management
- **GitHub Personal Access Token** with `repo` scope
- **Slack Incoming Webhook URL** (optional, for notifications)

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/CodesParadox/not_n_Issue.git
cd not_n_Issue
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file and customize it:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# Required: GitHub Authentication
GITHUB_TOKEN=ghp_your_personal_access_token_here
# Alternative: GH_TOKEN=ghp_your_personal_access_token_here

# Optional: Default repository owner (saves typing owner/repo every time)
GITHUB_OWNER=your-github-username-or-org

# Optional: Custom GitHub API URL (for GitHub Enterprise)
GITHUB_API_URL=https://api.github.com

# Optional: Slack webhook for notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

### 4. Test the Installation
```bash
python issues_manager.py --help
```

## 📖 Usage Examples

### Basic Issue Operations

#### Create a New Issue
```bash
# Full syntax with all options
python issues_manager.py create CodesParadox/not_n_Issue \
  --title "Bug: Login not working" \
  --body "Users cannot log in after the latest update. Error appears in browser console." \
  --label bug \
  --label priority-high \
  --assignee your-username

# Simplified (if GITHUB_OWNER is set)
python issues_manager.py create not_n_Issue -t "Feature Request" -b "Add dark mode support" -l enhancement
```

#### Get Issue Details
```bash
# Get issue information
python issues_manager.py get CodesParadox/not_n_Issue 123

# Get issue as JSON for parsing
python issues_manager.py get CodesParadox/not_n_Issue 123 --json
```

#### Update Issues
```bash
# Close an issue with reason
python issues_manager.py close CodesParadox/not_n_Issue 123 --reason completed

# Quick complete (close with completed reason)
python issues_manager.py complete CodesParadox/not_n_Issue 123

# Reopen an issue
python issues_manager.py reopen CodesParadox/not_n_Issue 123 --reason reopened

# Complex update with multiple changes
python issues_manager.py update CodesParadox/not_n_Issue 123 \
  --title "Updated: Bug fixed in login system" \
  --state closed \
  --reason completed \
  --add-label fixed \
  --remove-label priority-high \
  --add-assignee maintainer1
```

### You will get Notification as soon as you Push a commit/issue to the repository

<img width="890" height="824" alt="Image" src="https://github.com/user-attachments/assets/9d07f91a-168f-4006-932b-1dfd4808bd2c" />

#### Comments and Conversation Management
```bash
# Add a comment
python issues_manager.py comment CodesParadox/not_n_Issue 123 -b "Working on this issue now"

# Lock an issue conversation
python issues_manager.py lock CodesParadox/not_n_Issue 123 --reason spam

# Unlock an issue conversation  
python issues_manager.py unlock CodesParadox/not_n_Issue 123
```

### Advanced Filtering and Listing

#### List Issues with Filters
```bash
# List open issues
python issues_manager.py list CodesParadox/not_n_Issue

# List all issues (open and closed)
python issues_manager.py list CodesParadox/not_n_Issue --state all

# Filter by labels
python issues_manager.py list CodesParadox/not_n_Issue --label bug --label priority-high

# Filter by assignee
python issues_manager.py list CodesParadox/not_n_Issue --assignee your-username

# List unassigned issues
python issues_manager.py list CodesParadox/not_n_Issue --assignee none

# Filter by creator
python issues_manager.py list CodesParadox/not_n_Issue --creator contributor-name

# Filter by milestone
python issues_manager.py list CodesParadox/not_n_Issue --milestone "v1.0"

# List issues without milestone
python issues_manager.py list CodesParadox/not_n_Issue --milestone none

# Time-based filtering
python issues_manager.py list CodesParadox/not_n_Issue --since 7d  # Last 7 days
python issues_manager.py list CodesParadox/not_n_Issue --since 12h # Last 12 hours
python issues_manager.py list CodesParadox/not_n_Issue --since 30m # Last 30 minutes
python issues_manager.py list CodesParadox/not_n_Issue --since 2024-01-01 # Since specific date

# Sorting and pagination
python issues_manager.py list CodesParadox/not_n_Issue \
  --sort updated \
  --direction desc \
  --limit 20

# Complex query example
python issues_manager.py list CodesParadox/not_n_Issue \
  --state all \
  --label bug \
  --assignee your-username \
  --since 30d \
  --sort updated \
  --direction desc \
  --limit 50 \
  --json
```

## ⚙️ Configuration Guide

### GitHub Token Setup

1. **Create a Personal Access Token:**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Give it a descriptive name like "Issues Manager CLI"
   - Select scopes: `repo` (full repository access)
   - Copy the generated token

2. **Add to Environment:**
   ```bash
   # In your .env file
   GITHUB_TOKEN=ghp_your_token_here
   ```

### Slack Integration Setup

1. **Create a Slack App:**
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Choose app name and workspace

2. **Enable Incoming Webhooks:**
   - In your app settings, go to "Incoming Webhooks"
   - Turn on "Activate Incoming Webhooks"
   - Click "Add New Webhook to Workspace"
   - Select the channel for notifications
   - Copy the webhook URL

3. **Configure the Script:**
   ```bash
   # In your .env file
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
   ```

4. **Add to GitHub Secrets (for Actions):**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `SLACK_WEBHOOK_URL`
   - Value: Your webhook URL

### GitHub Actions Integration

This repository includes a GitHub Actions workflow (`.github/workflows/notify-slack-on-issue.yml`) that automatically sends Slack notifications when issues are created, updated, or closed through the GitHub web interface.

**Workflow Features:**
- Triggers on issue events: opened, reopened, closed, edited, assigned, unassigned, labeled, unlabeled, milestoned, demilestoned
- Formats messages with issue details and context
- Includes direct links to issues
- Handles special characters in issue titles
- Provides different message formats based on the action type

**Setup:**
1. Ensure `SLACK_WEBHOOK_URL` is configured in repository secrets
2. The workflow will automatically trigger on issue events
3. No additional configuration needed

## 🔧 Command Reference

### Global Options
- `--help` - Show help message
- `--install-completion` - Install shell completion
- `--show-completion` - Show completion script

### Commands Overview

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `create` | Create new issue | `--title`, `--body`, `--label`, `--assignee` |
| `get` | Get issue details | `--json` |
| `update` | Update issue fields | `--state`, `--reason`, `--add-label`, `--remove-label` |
| `close` | Close issue | `--reason` (completed/not_planned) |
| `complete` | Close with completed reason | None |
| `reopen` | Reopen closed issue | `--reason` (reopened) |
| `comment` | Add comment | `--body` |
| `lock` | Lock conversation | `--reason` |
| `unlock` | Unlock conversation | None |
| `list` | List issues with filters | `--state`, `--label`, `--assignee`, `--since`, `--sort` |

### Repository Format
- **Full format:** `owner/repository` (e.g., `CodesParadox/not_n_Issue`)
- **Short format:** `repository` (requires `GITHUB_OWNER` in .env)

### Time Format Support
- **Relative:** `7d` (days), `12h` (hours), `30m` (minutes)
- **ISO-8601:** `2024-01-01`, `2024-01-01T10:30:00Z`

### State Reasons
- **Close reasons:** `completed`, `not_planned`
- **Reopen reason:** `reopened`
- **Lock reasons:** `off-topic`, `too heated`, `resolved`, `spam`

## 📝 Notes and Tips

- **Repository shortcuts:** Set `GITHUB_OWNER` in `.env` to use just repository names instead of `owner/repo`
- **Slack notifications:** Are best-effort and won't fail the core operation if Slack is unavailable
- **Issue vs PR filtering:** The list command automatically filters out Pull Requests, showing only issues
- **Error handling:** All commands provide clear error messages for debugging
- **Rate limiting:** Respects GitHub API rate limits automatically
- **JSON output:** Most commands support `--json` flag for scripting and automation

## 🚨 Troubleshooting

### Common Issues

1. **"GITHUB_TOKEN not set" error:**
   - Ensure your `.env` file exists and contains a valid token
   - Check token permissions include `repo` scope

2. **"Repository not found" error:**
   - Verify repository name spelling
   - Ensure your token has access to the repository
   - For private repos, ensure token has appropriate permissions

3. **Slack notifications not working:**
   - Verify `SLACK_WEBHOOK_URL` is correct
   - Test the webhook URL directly with curl
   - Check Slack app configuration

4. **"Invalid reason" errors:**
   - Use only supported reasons for each operation
   - Close: `completed` or `not_planned`
   - Reopen: `reopened`

## 🔗 Integration Examples

### CI/CD Pipeline Integration
```bash
# In your CI/CD script
python issues_manager.py create your-org/your-repo \
  --title "Build failed in $CI_PIPELINE_ID" \
  --body "Build details: $CI_PIPELINE_URL" \
  --label ci-failure \
  --assignee devops-team
```

### Automated Issue Management
```bash
# Close all completed issues older than 30 days
python issues_manager.py list your-org/your-repo \
  --state closed \
  --since 30d \
  --json | jq -r '.[].number' | \
  xargs -I {} python issues_manager.py complete your-org/your-repo {}
```

This tool is designed to be the **repository name is based on your own repository you want to use this script** - simply replace `CodesParadox/not_n_Issue` with your own repository path in all examples above.

