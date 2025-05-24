*Just a simple test implementation of Demolari's [node-memory-system](https://github.com/Demolari/node-memory-system) concept.*

# ToyAgent: A CLI Assistant with Tools and Node-Based Memory

**ToyAgent** is a Python-based command-line interface (CLI) agent that interacts with OpenAI-compatible language models. It's designed to be a versatile assistant capable of performing tasks by utilizing a range of "tools," including file operations, shell command execution, Python code execution, web fetching, and direct user interaction. A key feature is its persistent node-based memory system, allowing it to store, tag, and retrieve information across sessions.

## Overview

The agent operates by taking user prompts (either in an interactive loop or as a single command) and deciding whether to respond directly or to use one of its available tools to gather more information or perform an action. For potentially harmful actions, it seeks explicit user approval. The integrated node-based memory system enhances its ability to learn and recall information over time, making it suitable for more personalized and context-aware interactions.

## Features

*   **Interactive Mode:** Engage in a continuous conversation with the assistant.
*   **Single-Pass Mode:** Provide a one-off prompt for the agent to execute and then exit.
*   **Extensible Toolset:**
    *   File system operations: `read_file`, `write_file`, `copy_file`, `list_directory`, `create_directory`.
    *   Code execution: `execute_shell_command`, `execute_python_code`.
    *   Information retrieval: `fetch_web_page`.
    *   User interaction: `ask_user`.
*   **Node-Based Memory System:**
    *   Persistently store and retrieve pieces of information ("nodes").
    *   Nodes are enriched with descriptive tags for efficient querying (e.g., `character:Abigail`, `project:Phoenix`, `user_preference:color_blue`).
    *   Tools to `create_memory_node`, `retrieve_memory_nodes`, `update_memory_node`, `delete_memory_node`, and `list_memory_nodes`.
    *   Memory is saved to a user-specified JSON file.
*   **User Approval for Dangerous Actions:** Critical actions (e.g., file system changes, code/shell execution, web access) require explicit user confirmation before execution.
*   **Colored Terminal Output:** Uses `colorama` (if available) for improved readability of assistant messages, tool calls, and warnings.
*   **Configurable:** Set API key, API base URL (for non-OpenAI providers), model name, temperature, and top-p sampling parameters.

## How it Works (Agent Loop)

1.  **User Input:** The user provides a prompt.
2.  **System Prompt Construction:** A system prompt is generated, informing the LLM about its role, OS environment, available tools, and the current date/time. If memory is enabled, instructions for memory tools are included.
3.  **API Call:** The conversation history (including the system prompt and user input) is sent to the configured LLM.
4.  **Response Processing:**
    *   **Text Response:** If the LLM responds with text, it's displayed to the user.
    *   **Tool Call(s):** If the LLM requests one or more tool calls:
        *   The agent parses the tool name and arguments.
        *   **Approval:** If a tool is marked "dangerous," the agent prints the details of the requested action and asks the user for approval (`y/N`).
        *   **Execution:** If approved (or if the tool is not dangerous), the corresponding Python function for the tool is executed.
        *   **Result:** The output/result from the tool is formatted as a message.
        *   The conversation history is updated with the tool call request and the tool result.
        *   The agent makes another API call to the LLM with the updated history, allowing the LLM to process the tool's output and continue.
5.  **Loop:** This process repeats, allowing for multi-turn conversations and sequences of tool uses.

## Requirements

*   Python 3.7+
*   `openai` library: For interacting with OpenAI-compatible APIs.
*   `requests` library: Used by the `fetch_web_page` tool.
*   `colorama` library (optional but recommended): For colored terminal output.

## Setup

1.  **Get the Code:**
    Ensure you have both `toyagent.py` and `toyagent_tools.py` in the same directory.

2.  **Install Dependencies:**
    Open your terminal and run:
    ```bash
    pip install openai requests colorama
    ```

3.  **Set OpenAI API Key:**
    The agent requires an API key from an OpenAI-compatible provider. You can set it as an environment variable:
    ```bash
    # For Linux/macOS
    export OPENAI_API_KEY="your_api_key_here"
    # For Windows (Command Prompt)
    set OPENAI_API_KEY=your_api_key_here
    # For Windows (PowerShell)
    $env:OPENAI_API_KEY="your_api_key_here"
    ```
    Alternatively, you can pass the API key directly using the `-k` or `--api-key` command-line argument.

