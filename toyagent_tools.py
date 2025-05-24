import os
import sys
import json
import subprocess
import platform
import pathlib
import shutil
from typing import Dict, Any, Optional, List, TypedDict
import requests
import uuid
import datetime

# --- Memory Node System ---
class MemoryNode(TypedDict):
    node_id: str
    tags: List[str]
    content: str
    source_chat: Optional[str]
    created_at: str
    updated_at: str

MEMORY_NODES: Dict[str, MemoryNode] = {}
MEMORY_FILE_PATH: Optional[str] = None

def _get_utc_iso_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def init_memory_system(filepath: str):
    global MEMORY_FILE_PATH
    MEMORY_FILE_PATH = filepath
    load_memory_from_file()

def load_memory_from_file():
    global MEMORY_NODES
    if MEMORY_FILE_PATH and os.path.exists(MEMORY_FILE_PATH):
        try:
            with open(MEMORY_FILE_PATH, 'r', encoding='utf-8') as f:
                loaded_nodes = json.load(f)
                if isinstance(loaded_nodes, dict):
                    MEMORY_NODES = loaded_nodes
                    print(f"INFO: Loaded {len(MEMORY_NODES)} memory nodes from {MEMORY_FILE_PATH}", file=sys.stderr)
                else:
                    print(f"ERROR: Memory file {MEMORY_FILE_PATH} does not contain a valid JSON object for nodes. Initializing fresh memory.", file=sys.stderr)
                    MEMORY_NODES = {}
        except json.JSONDecodeError:
            print(f"ERROR: Invalid JSON in memory file {MEMORY_FILE_PATH}. Initializing fresh memory.", file=sys.stderr)
            MEMORY_NODES = {} # Start fresh if loading fails or format is wrong
        except Exception as e:
            print(f"ERROR: Failed to load memory from {MEMORY_FILE_PATH}: {e}. Initializing fresh memory.", file=sys.stderr)
            MEMORY_NODES = {}
    else:
        MEMORY_NODES = {} # Initialize if file doesn't exist or path not set

def save_memory_to_file():
    if MEMORY_FILE_PATH:
        try:
            # Ensure parent directory exists
            path_obj = pathlib.Path(MEMORY_FILE_PATH)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(MEMORY_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(MEMORY_NODES, f, indent=2)
            # print(f"INFO: Memory saved to {MEMORY_FILE_PATH}", file=sys.stderr) # Can be too verbose
        except Exception as e:
            print(f"ERROR: Failed to save memory to {MEMORY_FILE_PATH}: {e}", file=sys.stderr)

def _generate_node_id() -> str:
    return str(uuid.uuid4())

# --- Tool Definitions (JSON Schema for OpenAI API) ---
EXECUTE_PYTHON_CODE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "execute_python_code",
        "description": ("Executes a given snippet of Python code in a separate process and returns its stdout and stderr. "
            "WARNING: This is highly dangerous and executes with the script's permissions. Requires careful user approval."),
        "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "description": "The Python code snippet to execute.",},
                "timeout_seconds": {"type": "integer", "description": "Optional timeout in seconds for the execution.","default": 30,},},
            "required": ["code"]}}}
EXECUTE_SHELL_COMMAND_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "execute_shell_command",
        "description": "Execute a shell command and return its stdout, stderr, and exit code. Use OS-specific commands (cmd.exe on Windows, sh/bash on Linux/macOS). Requires user approval.",
        "parameters": { "type": "object", "properties": {
                "command": {"type": "string", "description": "The shell command string to execute."},
                "working_directory": {"type": "string", "description": "Optional directory path to execute the command in.", "nullable": True},
                "timeout_seconds": {"type": "integer", "description": "Optional timeout in seconds.", "default": 60}},
            "required": ["command"]}}}
READ_FILE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "read_file",
        "description": "Reads the entire content of a specified file.",
        "parameters": { "type": "object", "properties": {
                "path": {"type": "string", "description": "The relative or absolute path to the file to read."}},
            "required": ["path"]}}}
