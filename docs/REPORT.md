# Issues Manager CLI – Deep Dive Report

This document explains the WhatN_Issue GitHub Issues Manager CLI in depth: goals, configuration, usage, internal functions, Slack integration, and how to run it in GitHub Actions.

Table of contents
- Goals and scope
- How it works end‑to‑end
- Configuration and secrets
- CLI usage and syntax with examples
- Function‑by‑function walkthrough
- Error handling and edge cases
- Implementation details and design choices
- GitHub Actions usage with sample workflow YAML
- Security and secret management
- Troubleshooting and FAQs
- Future enhancements

Goals and scope
- Provide a single‑file, dependency‑light CLI to manage GitHub Issues from terminals and CI.
- Offer convenient operations: create, get, update, close, complete, reopen, comment, lock/unlock, and list (with rich filters).
- Support optional Slack notifications via a simple Incoming Webhook.
- Be safe by default: clear errors for auth/validation failures, best‑effort Slack notifications.

How it works end‑to‑end
- Typer builds a CLI around small, focused functions that call GitHub’s REST API.
- Configuration comes from environment variables (loaded from .env in local runs via python‑dotenv).
- Each command validates inputs, calls the corresponding operation, and prints concise results; errors are raised as GitHubError and returned as non‑zero exit codes.
- If SLACK_WEBHOOK_URL is set, the script posts a minimal notification summarizing what happened.

Configuration and secrets
Environment variables (see .env.example):
- GITHUB_TOKEN or GH_TOKEN: Personal Access Token or GitHub Actions’ GITHUB_TOKEN with appropriate scopes to read/write issues.
- GITHUB_OWNER (optional): Default owner (user/org). When provided, you can pass just repo instead of owner/repo in commands.
- GITHUB_API_URL (optional): Defaults to https://api.github.com.
- SLACK_WEBHOOK_URL (optional): Slack Incoming Webhook to post notifications.

Setup steps
- Local runs: Copy .env.example to .env and set values. Do not commit .env.
- Slack:
  1) Create a Slack Incoming Webhook (or enable for your workspace).
  2) Choose a channel the webhook will post to and copy the webhook URL.
  3) Locally: put the URL into .env as SLACK_WEBHOOK_URL.
  4) In GitHub Actions: store the webhook as a repository/org Secret (e.g., SLACK_WEBHOOK_URL) and pass it as an env var.

CLI usage and syntax with examples
- You can target any repository. Examples use not_n_Issue; replace with your own repo name, or use owner/repo explicitly.
- If you set GITHUB_OWNER, you can pass just not_n_Issue; otherwise use CodesParadox/not_n_Issue (or your owner/repo).

Global help
- python issues_manager.py --help
- python issues_manager.py <command> --help

Create
- Syntax: python issues_manager.py create <repo> -t <title> [-b <body>] [-l <label> ...] [-a <assignee> ...] [-m <milestone>]
- Example: python issues_manager.py create not_n_Issue -t "Bug: crash on start" -b "Stacktrace..." -l bug -a your-username

Get
- Syntax: python issues_manager.py get <repo> <number> [--json]
- Example: python issues_manager.py get not_n_Issue 123 --json

Comment
- Syntax: python issues_manager.py comment <repo> <number> -b <body>
- Example: python issues_manager.py comment not_n_Issue 123 -b "Working on this now."

Update
- Syntax: python issues_manager.py update <repo> <number> [--title T] [--body B] [--state open|closed] [--reason completed|reopened|not_planned] [--add-label L ...] [--remove-label L ...] [--set-label L ...] [--add-assignee U ...] [--remove-assignee U ...] [--set-assignee U ...] [-m N]
- Examples:
  - Add labels: python issues_manager.py update not_n_Issue 123 --add-label triage --add-label backend
  - Replace labels: python issues_manager.py update not_n_Issue 123 --set-label bug --set-label urgent
  - Close with reason: python issues_manager.py update not_n_Issue 123 --state closed --reason not_planned

Close / complete / reopen
- Close: python issues_manager.py close not_n_Issue 123 --reason completed
- Complete (shorthand): python issues_manager.py complete not_n_Issue 123
- Reopen: python issues_manager.py reopen not_n_Issue 123 --reason reopened

Lock / unlock
- Lock: python issues_manager.py lock not_n_Issue 123 --reason resolved
- Unlock: python issues_manager.py unlock not_n_Issue 123

List
- Syntax: python issues_manager.py list <repo> [-s open|closed|all] [--label L ...] [--creator U] [--assignee U|none|*] [--mentioned U] [--milestone N|*|none] [--sort created|updated|comments] [--direction asc|desc] [--since ISO|7d|12h|30m] [-n LIMIT] [--json]
- Examples:
  - Open issues: python issues_manager.py list not_n_Issue
  - All with filters: python issues_manager.py list not_n_Issue -s all -l bug --since 7d --sort updated --direction desc -n 50

Function‑by‑function walkthrough
- Exceptions: class GitHubError(Exception)
  - A custom error for clear CLI failures. Commands catch it and exit non‑zero.

- gh_headers() -> dict
  - Ensures a token exists; raises GitHubError if missing.
  - Returns headers for GitHub REST v3 with an explicit API version and user‑agent.

- normalize_repo(repo: str) -> str
  - Accepts owner/repo or just repo if GITHUB_OWNER is set; otherwise raises GitHubError.

- notify_slack(text: str) -> None
  - If SLACK_WEBHOOK_URL is present, POSTs {"text": text} with a timeout; exceptions are swallowed so core CLI never fails on Slack issues.

