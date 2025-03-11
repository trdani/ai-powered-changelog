# Git Changelog Generator

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg) ![License](https://img.shields.io/badge/License-MIT-green.svg)

The **Git Changelog Generator** is a Python script that automates the creation of user-friendly changelogs from Git repositories. Whether you're summarizing updates from a local repo on your machine or a public GitHub repo, this tool fetches the latest commits and uses Anthropic's Claude AI to craft clear, engaging summaries tailored for non-technical users. It highlights major features and fixes—like new functionality or bug resolutions—while skipping minor code tweaks, making it perfect for sharing updates with end users or stakeholders.

## Features

- **Local and Remote Support:** Works with both local Git repositories and public GitHub repositories.
- **Non-Technical Focus:** Generates changelogs in plain English, emphasizing user-visible changes.
- **Smart Filtering:** Prioritizes big functional updates and key fixes, ignoring internal refactors or trivial changes.
- **Flexible Options:** Specify the number of commits to summarize and (for remote repos) the branch to analyze.
- **AI-Driven:** Powered by Anthropic’s Claude model for natural, intuitive summaries.

## How It Works

The script grabs the last `n` commits from your chosen repository, collecting details like commit messages, file changes, and diffs. It then sends this data to Claude, which generates a Markdown-formatted changelog sorted in reverse chronological order (newest first). For example:
- 2025-03-05 - Added a search bar so you can find your files faster!
- 2025-03-02 - Fixed a glitch that made the app crash when saving your work — no more lost progress.

## Getting Started

### Prerequisites

- **Python 3.11+:** Check with `python --version`.
- **Git:** Required for local repos; verify with `git --version`.
- **Anthropic API Key:** Sign up at `console.anthropic.com` to get one (trial credits may be available).
- **Dependencies:** Install required packages:
  ```bash
  pip install -r requirements.txt

### Setting Up Environment Variables
For security, the script expects the Anthropic API key to be stored in an environment variable named CLAUDE_API_KEY. Set it up as follows:

On Linux/MacOS:
`export CLAUDE_API_KEY='your-api-key-here'`
Add the above line to your ~/.bashrc, ~/.zshrc, or equivalent shell configuration file to make it persistent.

On Windows (Command Prompt):
`setx CLAUDE_API_KEY "your-api-key-here"`
Note: You may need to restart your terminal or computer for the change to take effect.
Alternatively, you can set the environment variable directly in your script execution environment, but avoid hardcoding sensitive data in the script itself.

## Usage
Run the script from the command line using python3 print_changelog.py. The script accepts several command-line arguments to customize its behavior.

### Command-Line Arguments
Argument	Description	Required	Default
--local	Specify if the repository is local (1) or remote (0).	Yes	N/A
--gitrepo	Path to the local Git repository or URL to the remote GitHub repository.	Yes	N/A
--num_commits	Number of commits to analyze (must be a positive integer).	Yes	N/A
--branch	Branch to analyze for remote repositories.	No	main

### Example Use Cases
Here are some examples of how to use the script:

1. Generate a Changelog for a Local Repository
Analyze the last 5 commits in a local Git repository located at ~/Projects/my-repo:

`python script_name.py --local 1 --gitrepo ~/Projects/my-repo --num_commits 5`

2. Generate a Changelog for a Remote GitHub Repository
Analyze the last 3 commits on the main branch of a remote GitHub repository:

`python script_name.py --local 0 --gitrepo https://github.com/owner/repo --num_commits 3`

3. Analyze a Specific Branch in a Remote Repository
Analyze the last 10 commits on the dev branch of a remote GitHub repository:

`python script_name.py --local 0 --gitrepo https://github.com/owner/repo --num_commits 10 --branch dev`


The script will output a Markdown-formatted changelog summarizing the commits in a user-friendly way, focusing on changes that matter to end-users.

## Troubleshooting
### Error: "Claude API key not set"
Ensure you've set the CLAUDE_API_KEY environment variable correctly. Check its value by running echo $CLAUDE_API_KEY (Linux/MacOS) or echo %CLAUDE_API_KEY% (Windows Command Prompt).

### Error: "Invalid GitHub URL"
Ensure the remote repository URL follows the format https://github.com/owner/repo. Remove any trailing slashes or .git suffixes if present.

### Error: "No commits found"
Verify that the repository (local or remote) contains commits and that you're targeting the correct branch for remote repositories.

### Connection Issues with APIs
Check your internet connection and ensure the GitHub and Anthropic APIs are accessible. You may need to retry after a delay if rate limits are encountered.

For additional help, feel free to open an issue on this repository.