import os
import httpx
import base64
import json
from datetime import datetime
from fastmcp import FastMCP

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_OWNER = os.environ["GITHUB_OWNER"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
API_KEY = os.environ.get("MCP_API_KEY", "")

BASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

mcp = FastMCP("Obsidian Memory MCP")

def gh_get(path: str):
    r = httpx.get(f"{BASE_URL}/contents/{path}", headers=HEADERS)
    return r.json()

def gh_put(path: str, content: str, message: str, sha: str = None):
    encoded = base64.b64encode(content.encode()).decode()
    payload = {"message": message, "content": encoded}
    if sha:
        payload["sha"] = sha
    r = httpx.put(f"{BASE_URL}/contents/{path}", headers=HEADERS, json=payload)
    return r.json()

def gh_delete(path: str, message: str, sha: str):
    r = httpx.delete(f"{BASE_URL}/contents/{path}", headers=HEADERS,
                     json={"message": message, "sha": sha})
    return r.json()

def sanitize_path(title: str, folder: str = "") -> str:
    fname = title.strip().replace(" ", "-").replace("/", "-") + ".md"
    return f"{folder.strip('/')}/{fname}".strip("/") if folder else fname

@mcp.tool()
def create_note(title: str, content: str, folder: str = "") -> str:
    """Create a new markdown note in the Obsidian vault. 
    Use folder to organise notes (e.g. 'meetings', 'ideas', 'tasks')."""
    path = sanitize_path(title, folder)
    front = f"---\ntitle: {title}\ncreated: {datetime.utcnow().isoformat()}Z\n---\n\n"
    result = gh_put(path, front + content, f"Create note: {title}")
    if "content" in result:
        return f"✅ Note created: {path}"
    return f"❌ Error: {result.get('message', str(result))}"

@mcp.tool()
def read_note(path: str) -> str:
    """Read a note from the vault by its file path (e.g. 'ideas/my-note.md')."""
    data = gh_get(path)
    if "content" in data:
        return base64.b64decode(data["content"]).decode()
    return f"❌ Not found: {data.get('message', str(data))}"

@mcp.tool()
def append_to_note(path: str, content: str) -> str:
    """Append content to an existing note. Great for logging, memory entries, and running notes."""
    data = gh_get(path)
    if "content" not in data:
        return f"❌ Not found: {data.get('message', str(data))}"
    existing = base64.b64decode(data["content"]).decode()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    updated = existing + f"\n\n---\n*{timestamp}*\n{content}"
    result = gh_put(path, updated, f"Append to: {path}", sha=data["sha"])
    if "content" in result:
        return f"✅ Appended to {path}"
    return f"❌ Error: {result.get('message', str(result))}"

@mcp.tool()
def update_note(path: str, content: str) -> str:
    """Fully replace the content of an existing note."""
    data = gh_get(path)
    if "content" not in data:
        return f"❌ Not found: {data.get('message', str(data))}"
    result = gh_put(path, content, f"Update: {path}", sha=data["sha"])
    if "content" in result:
        return f"✅ Updated {path}"
    return f"❌ Error: {result.get('message', str(result))}"

@mcp.tool()
def list_notes(folder: str = "") -> str:
    """List all notes in the vault or in a specific folder."""
    path = folder.strip("/") if folder else ""
    data = gh_get(path) if path else httpx.get(f"{BASE_URL}/contents", headers=HEADERS).json()
    if isinstance(data, list):
        files = [f["path"] for f in data if f["type"] == "file" and f["name"].endswith(".md")]
        dirs = [f["path"] + "/" for f in data if f["type"] == "dir"]
        return "📁 Folders: " + ", ".join(dirs) + "\n📝 Notes: " + ", ".join(files) if files or dirs else "Empty vault."
    return f"❌ Error: {data.get('message', str(data))}"

@mcp.tool()
def search_notes(query: str) -> str:
    """Search for notes in the vault by keyword using GitHub code search."""
    r = httpx.get(
        "https://api.github.com/search/code",
        headers=HEADERS,
        params={"q": f"{query} repo:{GITHUB_OWNER}/{GITHUB_REPO}", "per_page": 10}
    )
    data = r.json()
    items = data.get("items", [])
    if not items:
        return f"No notes found matching '{query}'."
    results = [f"- {item['path']}" for item in items]
    return f"Found {len(results)} note(s) matching '{query}':\n" + "\n".join(results)

@mcp.tool()
def delete_note(path: str) -> str:
    """Delete a note from the vault by its file path."""
    data = gh_get(path)
    if "content" not in data:
        return f"❌ Not found: {data.get('message', str(data))}"
    result = gh_delete(path, f"Delete: {path}", sha=data["sha"])
    if "commit" in result:
        return f"✅ Deleted {path}"
    return f"❌ Error: {result.get('message', str(result))}"

@mcp.tool()
def save_memory(content: str, category: str = "general") -> str:
    """Save something to Claude's persistent memory in Obsidian. 
    Use category to organise memories (e.g. 'preferences', 'context', 'tasks', 'people')."""
    path = f"memory/{category}.md"
    data = gh_get(path)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if "content" in data:
        existing = base64.b64decode(data["content"]).decode()
        updated = existing + f"\n\n---\n*{timestamp}*\n{content}"
        result = gh_put(path, updated, f"Memory update: {category}", sha=data["sha"])
    else:
        header = f"# Memory: {category}\n\n"
        result = gh_put(path, header + f"*{timestamp}*\n{content}", f"Memory init: {category}")
    if "content" in result:
        return f"✅ Memory saved to memory/{category}.md"
    return f"❌ Error: {result.get('message', str(result))}"

@mcp.tool()
def recall_memory(category: str = "") -> str:
    """Recall saved memories from the vault. Leave category blank to see all memory categories."""
    if not category:
        return list_notes("memory")
    return read_note(f"memory/{category}.md")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