- parse_since(value: Optional[str]) -> Optional[str]
  - Accepts None (returns None), ISO‑8601 (YYYY‑MM‑DD or full ISO, with optional Z), or relative shorthand like 7d/12h/30m; returns an ISO UTC timestamp.
  - On invalid inputs, raises GitHubError with usage guidance.

- create_issue(repo, title, body=None, labels=None, assignees=None, milestone=None) -> dict
  - Builds payload and POSTs to /repos/{owner}/{repo}/issues. On success, Slack‑notifies and returns the issue JSON.

- patch_issue(repo, issue_number, data) -> dict
  - Core PATCH call to update issue fields; raises on non‑2xx.

- get_issue(repo, issue_number) -> dict
  - GETs a single issue; raises on non‑2xx.

- close_issue(repo, issue_number, reason=None) -> dict
  - Sets state=closed; if reason is provided, validates completed|not_planned and sets state_reason; Slack‑notifies.

- reopen_issue(repo, issue_number, reason=None) -> dict
  - Sets state=open; if reason is provided, must be reopened; Slack‑notifies.

- comment_issue(repo, issue_number, body) -> dict
  - POSTs a new comment and Slack‑notifies (truncates body preview).

- lock_issue(repo, issue_number, lock_reason=None) -> None
  - PUT to /lock; expects 204; Slack‑notifies.

- unlock_issue(repo, issue_number) -> None
  - DELETE /lock; expects 204; Slack‑notifies.

- _apply_list_ops(current, add, remove, replace) -> (list|None, bool)
  - If replace is provided, it wins and de‑duplicates; else applies add then remove. Returns final list or None and a boolean indicating replace was used.

- update_issue(...many optional fields...) -> dict
  - Validates state and state_reason. Fetches current issue if needed to apply add/remove (without replace) for labels/assignees. Calls patch_issue, Slack‑notifies, returns updated JSON.

- list_issues(repo, state="open", labels=None, creator=None, assignee=None, mentioned=None, milestone=None, sort="created", direction="desc", since=None, limit=50) -> list
  - Paginates through the Issues API, filters out PRs, respects limit, and supports filters. Converts --since via parse_since.

Error handling and edge cases
- Missing token: gh_headers raises a clear GitHubError; commands exit non‑zero with a concise message.
- Repo format: normalize_repo enforces owner/repo unless GITHUB_OWNER is set.
- State and reasons: close supports completed|not_planned; reopen supports reopened; update supports completed|reopened|not_planned.
- Slack failures: ignored by design to not break core operations.
- Since parsing: accepts ISO (YYYY‑MM‑DD or full ISO with Z) and relative 7d/12h/30m; anything else errors with guidance.
- Pagination: list_issues follows Link: rel="next" until reaching limit; filters PRs by skipping items with a pull_request key.

Implementation details and design choices
- HTTP client: requests with explicit timeouts (30s for GitHub, 15s for Slack).
- Headers: GitHub API version header (X‑GitHub‑Api‑Version) and a static user‑agent for traceability.
- Idempotence: update paths use patch_issue; add/remove/replace lists with a helper to avoid duplicates.
- Data shapes: functions return parsed JSON from GitHub as Python dicts/lists for composability.

GitHub Actions usage with sample workflow YAML
- Typical use cases:
  - Nightly issue reports to Slack.
  - Automatic labeling or closing of issues under certain conditions.
  - One‑off maintenance via workflow_dispatch.

Secrets required
- GITHUB_TOKEN: Automatically provided as secrets.GITHUB_TOKEN; expose as env GH_TOKEN for the CLI.
- SLACK_WEBHOOK_URL: Create a repository/org Secret with your Slack webhook URL if you want notifications.
- Optional: set GITHUB_OWNER as an environment variable in the workflow to shorten repo args.

Example workflow (issues-manager.yml)
- Triggers on manual dispatch and a weekly schedule. Lists the latest open issues and posts notifications if Slack is configured.

name: Issues Manager

on:
  workflow_dispatch:
    inputs:
      repo:
        description: "owner/repo to target (defaults to CodesParadox/not_n_Issue)"
        required: false
        default: "CodesParadox/not_n_Issue"
  schedule:
    - cron: "0 6 * * 1"  # every Monday 06:00 UTC

jobs:
  run-cli:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: List issues
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_OWNER: CodesParadox
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          python issues_manager.py list "${{ github.event.inputs.repo || 'CodesParadox/not_n_Issue' }}" -s open -n 20

      # Example: Create an issue via workflow_dispatch if a title is provided
      # - name: Create an issue (optional)
      #   if: ${{ inputs.title != '' }}
      #   env:
      #     GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      #   run: |
      #     python issues_manager.py create "${{ github.event.inputs.repo }}" -t "${{ inputs.title }}" -b "Created by CI"

Security and secret management
- Never commit .env or secrets; keep .env in .gitignore.
- Use GitHub Secrets for sensitive values in CI. The built‑in GITHUB_TOKEN is scoped to the repo and is usually sufficient for issues.
- Restrict Slack webhook to a dedicated channel and rotate if leaked.

Troubleshooting and FAQs
- 401/403 from GitHub: Verify token validity/scopes and repository permissions; ensure correct owner/repo.
- Missing token error: Set GITHUB_TOKEN or GH_TOKEN. In CI, pass secrets.GITHUB_TOKEN as GH_TOKEN.
- Slack not receiving messages: Verify SLACK_WEBHOOK_URL; remember Slack notifications are best‑effort.
- No issues found on list: Check filters (state, labels, since, milestone). Remove filters to confirm connectivity.

Future enhancements
- Add subcommands for bulk operations (e.g., close by query).
- Interactive TUI mode for listing and editing issues.
- Better rate‑limit handling and retries for transient GitHub API errors.
- Optional structured outputs (e.g., NDJSON) for downstream scripting.

