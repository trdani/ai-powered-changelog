import argparse
import requests
import git
import os
from typing import Tuple, List, Dict, Any
import sys
from anthropic import Anthropic

# Move sensitive data to environment variables for security
ANTHROPIC_API_KEY = os.getenv(
    "CLAUDE_API_KEY", "your-default-api-key-here"
)  # Replace with actual default or raise error


def parse_github_link(url: str) -> Tuple[str, str]:
    """
    Parse a GitHub URL into owner and repository name.

    Args:
        url (str): GitHub URL (e.g., 'https://github.com/owner/repo').

    Returns:
        tuple: (owner, repo) as strings.

    Raises:
        ValueError: If the URL is invalid or malformed.
    """
    if not isinstance(url, str):
        raise ValueError("URL must be a string")

    # Remove leading/trailing whitespace and normalize the URL
    url = url.strip()

    # Remove '.git' suffix only if it exists at the end
    if url.endswith(".git"):
        url = url[:-4]  # Remove the last 4 characters ('.git')
    # Remove trailing slashes
    url = url.rstrip("/")

    # Split the URL by '/' and validate
    parts = url.split("/")
    if len(parts) < 2 or "github.com" not in parts:
        raise ValueError(
            "Invalid GitHub URL. Please use the format 'https://github.com/owner/repo'"
        )

    # Extract owner and repo from the end of the URL
    repo = parts[-1]
    owner = parts[-2]

    # Additional validation to ensure owner and repo are not empty
    if not owner or not repo:
        raise ValueError("Owner or repository name cannot be empty")

    return owner, repo


def get_last_n_commits_local(repo_path: str, n: int) -> List[Dict[str, Any]]:
    """
    Get the last n commits from a local git repo.

    Args:
        repo_path (str): Filepath for the git repo.
        n (int): Number of commits to get.

    Returns:
        list: List of dictionaries containing commit details.

    Raises:
        ValueError: If the repo path is invalid or not a git repository.
    """
    if not isinstance(repo_path, str):
        raise ValueError("Local repo path must be a string")
    if not os.path.exists(repo_path):
        raise ValueError(f"Local repo path '{repo_path}' does not exist")

    try:
        repo = git.Repo(repo_path)
        commits = list(repo.iter_commits(max_count=n))

        if not commits:
            raise ValueError(f"No commits found in repository at '{repo_path}'")

        # Convert commits into a list of dictionaries
        commit_list = []
        for commit in commits:
            # Process raw file changes
            file_diffs = []
            for diff in commit.diff():
                file_diffs.append(
                    {
                        "file_a": diff.a_path,  # Path in the parent (before change)
                        "file_b": diff.b_path,  # Path in the commit (after change)
                        "change_type": diff.change_type,  # 'A' (added), 'D' (deleted), 'M' (modified), etc.
                        "diff_text": (
                            diff.diff.decode("utf-8") if diff.diff else ""
                        ),  # Raw diff text
                    }
                )

            # Process metadata and save file changes
            commit_list.append(
                {
                    "hash": commit.hexsha,
                    "author": commit.author.name,
                    "date": commit.authored_datetime.isoformat(),
                    "file_changes": commit.stats.total,  # Use .total for a dict of stats
                    "file_diffs": file_diffs,
                    "message": commit.message.strip(),
                }
            )

        return commit_list
    except git.exc.InvalidGitRepositoryError:
        raise ValueError(f"'{repo_path}' is not a valid git repository")
    except Exception as e:
        raise ValueError(f"Error processing local repository: {e}")