WRITE_FILE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "write_file",
        "description": "Writes content to a specified file. Creates directories if needed. Requires user approval.",
        "parameters": { "type": "object", "properties": {
                "path": {"type": "string", "description": "The relative or absolute path to the file to write."},
                "content": {"type": "string", "description": "The content to write to the file."},
                "overwrite": {"type": "boolean", "description": "Whether to overwrite the file if it exists.", "default": False}},
            "required": ["path", "content"]}}}
COPY_FILE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "copy_file",
        "description": "Copies a source file to a destination path. Creates destination directories if needed. Requires user approval.",
        "parameters": { "type": "object", "properties": {
                "source_path": {"type": "string", "description": "The relative or absolute path of the file to copy."},
                "destination_path": {"type": "string", "description": "The relative or absolute path where the file should be copied."},
                "overwrite": {"type": "boolean", "description": "Whether to overwrite the destination file if it already exists.", "default": False}},
            "required": ["source_path", "destination_path"]}}}
LIST_DIRECTORY_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "list_directory",
        "description": "Lists the files and subdirectories within a specified directory.",
        "parameters": { "type": "object", "properties": {
                "path": {"type": "string", "description": "The relative or absolute path to the directory.", "default": "."},
                "recursive": {"type": "boolean", "description": "Whether to list contents recursively (use with caution).", "default": False}},
            "required": []}}}
CREATE_DIRECTORY_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "create_directory",
        "description": "Creates a new directory, including any necessary parent directories. Requires user approval.",
        "parameters": { "type": "object", "properties": {
                "path": {"type": "string", "description": "The relative or absolute directory path to create."}},
            "required": ["path"]}}}
FETCH_WEB_PAGE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "fetch_web_page",
        "description": "Fetches the text content of a given URL. Requires user approval.",
        "parameters": { "type": "object", "properties": {
                "url": {"type": "string", "description": "The URL to fetch (must include http:// or https://)."},
                "timeout_seconds": {"type": "integer", "description": "Optional timeout in seconds.", "default": 10}},
            "required": ["url"]}}}
ASK_USER_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "ask_user",
        "description": "Asks the human user a question and returns their response.",
        "parameters": { "type": "object", "properties": {
                "question": {"type": "string", "description": "The question to ask the user."}},
            "required": ["question"]}}}

# --- Memory Tool Schemas ---
CREATE_MEMORY_NODE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "create_memory_node",
        "description": "Creates a new memory node. Nodes are used to store pieces of information with associated tags for later retrieval.",
        "parameters": {"type": "object", "properties": {
            "tags": {"type": "array", "items": {"type": "string"}, "description": "A list of tags to associate with the node (e.g., ['project:alpha', 'user_id:123', 'todo'])."},
            "content": {"type": "string", "description": "The textual content of the memory node."},
            "source_chat": {"type": "string", "description": "Optional: A reference to the source of this information (e.g., a chat ID, date, or session identifier).", "nullable": True}
        }, "required": ["tags", "content"]}}}

RETRIEVE_MEMORY_NODES_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "retrieve_memory_nodes",
        "description": "Retrieves memory nodes that match ALL provided tags. Optionally, can filter by a query string within the node content. Returns full node objects.",
        "parameters": {"type": "object", "properties": {
            "match_all_tags": {"type": "array", "items": {"type": "string"}, "description": "A list of tags. Nodes must have ALL of these tags to be returned."},
            "query_in_content": {"type": "string", "description": "Optional: A string to search for within the content of the nodes (case-insensitive).", "nullable": True},
            "limit": {"type": "integer", "description": "Maximum number of nodes to return.", "default": 10}
        }, "required": ["match_all_tags"]}}}

