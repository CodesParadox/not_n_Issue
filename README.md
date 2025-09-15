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

Requirements
- Python 3.9+
- Dependencies: requests, typer, python-dotenv
- Install with: pip install -r requirements.txt

Configuration
- Create a .env file (never commit it) using .env.example as a template.
- Variables:
  - GITHUB_TOKEN or GH_TOKEN: a Personal Access Token with repo scope (or use Actions-provided GITHUB_TOKEN in CI).
  - GITHUB_OWNER: optional default owner; lets you pass just the repo name instead of owner/repo.
  - GITHUB_API_URL: defaults to https://api.github.com.
  - SLACK_WEBHOOK_URL: optional Slack Incoming Webhook URL to post notifications.

Example .env
- Don’t commit secrets. Keep .env out of version control.

GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=CodesParadox
# GITHUB_API_URL=https://api.github.com
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ

Quick start
1) Setup
- Copy .env.example to .env and fill in values.
- Install dependencies: pip install -r requirements.txt

2) Run help
- python issues_manager.py --help
- python issues_manager.py create --help
- python issues_manager.py list --help

3) Use with your repo
- Replace not_n_Issue with your repository name, or set GITHUB_OWNER to avoid typing the owner.

Common commands (replace owner/repo with your own)
- If GITHUB_OWNER is set in .env, you can use just not_n_Issue; otherwise use CodesParadox/not_n_Issue.

Create
- python issues_manager.py create not_n_Issue -t "Bug: crash on start" -b "Stacktrace here" -l bug -a your-username
- python issues_manager.py create CodesParadox/not_n_Issue -t "Feature: export" -b "CSV export" -l enhancement

Get
- python issues_manager.py get not_n_Issue 123
- python issues_manager.py get not_n_Issue 123 --json

Comment
- python issues_manager.py comment not_n_Issue 123 -b "Working on this now."

Update fields
- python issues_manager.py update not_n_Issue 123 --title "New title" --body "Updated body"
- python issues_manager.py update not_n_Issue 123 --add-label triage --add-label backend
- python issues_manager.py update not_n_Issue 123 --remove-label triage
- python issues_manager.py update not_n_Issue 123 --set-label bug --set-label urgent
- python issues_manager.py update not_n_Issue 123 --add-assignee dev1 --remove-assignee dev2
- python issues_manager.py update not_n_Issue 123 --state closed --reason not_planned
- python issues_manager.py update not_n_Issue 123 --milestone 1

Close / complete / reopen
- python issues_manager.py close not_n_Issue 123 --reason completed
- python issues_manager.py complete not_n_Issue 123
- python issues_manager.py reopen not_n_Issue 123 --reason reopened

Lock / unlock
- python issues_manager.py lock not_n_Issue 123 --reason resolved
- python issues_manager.py unlock not_n_Issue 123

List issues
- python issues_manager.py list not_n_Issue
- python issues_manager.py list not_n_Issue -s all -l bug --since 7d --sort updated --direction desc -n 50
- python issues_manager.py list not_n_Issue --assignee your-username
- python issues_manager.py list not_n_Issue --milestone none
- python issues_manager.py list not_n_Issue --creator your-username --json

Arguments and options summary
- repo: owner/repo or just repo (if GITHUB_OWNER set)
- --title/-t, --body/-b: strings
- --label/-l, --assignee/-a: repeatable flags (can pass multiple)
- --milestone/-m: milestone number
- --state: open|closed
- --reason: completed|reopened|not_planned (close: completed|not_planned, reopen: reopened)
- --since: ISO-8601 or relative (e.g., 2024-01-01T12:00:00Z, 7d, 12h, 30m)
- --sort: created|updated|comments; --direction: asc|desc; --limit/-n: number of items
- --json: print raw JSON for get/list

Slack integration
- Optional. Set SLACK_WEBHOOK_URL in .env to receive notifications for actions (create, update, close, reopen, comment, lock/unlock).
- Best practice in CI: store SLACK_WEBHOOK_URL as an encrypted GitHub secret, not in your repo.

Run in GitHub Actions (optional)
- You can run this CLI in CI to automate labeling, closing stale issues, or nightly reports.
- Store your secrets (e.g., SLACK_WEBHOOK_URL) in repo or org Secrets.
- See docs/REPORT.md for a sample workflow YAML and deeper explanation.

Troubleshooting
- "GITHUB_TOKEN/GH_TOKEN is not set": set it in .env or in CI as an env var/secret.
- 401/403 errors: check token scopes and repository permissions; verify owner/repo.
- Slack doesn’t notify: verify SLACK_WEBHOOK_URL; notifications are best-effort and won’t block commands.

Next steps
- For a deep dive into functions, API calls, error handling, Slack setup, and CI usage, read docs/REPORT.md.
