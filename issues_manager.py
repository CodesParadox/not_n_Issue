# issues_manager.py
# Single-file GitHub Issues manager CLI with optional Slack notification.
# Requirements:
#   pip install typer requests python-dotenv
# Usage examples:
#   python issues_manager.py create CodesParadox/not_n_Issue --title "Bug" --body "Stacktrace..." --label bug
#   python issues_manager.py close  not_n_Issue 12
#   python issues_manager.py list   not_n_Issue --state open --limit 20


from __future__ import annotations
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
import requests
import typer
from dotenv import load_dotenv

app = typer.Typer(help="GitHub Issues Manager CLI (single-file)")

# Load .env if present
load_dotenv()

# --- Config ---
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
# Accept common env var names
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
GITHUB_OWNER_DEFAULT = os.getenv("GITHUB_OWNER")  # optional convenience to avoid typing owner/repo

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


# --- Exceptions ---
class GitHubError(Exception):
    pass


# --- Helpers ---
def gh_headers() -> Dict[str, str]:
    if not GITHUB_TOKEN:
        raise GitHubError("GITHUB_TOKEN/GH_TOKEN is not set. Put it in your .env file.")
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "issues-manager-cli"
    }


def normalize_repo(repo: str) -> str:
    """
    Accepts 'owner/repo' or just 'repo' if GITHUB_OWNER is set.
    """
    if "/" in repo:
        return repo
    if not GITHUB_OWNER_DEFAULT:
        raise GitHubError("Repo must be 'owner/repo' or set GITHUB_OWNER in .env.")
    return f"{GITHUB_OWNER_DEFAULT}/{repo}"


def notify_slack(text: str) -> None:
    """
    Send a simple Slack message via Incoming Webhook URL if configured.
    This is optional; if SLACK_WEBHOOK_URL is missing, do nothing.
    """
    if not SLACK_WEBHOOK_URL:
        return
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=15)
        resp.raise_for_status()
    except Exception:
        # We don't raise here to avoid failing the core command if Slack is down.
        pass


def parse_since(value: Optional[str]) -> Optional[str]:
    """Accepts ISO-8601 (YYYY-MM-DD or full timestamp) or relative like '7d', '12h', '30m'. Returns ISO string."""
    if not value:
        return None
    v = value.strip()
    try:
        # Try full ISO first
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    # Relative format
    try:
        amount = int(v[:-1])
        unit = v[-1].lower()
        if unit == 'd':
            delta = timedelta(days=amount)
        elif unit == 'h':
            delta = timedelta(hours=amount)
        elif unit == 'm':
            delta = timedelta(minutes=amount)
        else:
            raise ValueError
        dt = datetime.now(timezone.utc) - delta
        return dt.isoformat()
    except Exception:
        raise GitHubError("Invalid --since value. Use ISO-8601 (e.g., 2024-01-01 or 2024-01-01T12:00:00Z) or relative like 7d/12h/30m.")


# --- Core GitHub operations ---
def create_issue(
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    milestone: Optional[int] = None,
) -> Dict[str, Any]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues"
    payload: Dict[str, Any] = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    if milestone is not None:
        payload["milestone"] = milestone

    resp = requests.post(url, headers=gh_headers(), json=payload, timeout=30)
    if resp.status_code >= 300:
        raise GitHubError(f"Create issue failed: {resp.status_code} {resp.text}")
    issue = resp.json()
    notify_slack(f"[{full}] Created issue #{issue['number']}: {issue['title']}\n{issue['html_url']}")
    return issue


def patch_issue(repo: str, issue_number: int, data: Dict[str, Any]) -> Dict[str, Any]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues/{int(issue_number)}"
    resp = requests.patch(url, headers=gh_headers(), json=data, timeout=30)
    if resp.status_code >= 300:
        raise GitHubError(f"Update issue failed: {resp.status_code} {resp.text}")
    return resp.json()


def get_issue(repo: str, issue_number: int) -> Dict[str, Any]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues/{int(issue_number)}"
    resp = requests.get(url, headers=gh_headers(), timeout=30)
    if resp.status_code >= 300:
        raise GitHubError(f"Get issue failed: {resp.status_code} {resp.text}")
    return resp.json()