UPDATE_MEMORY_NODE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "update_memory_node",
        "description": "Updates an existing memory node by its ID. Allows modification of content and tags.",
        "parameters": {"type": "object", "properties": {
            "node_id": {"type": "string", "description": "The ID of the memory node to update."},
            "new_content": {"type": "string", "description": "Optional: New content for the node. If null, content is not changed.", "nullable": True},
            "add_tags": {"type": "array", "items": {"type": "string"}, "description": "Optional: A list of tags to add to the node. Duplicates are ignored.", "nullable": True},
            "remove_tags": {"type": "array", "items": {"type": "string"}, "description": "Optional: A list of tags to remove from the node.", "nullable": True}
        }, "required": ["node_id"]}}}

DELETE_MEMORY_NODE_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "delete_memory_node",
        "description": "Deletes a memory node by its ID.",
        "parameters": {"type": "object", "properties": {
            "node_id": {"type": "string", "description": "The ID of the memory node to delete."}
        }, "required": ["node_id"]}}}

LIST_MEMORY_NODES_TOOL_SCHEMA = {
    "type": "function", "function": {
        "name": "list_memory_nodes",
        "description": "Lists memory nodes, optionally filtered by tags. Nodes are returned sorted by last updated time (descending).",
        "parameters": {"type": "object", "properties": {
            "filter_match_all_tags": {"type": "array", "items": {"type": "string"}, "description": "Optional: If provided, only nodes having ALL these tags will be listed.", "nullable": True},
            "limit": {"type": "integer", "description": "Maximum number of nodes to return.", "default": 20},
            "offset": {"type": "integer", "description": "Number of nodes to skip for pagination.", "default": 0}
        }, "required": []}}}


TOOLS_LIST = [
    EXECUTE_PYTHON_CODE_TOOL_SCHEMA, EXECUTE_SHELL_COMMAND_TOOL_SCHEMA, READ_FILE_TOOL_SCHEMA, WRITE_FILE_TOOL_SCHEMA, COPY_FILE_TOOL_SCHEMA,
    LIST_DIRECTORY_TOOL_SCHEMA, CREATE_DIRECTORY_TOOL_SCHEMA, FETCH_WEB_PAGE_TOOL_SCHEMA, ASK_USER_TOOL_SCHEMA,
    CREATE_MEMORY_NODE_TOOL_SCHEMA, RETRIEVE_MEMORY_NODES_TOOL_SCHEMA, UPDATE_MEMORY_NODE_TOOL_SCHEMA,
    DELETE_MEMORY_NODE_TOOL_SCHEMA, LIST_MEMORY_NODES_TOOL_SCHEMA,
]

