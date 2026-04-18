# Obsidian Memory MCP

A URL-based MCP server that gives Claude persistent memory via your Obsidian vault on GitHub.

## Tools
- `create_note` — create a new note
- `read_note` — read a note by path
- `append_to_note` — append content to existing note
- `update_note` — replace note content
- `list_notes` — browse vault
- `search_notes` — search by keyword
- `delete_note` — remove a note
- `save_memory` — save Claude memory by category
- `recall_memory` — recall saved memories

## Environment Variables
- `GITHUB_TOKEN` — GitHub personal access token (repo scope)
- `GITHUB_OWNER` — GitHub username
- `GITHUB_REPO` — vault repo name (e.g. claude-obsidian-vault)
- `MCP_API_KEY` — optional API key for securing the server