def close_issue(repo: str, issue_number: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """Close an issue with optional state_reason: completed | not_planned."""
    payload: Dict[str, Any] = {"state": "closed"}
    if reason:
        r = reason.lower().replace("-", "_")
        if r not in {"completed", "not_planned"}:
            raise GitHubError("Invalid reason. Use completed or not_planned.")
        payload["state_reason"] = r
    issue = patch_issue(repo, issue_number, payload)
    full = normalize_repo(repo)
    title = issue.get('title', '')
    msg_reason = f" ({payload.get('state_reason')})" if payload.get('state_reason') else ""
    notify_slack(f"[{full}] Closed issue #{issue['number']}{msg_reason}: {title}\n{issue.get('html_url','')}")
    return issue


def reopen_issue(repo: str, issue_number: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """Reopen an issue. Optionally set state_reason=reopened."""
    payload: Dict[str, Any] = {"state": "open"}
    if reason:
        r = reason.lower()
        if r != "reopened":
            raise GitHubError("Invalid reason for reopen. Use: reopened")
        payload["state_reason"] = r
    issue = patch_issue(repo, issue_number, payload)
    full = normalize_repo(repo)
    notify_slack(f"[{full}] Reopened issue #{issue['number']}: {issue.get('title','')}\n{issue.get('html_url','')}")
    return issue


def comment_issue(repo: str, issue_number: int, body: str) -> Dict[str, Any]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues/{int(issue_number)}/comments"
    resp = requests.post(url, headers=gh_headers(), json={"body": body}, timeout=30)
    if resp.status_code >= 300:
        raise GitHubError(f"Add comment failed: {resp.status_code} {resp.text}")
    comment = resp.json()
    notify_slack(f"[{full}] Commented on issue #{issue_number}: {body[:140]}\n{comment.get('html_url','')}")
    return comment


def lock_issue(repo: str, issue_number: int, lock_reason: Optional[str] = None) -> None:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues/{int(issue_number)}/lock"
    payload = {"lock_reason": lock_reason} if lock_reason else None
    resp = requests.put(url, headers=gh_headers(), json=payload, timeout=30)
    if resp.status_code not in {204}:
        raise GitHubError(f"Lock issue failed: {resp.status_code} {resp.text}")
    notify_slack(f"[{full}] Locked issue #{issue_number}{f' (reason: {lock_reason})' if lock_reason else ''}")


def unlock_issue(repo: str, issue_number: int) -> None:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues/{int(issue_number)}/lock"
    resp = requests.delete(url, headers=gh_headers(), timeout=30)
    if resp.status_code not in {204}:
        raise GitHubError(f"Unlock issue failed: {resp.status_code} {resp.text}")
    notify_slack(f"[{full}] Unlocked issue #{issue_number}")


def _apply_list_ops(current: List[str], add: Optional[List[str]], remove: Optional[List[str]], replace: Optional[List[str]]) -> Tuple[Optional[List[str]], bool]:
    """Helper to determine final list. Returns (final_list_or_None, used_replace).
    If replace provided, it wins. Otherwise, apply add/remove to current.
    """
    if replace is not None:
        return list(dict.fromkeys(replace)), True
    if not add and not remove:
        return None, False
    cur = list(current)
    if add:
        for a in add:
            if a not in cur:
                cur.append(a)
    if remove:
        cur = [x for x in cur if x not in set(remove)]
    return cur, False


def update_issue(
    repo: str,
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    state_reason: Optional[str] = None,
    add_labels: Optional[List[str]] = None,
    remove_labels: Optional[List[str]] = None,
    set_labels: Optional[List[str]] = None,
    add_assignees: Optional[List[str]] = None,
    remove_assignees: Optional[List[str]] = None,
    set_assignees: Optional[List[str]] = None,
    milestone: Optional[int] = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if title is not None:
        data["title"] = title
    if body is not None:
        data["body"] = body
    if state is not None:
        s = state.lower()
        if s not in {"open", "closed"}:
            raise GitHubError("state must be open or closed")
        data["state"] = s
    if state_reason is not None:
        r = state_reason.lower().replace("-", "_")
        if r not in {"completed", "reopened", "not_planned"}:
            raise GitHubError("state_reason must be one of: completed, reopened, not_planned")
        data["state_reason"] = r

    # For labels/assignees we may need the current lists if doing add/remove
    needs_issue = any([
        (add_labels or remove_labels) and not set_labels,
        (add_assignees or remove_assignees) and not set_assignees,
    ])
    current_issue: Optional[Dict[str, Any]] = None
    if needs_issue:
        # Fetch issue once if needed for current lists
        current_issue = get_issue(repo, issue_number)

    if milestone is not None:
        data["milestone"] = milestone

    # Labels
    if current_issue is not None:
        cur_labels = [l["name"] for l in current_issue.get("labels", [])]
    else:
        cur_labels = []
    final_labels, used_replace = _apply_list_ops(cur_labels, add_labels, remove_labels, set_labels)
    if used_replace or final_labels is not None:
        data["labels"] = final_labels if final_labels is not None else []

    # Assignees
    if current_issue is not None:
        cur_assignees = [a["login"] for a in current_issue.get("assignees", [])]
    else:
        cur_assignees = []
    final_assignees, used_replace_a = _apply_list_ops(cur_assignees, add_assignees, remove_assignees, set_assignees)
    if used_replace_a or final_assignees is not None:
        data["assignees"] = final_assignees if final_assignees is not None else []

    updated = patch_issue(repo, issue_number, data)
    full = normalize_repo(repo)
    notify_slack(f"[{full}] Updated issue #{updated['number']}: {updated.get('title','')}\n{updated.get('html_url','')}")
    return updated


def list_issues(
    repo: str,
    state: str = "open",   # open | closed | all
    labels: Optional[List[str]] = None,
    creator: Optional[str] = None,
    assignee: Optional[str] = None,
    mentioned: Optional[str] = None,
    milestone: Optional[str] = None,  # number or '*', 'none'
    sort: str = "created",  # created | updated | comments
    direction: str = "desc", # asc | desc
    since: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues"
    params: Dict[str, Any] = {
        "state": state,
        "per_page": min(100, max(1, limit)),
        "sort": sort,
        "direction": direction,
    }
    if labels:
        params["labels"] = ",".join(labels)
    if creator:
        params["creator"] = creator
    if assignee:
        params["assignee"] = assignee
    if mentioned:
        params["mentioned"] = mentioned
    if milestone is not None:
        params["milestone"] = milestone
    if since:
        params["since"] = parse_since(since)

    items: List[Dict[str, Any]] = []
    page = 1
    while len(items) < limit:
        params["page"] = page
        resp = requests.get(url, headers=gh_headers(), params=params, timeout=30)
        if resp.status_code >= 300:
            raise GitHubError(f"List issues failed: {resp.status_code} {resp.text}")
        batch = resp.json()
        # Filter out PRs (GitHub mixes PRs in the Issues API)
        batch = [it for it in batch if "pull_request" not in it]
        items.extend(batch)
        if "next" not in resp.links:
            break
        page += 1
    return items[:limit]


# --- CLI Commands ---
@app.command("create")
def cmd_create(
    repo: str = typer.Argument(..., help="owner/repo or just repo if GITHUB_OWNER set"),
    title: str = typer.Option(..., "--title", "-t", help="Issue title"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Issue body/description"),
    labels: Optional[List[str]] = typer.Option(None, "--label", "-l", help="Repeatable: -l bug -l backend"),
    assignees: Optional[List[str]] = typer.Option(None, "--assignee", "-a", help="Repeatable: -a user1 -a user2"),
    milestone: Optional[int] = typer.Option(None, "--milestone", "-m", help="Milestone number"),
):
    """Create a new issue."""
    try:
        issue = create_issue(repo, title, body, labels, assignees, milestone)
        typer.echo(f" Created issue #{issue['number']}: {issue['html_url']}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("get")
def cmd_get(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number"),
    json_out: bool = typer.Option(False, "--json", help="Print raw JSON"),
):
    """Get a single issue by number."""
    try:
        it = get_issue(repo, number)
        if json_out:
            typer.echo(json.dumps(it, indent=2))
            return
        typer.echo(f"#{it['number']} [{it['state']}] {it['title']} -> {it['html_url']}")
        sr = it.get('state_reason')
        if sr:
            typer.echo(f"  reason: {sr}")
        if it.get('labels'):
            labels = ", ".join([l['name'] for l in it['labels']])
            typer.echo(f"  labels: {labels}")
        if it.get('assignees'):
            assg = ", ".join([a['login'] for a in it['assignees']])
            typer.echo(f"  assignees: {assg}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("close")
def cmd_close(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number to close"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="completed|not_planned"),
):
    """Close an existing issue by number."""
    try:
        issue = close_issue(repo, number, reason)
        typer.echo(f" Closed issue #{issue['number']}: {issue['html_url']}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("complete")
def cmd_complete(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number to mark completed"),
):
    """Shorthand: close an issue with reason=completed."""
    try:
        issue = close_issue(repo, number, reason="completed")
        typer.echo(f" Completed issue #{issue['number']}: {issue['html_url']}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("reopen")
def cmd_reopen(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number to reopen"),
    reason: Optional[str] = typer.Option(None, "--reason", help="Use 'reopened' to set state_reason"),
):
    """Reopen a closed issue."""
    try:
        issue = reopen_issue(repo, number, reason)
        typer.echo(f" Reopened issue #{issue['number']}: {issue['html_url']}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("comment")
def cmd_comment(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number"),
    body: str = typer.Option(..., "--body", "-b", help="Comment body"),
):
    """Add a comment to an issue."""
    try:
        c = comment_issue(repo, number, body)
        typer.echo(f" Comment added: {c.get('html_url','')}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("lock")
def cmd_lock(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number"),
    lock_reason: Optional[str] = typer.Option(None, "--reason", help="off-topic|too heated|resolved|spam"),
):
    """Lock an issue's conversation."""
    try:
        lock_issue(repo, number, lock_reason)
        typer.echo(" Issue locked")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("unlock")
def cmd_unlock(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number"),
):
    """Unlock an issue's conversation."""
    try:
        unlock_issue(repo, number)
        typer.echo(" Issue unlocked")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("update")
def cmd_update(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    body: Optional[str] = typer.Option(None, "--body", "-b"),
    state: Optional[str] = typer.Option(None, "--state", help="open|closed"),
    state_reason: Optional[str] = typer.Option(None, "--reason", help="completed|reopened|not_planned"),
    add_label: Optional[List[str]] = typer.Option(None, "--add-label", help="Add labels"),
    remove_label: Optional[List[str]] = typer.Option(None, "--remove-label", help="Remove labels"),
    set_label: Optional[List[str]] = typer.Option(None, "--set-label", help="Replace labels (overrides add/remove)"),
    add_assignee: Optional[List[str]] = typer.Option(None, "--add-assignee", help="Add assignees"),
    remove_assignee: Optional[List[str]] = typer.Option(None, "--remove-assignee", help="Remove assignees"),
    set_assignee: Optional[List[str]] = typer.Option(None, "--set-assignee", help="Replace assignees (overrides add/remove)"),
    milestone: Optional[int] = typer.Option(None, "--milestone", "-m", help="Milestone number"),
):
    """Update fields on an issue, including state and state_reason."""
    try:
        it = update_issue(
            repo,
            number,
            title=title,
            body=body,
            state=state,
            state_reason=state_reason,
            add_labels=add_label,
            remove_labels=remove_label,
            set_labels=set_label,
            add_assignees=add_assignee,
            remove_assignees=remove_assignee,
            set_assignees=set_assignee,
            milestone=milestone,
        )
        typer.echo(f" Updated issue #{it['number']}: {it.get('html_url','')}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("list")
def cmd_list(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    state: str = typer.Option("open", "--state", "-s", help="open|closed|all", case_sensitive=False),
    label: Optional[List[str]] = typer.Option(None, "--label", "-l", help="Filter by labels"),
    creator: Optional[str] = typer.Option(None, "--creator", help="Filter by creator"),
    assignee: Optional[str] = typer.Option(None, "--assignee", help="Filter by assignee (username|none|*)"),
    mentioned: Optional[str] = typer.Option(None, "--mentioned", help="Filter by mentioned user"),
    milestone: Optional[str] = typer.Option(None, "--milestone", help="milestone number|*|none"),
    sort: str = typer.Option("created", "--sort", help="created|updated|comments"),
    direction: str = typer.Option("desc", "--direction", help="asc|desc"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO datetime or relative 7d/12h/30m"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max number to fetch (<= 100 recommended)"),
    json_out: bool = typer.Option(False, "--json", help="Print raw JSON"),
):
    """List issues with optional filtering."""
    s = state.lower()
    if s not in {"open", "closed", "all"}:
        typer.echo("❌ --state must be one of: open, closed, all")
        raise typer.Exit(2)
    if sort not in {"created", "updated", "comments"}:
        typer.echo("❌ --sort must be one of: created, updated, comments")
        raise typer.Exit(2)
    if direction not in {"asc", "desc"}:
        typer.echo("❌ --direction must be one of: asc, desc")
        raise typer.Exit(2)
    try:
        issues = list_issues(repo, s, label, creator, assignee, mentioned, milestone, sort, direction, since, limit)
        if json_out:
            typer.echo(json.dumps(issues, indent=2))
            return
        if not issues:
            typer.echo("No issues found.")
            raise typer.Exit(0)
        for it in issues:
            sr = it.get('state_reason')
            extra = f" | reason: {sr}" if sr else ""
            typer.echo(f"#{it['number']} [{it['state']}] {it['title']}{extra} -> {it['html_url']}")
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