4.  **(Optional) Set OpenAI Base URL:**
    If you are using a third-party provider compatible with the OpenAI API, or a proxy, you might need to set a custom base URL.
    ```bash
    # For Linux/macOS
    export OPENAI_BASE_URL="your_custom_api_base_url"
    # (Similar for Windows)
    ```
    This can also be passed via the `-b` or `--base-url` argument.

## Usage

### Command-Line Arguments

To see all available options, run:
```bash
python toyagent.py --help
```

This will output:
```
usage: toyagent.py [-h] [-k API_KEY] [-b BASE_URL] [-m MODEL] [-t TEMPERATURE] [-p TOP_P] [--memory-file MEMORY_FILE] [prompt]

Python CLI agent interacting with OpenAI-compatible APIs using tools.

positional arguments:
  prompt                Initial prompt. If omitted, enters interactive mode. (default: None)

options:
  -h, --help            show this help message and exit
  -k API_KEY, --api-key API_KEY
                        API key (or use $OPENAI_API_KEY). REQUIRED. (default: <your_env_var_value_or_None>)
  -b BASE_URL, --base-url BASE_URL
                        API base URL (for non-OpenAI providers, or use $OPENAI_BASE_URL). Optional. (default: <your_env_var_value_or_None>)
  -m MODEL, --model MODEL
                        Model name. (default: gpt-4o-mini)
  -t TEMPERATURE, --temperature TEMPERATURE
                        Sampling temperature (e.g., 0.6). (default: 0.6)
  -p TOP_P, --top-p TOP_P
                        Nucleus sampling 'top_p' (e.g., 0.9). (default: 0.9)
  --memory-file MEMORY_FILE
                        Path to JSON file for persistent memory. If not provided, memory is not used. Default if enabled but path not specified: agent_memory.json (but disabled by default). To enable, provide a path e.g. './agent_memory.json' (default: None)
```

### Interactive Mode

If you run the script without an initial `prompt`, it enters interactive mode:
```bash
python toyagent.py
```
You can then type your messages, and the assistant will respond. Type `quit` or `exit` to end the session.

### Single-Pass Mode

Provide an initial prompt as a command-line argument:
```bash
python toyagent.py "What is the current directory? Then, list all python files in it."
```
The agent will attempt to complete the task and then exit.

### Using the Node-Based Memory System

To enable persistent memory, use the `--memory-file` argument, followed by the path to a JSON file where memories will be stored.
```bash
# Start interactive mode with memory stored in 'my_project_notes.json'
python toyagent.py --memory-file my_project_notes.json

# Run a single task using memory
python toyagent.py --memory-file user_prefs.json "Remind me about my preferred settings for project X."
```
If you provide `--memory-file` without a specific path (e.g., `python toyagent.py --memory-file ""`), it will default to using `agent_memory.json` in the current directory. If the specified memory file does not exist, it will be created. Memory is saved to the file after each memory-modifying tool operation and when the agent exits.

## Available Tools

The agent has access to the following tools, which it can choose to use based on your prompts:

### Standard Tools

*   `execute_python_code`: Executes a given snippet of Python code. **(DANGEROUS)**
*   `execute_shell_command`: Executes a shell command. **(DANGEROUS)**
*   `read_file`: Reads the entire content of a specified file.
*   `write_file`: Writes content to a specified file. Creates directories if needed. **(DANGEROUS)**
*   `copy_file`: Copies a source file to a destination path. **(DANGEROUS)**
*   `list_directory`: Lists files and subdirectories within a directory.
*   `create_directory`: Creates a new directory, including parent directories if needed. **(DANGEROUS)**
*   `fetch_web_page`: Fetches the text content of a given URL. **(DANGEROUS)**
*   `ask_user`: Asks the human user a question and returns their response.

### Memory Management Tools

These tools are available when the `--memory-file` option is used:

*   `create_memory_node`: Creates a new memory node with specified `tags` (list of strings), `content` (string), and an optional `source_chat` identifier. Returns the new node's ID and details.
*   `retrieve_memory_nodes`: Searches for memory nodes. Requires `match_all_tags` (a list of tags that nodes must possess). Can optionally filter by `query_in_content` (a string to find within node content) and limit the number of results.
*   `update_memory_node`: Modifies an existing node specified by `node_id`. Can update `new_content`, `add_tags`, or `remove_tags`.
*   `delete_memory_node`: Deletes a memory node specified by `node_id`.
*   `list_memory_nodes`: Lists stored memory nodes, optionally filtered by `filter_match_all_tags`. Supports pagination with `limit` and `offset`.