def extract_remote_diff_data(
    commit_url: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Get the latest data for a specific remote commit.

    Args:
        commit_url (str): The URL of the commit as would be accessed on github.com.

    Returns:
        tuple: (file_changes, file_diffs) where each is a list of dictionaries.

    Raises:
        ValueError: If the API request fails or returns invalid data.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        commit_response = requests.get(commit_url, headers=headers, timeout=10)
        commit_response.raise_for_status()
        commit_details = commit_response.json()

        # Extract file changes and diffs
        file_changes = []
        file_diffs = []
        total_insertions = 0
        total_deletions = 0
        for file in commit_details.get("files", []):
            file_path = file["filename"]
            # Parse stats from the file change
            insertions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            total_insertions += insertions
            total_deletions += deletions

            file_changes.append(
                {
                    "file": file_path,
                    "insertions": insertions,
                    "deletions": deletions,
                    "lines_changed": insertions + deletions,
                }
            )

            # Extract diff if available
            if "patch" in file:
                file_diffs.append(
                    {
                        "file_a": file.get("previous_filename", file_path),
                        "file_b": file_path,
                        "change_type": file["status"][0].upper(),  # 'A', 'D', 'M', etc.
                        "diff_text": file["patch"],
                    }
                )

        return file_changes, file_diffs
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error accessing GitHub API for commit '{commit_url}': {e}")
    except Exception as e:
        raise ValueError(f"Error processing commit data: {e}")


def get_last_n_commits_remote(
    owner: str, repo: str, n: int, branch: str = "main"
) -> List[Dict[str, Any]]:
    """
    Get the last n commits from a GitHub repository using the GitHub API.

    Args:
        owner (str): GitHub username.
        repo (str): Repo name.
        n (int): Number of commits to get.
        branch (str): Branch name (default = 'main').

    Returns:
        list: List of dictionaries containing commit details.

    Raises:
        ValueError: If the API request fails or no commits are found.
    """
    # GitHub API endpoint for commits, with pagination support
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {
        "sha": branch,
        "per_page": min(n, 100),
    }  # GitHub API limits to 100 per page

    try:
        # Make the API request
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        response.raise_for_status()
        commits_json = response.json()

        if not commits_json:
            raise ValueError(
                f"No commits found in repository '{owner}/{repo}' on branch '{branch}'"
            )

        # Limit to n commits
        commits_json = commits_json[:n]
        commit_list = []
        for commit_data in commits_json:
            sha = commit_data["sha"]

            # Fetch detailed commit info (including diffs)
            commit_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
            file_changes, file_diffs = extract_remote_diff_data(commit_url)

            commit_list.append(
                {
                    "hash": commit_data["sha"],
                    "author": commit_data["commit"]["author"]["name"],
                    "date": commit_data["commit"]["author"]["date"],
                    "file_changes": file_changes,
                    "file_diffs": file_diffs,
                    "message": commit_data["commit"]["message"].strip(),
                }
            )

        return commit_list

    except requests.exceptions.RequestException as e:
        raise ValueError(
            f"Error accessing GitHub API for repository '{owner}/{repo}': {e}"
        )
    except Exception as e:
        raise ValueError(f"Error processing remote repository: {e}")


def main():
    """
    Main function to run the CLI, handle arguments, and produce the changelog.
    """
    parser = argparse.ArgumentParser(
        description="Summarize the last n commits of your local or remote public git repo!"
    )
    parser.add_argument(
        "--local",
        type=int,
        choices=[0, 1],  # Restrict to valid values
        required=True,
        help="Specify if the gitrepo is a local filesystem path. 1 if yes, 0 if no (i.e., a remote repo link).",
    )
    parser.add_argument(
        "--gitrepo",
        type=str,
        required=True,
        help="If local, path to a git repository (e.g., '~/Documents/Projects/example-git-repo'). If remote, link to the git repo home (e.g., 'https://github.com/owner/repo').",
    )
    parser.add_argument(
        "--num_commits",
        type=int,
        required=True,
        help="Number of commits to summarize (must be a positive integer).",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="main",
        help="Branch to summarize for remote repos (default: 'main').",
    )

    args = parser.parse_args()

    # Validate num_commits
    if args.num_commits <= 0:
        print("Error: Number of commits must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    # Validate API key
    if ANTHROPIC_API_KEY == "your-default-api-key-here":
        print(
            "Error: Claude API key not set. Please set the 'CLAUDE_API_KEY' environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Get the last n commits
        gitlog = []
        if args.local == 1:
            repo_filepath = os.path.expanduser(
                args.gitrepo
            )  # Handle ~ for user home directory
            gitlog = get_last_n_commits_local(repo_filepath, args.num_commits)
        else:
            owner, repo_name = parse_github_link(args.gitrepo)
            gitlog = get_last_n_commits_remote(
                owner, repo_name, args.num_commits, branch=args.branch
            )

        # Initialize the Anthropic client
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Put together prompt
        messages = [
            {
                "role": "user",
                "content": """
        You are the friendly owner of a software project, tasked with creating a changelog for non-technical users who rely on your software every day. Your goal is to explain recent updates in a way that’s clear, engaging, and meaningful to them—think of them as people who care about what the software *does* for them, not how it’s built. Based on the git log provided, generate a changelog that highlights major functional changes (like new features or improvements they’ll notice) and important fixes (like bugs that affected their experience), while skipping minor tweaks, code refactors, or technical details that don’t impact their daily use.

        You’ll receive the git log as a JSON string with this schema:
        [
            {
                'hash': (hash value of commit),
                'author': (who authored it),
                'date': (date of change),
                'file_changes': (files changed, insertions/deletions, etc.),
                'file_diffs': (raw text of the changes from parent commit),
                'message': (the commit message)
            },
            ... more changelogs
        ]

        Here’s what to do:
        - Analyze the commit messages, file changes, and diffs to identify updates that matter to users.
        - Focus on big wins: new features, usability improvements, or fixes to obvious problems.
        - Ignore small stuff: code cleanups, internal refactors, or changes with no clear user impact (e.g., typo fixes in code comments).
        - If a commit’s purpose isn’t obvious or doesn’t affect users, skip it or summarize it as “Behind-the-scenes improvements” without details.
        - Write summaries in plain, friendly English—avoid jargon like “refactored” or “optimized.”
        - Sort entries in reverse chronological order (newest first).
        - Format the output as a Markdown list, with each entry starting with the date in 'YYYY-MM-DD' format, followed by a short, upbeat summary. Keep each summary 1-2 sentences, max.

        Examples of good summaries:
        - 2025-03-05 - Added a search bar so you can find your files faster!
        - 2025-03-02 - Fixed a glitch that made the app crash when saving your work—no more lost progress.

        Provide the changelog as a standalone Markdown list, nothing else—no extra explanations or metadata like hashes or authors.
        """,
            },
            {"role": "user", "content": f"{gitlog}"},
        ]

        # Make the API call using the Anthropic SDK
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4096,
            temperature=0.3,
            messages=messages,
        )

        # Extract the summary from the response
        summary = response.content[
            0
        ].text  # Anthropic API returns content as a list of blocks
        print(summary)
        print("success until the API call!")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