# --- Tool Implementation Functions ---
def execute_shell_command(command: str, working_directory: Optional[str] = None, timeout_seconds: int = 60) -> Dict[str, Any]:
    """Executes a shell command."""
    result = {"stdout": "", "stderr": "", "exit_code": None, "error": None}
    effective_cwd = working_directory or os.getcwd()
    print(f"  (Executing in: {effective_cwd})") # Context for user
    if not pathlib.Path(effective_cwd).is_dir():
        result["error"] = f"Working directory not found: {effective_cwd}"
        result["exit_code"] = -2 # Consistent error code
        return result
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            encoding='utf-8', errors='replace', cwd=effective_cwd,
            timeout=timeout_seconds, check=False, 
        )
        result.update({"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "exit_code": proc.returncode})
    except subprocess.TimeoutExpired:
        result.update({"error": f"Timeout ({timeout_seconds}s)", "exit_code": -1})
    except FileNotFoundError: 
        cmd_name = command.split()[0] if command else '<empty command>'
        result.update({"error": f"Command or executable not found: '{cmd_name}'", "exit_code": -2}) 
    except Exception as e:
        result.update({"error": f"Execution failed: {e}", "exit_code": -3})
        if not result["stderr"]: result["stderr"] = str(e) 
    return result

def read_file(path: str) -> Dict[str, Any]:
    """Reads the content of a file."""
    try:
        p = pathlib.Path(path)
        if not p.is_file(): raise FileNotFoundError(f"Not a file: {path}")
        content = p.read_text(encoding='utf-8', errors='replace')
        return {"content": content, "error": None}
    except (FileNotFoundError, PermissionError, IsADirectoryError, UnicodeDecodeError, OSError) as e: 
        return {"content": None, "error": f"Read failed: {e}"}
    except Exception as e:
        return {"content": None, "error": f"Unexpected read error: {e}"}

def write_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """Writes content to a file."""
    try:
        p = pathlib.Path(path)
        if p.exists() and p.is_dir(): raise IsADirectoryError(f"Path is a directory: {path}")
        if p.exists() and not overwrite: raise FileExistsError(f"File exists, overwrite=False: {path}")
        p.parent.mkdir(parents=True, exist_ok=True) 
        p.write_text(content, encoding='utf-8')
        return {"success": True, "error": None}
    except (FileExistsError, IsADirectoryError, PermissionError, OSError) as e:
        return {"success": False, "error": f"Write failed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected write error: {e}"}

def copy_file(source_path: str, destination_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Copies a file from source to destination."""
    try:
        src = pathlib.Path(source_path)
        dest = pathlib.Path(destination_path)

        if not src.is_file(): raise FileNotFoundError(f"Source not found or not a file: {source_path}")
        if dest.exists():
            if dest.is_dir(): raise IsADirectoryError(f"Destination is a directory: {destination_path}")
            if not overwrite: raise FileExistsError(f"Destination exists, overwrite=False: {destination_path}")
            if not dest.is_file(): raise ValueError(f"Cannot overwrite non-file destination: {destination_path}")
        dest.parent.mkdir(parents=True, exist_ok=True) 
        shutil.copy2(src, dest) 
        return {"success": True, "error": None}
    except (FileNotFoundError, FileExistsError, IsADirectoryError, PermissionError, shutil.Error, ValueError, OSError) as e:
        return {"success": False, "error": f"Copy failed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected copy error: {e}"}

def list_directory(path: str = ".", recursive: bool = False) -> Dict[str, Any]:
    """Lists directory contents."""
    try:
        p = pathlib.Path(path)
        if not p.is_dir(): raise FileNotFoundError(f"Not a directory: {path}")
        entries = []
        if recursive:
            for item in sorted(p.rglob('*')): 
                rel_path = item.relative_to(p)
                entry_str = f"{rel_path}{os.sep}" if item.is_dir() else str(rel_path)
                entries.append(entry_str)
        else:
             for item in sorted(p.iterdir()):
                  entries.append(f"{item.name}{os.sep}" if item.is_dir() else item.name)
        return {"entries": entries, "error": None}
    except (FileNotFoundError, PermissionError, OSError) as e:
        return {"entries": None, "error": f"List failed: {e}"}
    except Exception as e:
        return {"entries": None, "error": f"Unexpected list error: {e}"}

def create_directory(path: str) -> Dict[str, Any]:
    """Creates a directory."""
    try:
        p = pathlib.Path(path)
        if p.exists() and not p.is_dir():
            raise FileExistsError(f"Path exists but is a file: {path}")
        p.mkdir(parents=True, exist_ok=True) 
        if not p.is_dir(): raise OSError(f"Failed to create or confirm directory: {path}")
        return {"success": True, "error": None}
    except (FileExistsError, PermissionError, OSError) as e:
        return {"success": False, "error": f"Create dir failed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected create dir error: {e}"}

def fetch_web_page(url: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """Fetches the text content of a web page."""
    if requests is None: return {"content": None, "status_code": None, "error": "'requests' library not installed."}
    if not url.startswith(('http://', 'https://')): return {"content": None, "status_code": None, "error": "URL must start with http:// or https://"}
    result = {"content": None, "status_code": None, "error": None}
    try:
        response = requests.get(url, timeout=timeout_seconds, headers={'User-Agent': 'PythonAgent/1.0'})
        result["status_code"] = response.status_code
        response.raise_for_status() 
        response.encoding = response.apparent_encoding or 'utf-8'
        result["content"] = response.text
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout ({timeout_seconds}s)"
    except requests.exceptions.RequestException as e:
        status_info = f" (Status: {e.response.status_code})" if hasattr(e, 'response') and e.response is not None else ""
        result["error"] = f"Fetch failed: {e}{status_info}"
        if hasattr(e, 'response') and e.response is not None: result["status_code"] = e.response.status_code 
    except Exception as e:
         result["error"] = f"Unexpected fetch error: {e}"
    return result

def ask_user(question: str) -> Dict[str, Any]:
    """Asks the user a question. Handles basic input."""
    try:
        response = input(f"{question}\nYour response: ")
        return {"response": response, "error": None}
    except (KeyboardInterrupt, EOFError):
        return {"response": None, "error": "User interrupted or input closed."}
    except Exception as e:
        return {"response": None, "error": f"Input error: {e}"}

def execute_python_code(code: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Executes a Python code snippet in a subprocess."""
    result = {"stdout": None, "stderr": None, "error": None}
    if not code:
        result["error"] = "No code provided to execute."
        return result

    try:
        proc = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout_seconds,
            check=False,
        )
        result["stdout"] = proc.stdout.strip()
        result["stderr"] = proc.stderr.strip()
        if proc.returncode != 0 and not result["stderr"]:
             result["stderr"] = f"Python process exited with non-zero code: {proc.returncode}"
    except subprocess.TimeoutExpired:
        result["error"] = f"Python code execution timed out after {timeout_seconds} seconds."
    except FileNotFoundError:
         result["error"] = f"Python executable not found: {sys.executable}" 
    except Exception as e:
        result["error"] = f"Failed to execute Python code: {e}"
        if not result["stderr"]: result["stderr"] = str(e) 

    return result

# --- Memory Tool Implementations ---
def create_memory_node(tags: List[str], content: str, source_chat: Optional[str] = None) -> Dict[str, Any]:
    if not MEMORY_FILE_PATH: return {"error": "Memory system not initialized. Provide --memory-file."}
    try:
        node_id = _generate_node_id()
        timestamp = _get_utc_iso_timestamp()
        unique_tags = sorted(list(set(tags))) # Ensure unique tags and consistent order
        
        node: MemoryNode = {
            "node_id": node_id,
            "tags": unique_tags,
            "content": content,
            "source_chat": source_chat,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        MEMORY_NODES[node_id] = node
        save_memory_to_file()
        return {"node_id": node_id, "status": "created", "node": node}
    except Exception as e:
        return {"error": f"Failed to create memory node: {e}"}

def retrieve_memory_nodes(match_all_tags: List[str], query_in_content: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    if not MEMORY_FILE_PATH: return {"error": "Memory system not initialized."}
    try:
        if not match_all_tags: # Must have at least one tag to search effectively
             return {"error": "The 'match_all_tags' parameter cannot be empty for retrieval."}

        results: List[MemoryNode] = []
        required_tags_set = set(match_all_tags)

        # Iterate through a copy of values in case of concurrent modification (less likely here)
        # Sort by updated_at descending to process more recent nodes first if limit is hit early
        sorted_nodes = sorted(MEMORY_NODES.values(), key=lambda n: n["updated_at"], reverse=True)

        for node in sorted_nodes:
            if required_tags_set.issubset(set(node["tags"])):
                if query_in_content:
                    if query_in_content.lower() not in node["content"].lower():
                        continue # Skip if query doesn't match
                results.append(node)
                if len(results) >= limit:
                    break
        return {"nodes": results, "count": len(results)}
    except Exception as e:
        return {"error": f"Failed to retrieve memory nodes: {e}", "nodes": []}

def update_memory_node(node_id: str, new_content: Optional[str] = None, add_tags: Optional[List[str]] = None, remove_tags: Optional[List[str]] = None) -> Dict[str, Any]:
    if not MEMORY_FILE_PATH: return {"error": "Memory system not initialized."}
    try:
        if node_id not in MEMORY_NODES:
            return {"error": f"Node with ID '{node_id}' not found."}

        node = MEMORY_NODES[node_id]
        updated_fields = []

        if new_content is not None:
            node["content"] = new_content
            updated_fields.append("content")

        current_tags_set = set(node["tags"])
        if add_tags:
            for tag in add_tags:
                if tag not in current_tags_set:
                    current_tags_set.add(tag)
                    if "tags" not in updated_fields: updated_fields.append("tags")
        
        if remove_tags:
            for tag in remove_tags:
                if tag in current_tags_set:
                    current_tags_set.remove(tag)
                    if "tags" not in updated_fields: updated_fields.append("tags")
        
        node["tags"] = sorted(list(current_tags_set)) # Update with unique, sorted tags
        
        if updated_fields: # Only update timestamp if something changed
            node["updated_at"] = _get_utc_iso_timestamp()
            save_memory_to_file()
            return {"node_id": node_id, "status": "updated", "updated_fields": updated_fields, "node": node}
        else:
            return {"node_id": node_id, "status": "no_changes_made", "node": node}
            
    except Exception as e:
        return {"error": f"Failed to update memory node '{node_id}': {e}"}

def delete_memory_node(node_id: str) -> Dict[str, Any]:
    if not MEMORY_FILE_PATH: return {"error": "Memory system not initialized."}
    try:
        if node_id in MEMORY_NODES:
            deleted_node_preview = {"node_id": node_id, "tags": MEMORY_NODES[node_id]["tags"][:3], "content_preview": MEMORY_NODES[node_id]["content"][:50]+"..."}
            del MEMORY_NODES[node_id]
            save_memory_to_file()
            return {"node_id": node_id, "status": "deleted", "details": deleted_node_preview}
        else:
            return {"error": f"Node with ID '{node_id}' not found."}
    except Exception as e:
        return {"error": f"Failed to delete memory node '{node_id}': {e}"}

def list_memory_nodes(filter_match_all_tags: Optional[List[str]] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    if not MEMORY_FILE_PATH: return {"error": "Memory system not initialized."}
    try:
        # Get all nodes, sorted by updated_at descending
        all_nodes_sorted = sorted(MEMORY_NODES.values(), key=lambda n: n["updated_at"], reverse=True)
        
        filtered_nodes: List[MemoryNode] = []
        if filter_match_all_tags:
            required_tags_set = set(filter_match_all_tags)
            for node in all_nodes_sorted:
                if required_tags_set.issubset(set(node["tags"])):
                    filtered_nodes.append(node)
        else:
            filtered_nodes = all_nodes_sorted

        total_matching = len(filtered_nodes)
        paginated_nodes = filtered_nodes[offset : offset + limit]
        
        return {
            "nodes": paginated_nodes,
            "total_matching": total_matching,
            "count_returned": len(paginated_nodes),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        return {"error": f"Failed to list memory nodes: {e}", "nodes": []}


TOOL_EXECUTORS = {
    "execute_shell_command": execute_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "copy_file": copy_file,
    "list_directory": list_directory,
    "create_directory": create_directory,
    "fetch_web_page": fetch_web_page,
    "ask_user": ask_user,
    "execute_python_code": execute_python_code,
    # Memory tools
    "create_memory_node": create_memory_node,
    "retrieve_memory_nodes": retrieve_memory_nodes,
    "update_memory_node": update_memory_node,
    "delete_memory_node": delete_memory_node,
    "list_memory_nodes": list_memory_nodes,
}

# --- Dangerous Tool Info ---
class DangerousToolInfo(TypedDict):
    desc: str
    detail_arg: str

DANGEROUS_TOOL_INFO: Dict[str, DangerousToolInfo] = {
    "execute_shell_command":          {"desc": "Execute Shell Command", "detail_arg": "command"},
    "write_file":          {"desc": "Write to File",         "detail_arg": "path"},
    "copy_file":           {"desc": "Copy File",             "detail_arg": "destination_path"},
    "create_directory":    {"desc": "Create Directory",      "detail_arg": "path"},
    "fetch_web_page":      {"desc": "Fetch Web Page",        "detail_arg": "url"},
    "execute_python_code": {"desc": "Execute Python Code",   "detail_arg": "code"},
}
DANGEROUS_TOOLS = set(DANGEROUS_TOOL_INFO.keys())