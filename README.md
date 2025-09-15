# GitHub Issues Manager CLI

Single-file CLI to manage GitHub Issues with optional Slack notifications.

Features
- Create, get, update, close, complete (close with reason=completed), and reopen issues
- Comment, lock/unlock issues
- Update labels/assignees with add/remove/replace operations
- Set milestone
- Rich listing filters: state/open-closed-all, labels, creator, assignee (username|none|*), mentioned, milestone (*|none|#), sort, direction, since (ISO or relative like 7d/12h/30m)
- Optional Slack webhook notifications

Requirements
- Python 3.9+
- pip install -r requirements.txt
- Environment variables (see .env.example)

Quick start
1. Copy .env.example to .env and set your values.
2. Install deps: `pip install -r requirements.txt`
3. Examples:
   - Create: `python issues_manager.py create owner/repo -t "Bug" -b "Stacktrace" -l bug -a your-username`
   - Close: `python issues_manager.py close owner/repo 123 --reason completed`
   - Complete: `python issues_manager.py complete owner/repo 123`
   - Reopen: `python issues_manager.py reopen owner/repo 123 --reason reopened`
   - Comment: `python issues_manager.py comment owner/repo 123 -b "On it"`
   - Update: `python issues_manager.py update owner/repo 123 --state closed --reason not_planned --add-label triage --remove-assignee user1`
   - List: `python issues_manager.py list owner/repo -s all -l bug --since 7d --sort updated --direction desc -n 50`

Notes
- Repo can be just `repo` if you set GITHUB_OWNER in your .env.
- `--since` accepts ISO-8601 (International Organization for Standardization) is as follows: year, month, day, hour, minutes, seconds, and milliseconds. or relative like `7d`, `12h`, `30m`.
- `--reason` for close supports `completed` or `not_planned`; for reopen use `reopened`.
- Listing auto-filters out Pull Requests.
- Slack notifications are best-effort and won't fail the core operation.

