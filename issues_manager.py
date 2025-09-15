# issues_manager.py
# Single-file GitHub Issues manager CLI with optional Slack notification.
# Requirements:
#   pip install typer requests python-dotenv
# Usage examples:
#   python issues_manager.py create CodesParadox/DevOpsCourseAug23 --title "Bug" --body "Stacktrace..." --label bug
#   python issues_manager.py close  DevOpsCourseAug23 12
#   python issues_manager.py list   DevOpsCourseAug23 --state open --limit 20

from __future__ import annotations
import os
from typing import Optional, List, Dict, Any
import requests
import typer
from dotenv import load_dotenv

app = typer.Typer(help="GitHub Issues Manager CLI (single-file)")

# Load .env if present
load_dotenv()

# --- Config ---
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER_DEFAULT = os.getenv("GITHUB_OWNER")  # optional convenience

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # optional


# --- Exceptions ---
class GitHubError(Exception):
    pass


# --- Helpers ---
def gh_headers() -> Dict[str, str]:
    if not GITHUB_TOKEN:
        raise GitHubError("GITHUB_TOKEN is not set. Put it in your .env file.")
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


# --- Core GitHub operations ---
def create_issue(
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
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

    resp = requests.post(url, headers=gh_headers(), json=payload, timeout=30)
    if resp.status_code >= 300:
        raise GitHubError(f"Create issue failed: {resp.status_code} {resp.text}")
    issue = resp.json()
    notify_slack(f"[{full}] Created issue #{issue['number']}: {issue['title']}\n{issue['html_url']}")
    return issue


def close_issue(repo: str, issue_number: int) -> Dict[str, Any]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues/{int(issue_number)}"
    resp = requests.patch(url, headers=gh_headers(), json={"state": "closed"}, timeout=30)
    if resp.status_code >= 300:
        raise GitHubError(f"Close issue failed: {resp.status_code} {resp.text}")
    issue = resp.json()
    notify_slack(f"[{full}] Closed issue #{issue['number']}: {issue['title']}\n{issue['html_url']}")
    return issue


def list_issues(
    repo: str,
    state: str = "open",   # open | closed | all
    labels: Optional[List[str]] = None,
    creator: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    full = normalize_repo(repo)
    url = f"{GITHUB_API_URL}/repos/{full}/issues"
    params: Dict[str, Any] = {
        "state": state,
        "per_page": min(100, max(1, limit)),
    }
    if labels:
        params["labels"] = ",".join(labels)
    if creator:
        params["creator"] = creator
    if assignee:
        params["assignee"] = assignee

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
):
    """Create a new issue."""
    try:
        issue = create_issue(repo, title, body, labels, assignees)
        typer.echo(f" Created issue #{issue['number']}: {issue['html_url']}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("close")
def cmd_close(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    number: int = typer.Argument(..., help="Issue number to close"),
):
    """Close an existing issue by number."""
    try:
        issue = close_issue(repo, number)
        typer.echo(f" Closed issue #{issue['number']}: {issue['html_url']}")
    except GitHubError as e:
        typer.echo(f"X {e}")
        raise typer.Exit(1)


@app.command("list")
def cmd_list(
    repo: str = typer.Argument(..., help="owner/repo or just repo"),
    state: str = typer.Option("open", "--state", "-s", help="open|closed|all", case_sensitive=False),
    label: Optional[List[str]] = typer.Option(None, "--label", "-l", help="Filter by labels"),
    creator: Optional[str] = typer.Option(None, "--creator", help="Filter by creator"),
    assignee: Optional[str] = typer.Option(None, "--assignee", help="Filter by assignee"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max number to fetch (<= 100 recommended)"),
):
    """List issues with optional filtering."""
    s = state.lower()
    if s not in {"open", "closed", "all"}:
        typer.echo("❌ --state must be one of: open, closed, all")
        raise typer.Exit(2)
    try:
        issues = list_issues(repo, s, label, creator, assignee, limit)
        if not issues:
            typer.echo("No issues found.")
            raise typer.Exit(0)
        for it in issues:
            typer.echo(f"#{it['number']} [{it['state']}] {it['title']}  -> {it['html_url']}")
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