### Dangerous Tools & User Approval

Tools marked **(DANGEROUS)** can perform actions that might have significant or unintended consequences (e.g., modifying your file system, running arbitrary code, accessing the internet). For these tools, **ToyAgent will always print a clear description of the action it wants to take and ask for your explicit approval (`y/N`) before proceeding.** Review these requests very carefully.

## Node-Based Memory System

The node-based memory system is inspired by the conceptual `node_memory_system.txt` provided, aiming for more structured and efficient long-term information retention than simple chat history.

*   **Concept:** Information is broken down into discrete "nodes." Each node represents a specific idea, fact, event, or piece of data.
*   **Tags:** Each node is associated with a list of descriptive string tags (e.g., `["user:john", "project:alpha", "deadline:2024-12-31"]`). These tags are crucial for semantic searching and retrieval. The LLM is instructed to create meaningful and specific tags.
*   **Content:** The main information payload of the node.
*   **Metadata:** Nodes also store a unique `node_id`, `created_at`, and `updated_at` timestamps, and an optional `source_chat` field.
*   **Persistence:** All memory nodes are stored in a single JSON file specified by the `--memory-file` argument. This allows information to persist across different sessions of running the agent.
*   **Interaction via Tools:** The LLM interacts with this memory system exclusively through the dedicated memory management tools. For example, to remember a user's preference, it would call `create_memory_node`. To recall it, it would use `retrieve_memory_nodes` with appropriate tags.

**Benefits:**

*   **Targeted Recall:** Allows the agent to retrieve specific, relevant information without processing vast amounts of raw text from past conversations, saving on token usage and processing time.
*   **Personalization:** Enables the agent to "remember" user details, preferences, project information, or past significant interactions over extended periods.
*   **Structured Knowledge:** Organizes information in a more structured and machine-usable way.

## Example Interaction (with Memory)

1.  **Start the agent with memory enabled:**
    ```bash
    python toyagent.py --memory-file ./shared_notes.json
    ```

2.  **User tells the agent something to remember:**
    ```
    User:
    Please remember that the project codenamed "Aquila" has a deadline of next Friday.

    Assistant:
    Okay, I'll make a note that Project Aquila's deadline is next Friday.

    Tool Call Request:
      Function: create_memory_node
      Arguments:
    {
      "tags": [
        "project:Aquila",
        "deadline",
        "task_management"
      ],
      "content": "Project Aquila deadline is next Friday."
    }
    Tool Result (create_memory_node [...]):
    {
      "node_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "status": "created",
      "node": { ... details of the node ... }
    }

    Assistant:
    I've noted that Project Aquila's deadline is next Friday.
    ```

3.  **Later, the user asks for a reminder:**
    ```
    User:
    What's the deadline for Project Aquila?

    Assistant:
    Let me check my notes on that.

    Tool Call Request:
      Function: retrieve_memory_nodes
      Arguments:
    {
      "match_all_tags": [
        "project:Aquila",
        "deadline"
      ]
    }
    Tool Result (retrieve_memory_nodes [...]):
    {
      "nodes": [
        {
          "node_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
          "tags": ["project:Aquila", "deadline", "task_management"],
          "content": "Project Aquila deadline is next Friday.",
          ...
        }
      ],
      "count": 1
    }

    Assistant:
    The deadline for Project Aquila is next Friday.
    ```

## Disclaimer

*   This is a "toy" agent. While it implements powerful tools, exercise extreme caution, especially with `execute_shell_command` and `execute_python_code`. **Always review approval requests carefully.**
*   The effectiveness of the memory system and tool usage depends heavily on the capabilities of the underlying LLM.
*   The agent and its tools operate with the permissions of the user running the script.

## Potential Future Enhancements

*   More sophisticated memory querying (e.g., OR logic for tags, date range searches).
*   Automatic summarization or pruning of old/less relevant memory nodes.
*   Integration of more complex tools or APIs.
*   A more robust sandboxing environment for code execution.
*   Support for asynchronous tool execution.
```
