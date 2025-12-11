# Git Merge Conflict Resolution Skill for AI Agents

This repository contains a modular skill designed to enable AI agents (specifically within the Claude Code environment) to autonomously and accurately resolve git merge conflicts.

While Large Language Models are proficient at writing code, they often struggle with the syntax of standard git merge markers (`<<<<<<<`, `=======`, `>>>>>>>`) due to a lack of context regarding the conflicting branches. This project bridges that gap by providing the agent with executable tools to retrieve the full history of the conflict (Base, Local, Remote) and a strict set of operational guidelines.

## Architecture Overview

The solution relies on a "Tool-Use" pattern where the agent acts not just as a text processor but as an orchestrator. It uses local Python scripts to interact with the Git CLI, processes the data, and applies resolution logic based on a predefined educational context.

## Repository Structure & File Descriptions

To implement this skill effectively, the project requires the following file structure. Each file serves a specific role in the agent's decision-making loop.

### 1. `instructions.md` (The Educational Layer)

This file acts as the system prompt or "knowledge base" for the agent. It dictates the behavior and decision-making process. It does not contain code to be executed, but rather the logic the agent must follow.

**Purpose:** Teaches the agent the "Algorithm of Resolution."

**Key Contents:**

* **Step-by-Step Workflow:** Instructions to identify conflicts, fetch raw data, analyze intent, and apply fixes.
* **Conflict Strategies:** Rules for handling specific scenarios:
    * **Independent Changes:** When both branches modified different parts, merge both changes
    * **Conflicting Logic:** When same lines have incompatible changes, prefer the version from the more authoritative branch (typically main/master)
    * **Rename Conflicts:** When variables/functions are renamed, follow the naming standard from main branch
    * **Import Conflicts:** Perform a union of all imports from both branches, sorted alphabetically
    * **Ambiguous Cases:** When intent is unclear, keep current version and add TODO comment with explanation
* **Special Cases:** Instructions for handling deleted files, binary files, and multiple conflicts in one file
* **Validation Requirements:** Mandate to always validate syntax before staging

### 2. `git_tools.py` (The Execution Layer)

This Python script serves as the bridge between the AI agent and the local Git repository. The agent calls functions within this file to gather factual data about the state of the codebase.

**Purpose:** Provides deterministic, structured data to the LLM.

**Key Functions:**

* `list_conflicted_files()`: Parses `git status --porcelain` to identify files with merge conflicts (status "UU")
* `get_three_way_diff(filepath)`: Uses `git show` to extract the three versions:
    * **:1 (Base):** The common ancestor
    * **:2 (Ours):** The local changes (HEAD)
    * **:3 (Theirs):** The incoming changes
    * Returns structured JSON with all three versions plus branch names
* `validate_syntax(filepath)`: Runs language-specific validation:
    * Python: Uses `ast.parse()` to check syntax
    * JavaScript/TypeScript: Attempts to use eslint if available
    * Java: Attempts to use javac if available
    * Returns JSON with validation status and error messages

**CLI Interface:** Accepts commands `--list`, `--extract <file>`, `--verify <file>` and outputs JSON for easy parsing by the agent.

### 3. `resolution_template.md` (Optional)

A template file used by the agent to structure its reasoning before editing the code.

**Purpose:** Forces the agent to output a "Chain of Thought" before writing code.

**Structure:**
* Conflict Summary (file, branches, location)
* Version Analysis (what Base, Ours, and Theirs contain)
* Detected Intent (what each branch was trying to accomplish)
* Conflict Type Classification
* Proposed Resolution Strategy
* Proposed Resolution Code
* Reasoning
* Validation Checklist

### 4. `examples/conflict_scenarios.md` (Optional but Recommended)

Real-world examples of common conflict patterns and their resolutions.

**Purpose:** Provides concrete examples the agent can reference when encountering similar conflicts.

**Contents:**
* Example: Independent feature additions (logging vs. validation) with resolution showing both merged
* Example: Variable rename conflicts with resolution following main branch convention
* Example: Import statement differences with resolution performing union
* Example: Conflicting algorithm changes with resolution preferring main branch
* Example: Deleted vs. modified file with context-dependent decision

Each example shows Base, Ours, Theirs, and the Resolution with explanation.

## Operational Workflow

When the agent is tasked with fixing a merge conflict, the expected execution flow is:

1. **Context Loading:** The agent reads `instructions.md` to understand its role and constraints.
2. **Discovery:** The agent executes `python git_tools.py --list` to find the target files.
3. **Data Extraction:** For every conflict, the agent executes `python git_tools.py --extract <filename>`. It receives a structured JSON object containing the Base, Ours, and Theirs content plus branch information.
4. **Intent Analysis:** The agent compares the three versions to understand what changed and why in each branch.
5. **Strategy Selection:** Based on the analysis, the agent selects the appropriate resolution strategy from `instructions.md`.
6. **Logic Synthesis:** The agent reconstructs the valid code path based on the chosen strategy, preserving intent from both branches when possible.
7. **Application:** The agent rewrites the file content locally with the resolved code.
8. **Verification:** The agent executes `python git_tools.py --verify <filename>` to catch syntax errors.
9. **Staging:** If validation passes, the agent runs `git add <filename>`.
10. **Completion:** After all conflicts are resolved, the agent can commit the merge.

## Key Design Principles

**Separation of Concerns:** Documentation defines the "what" and "why" while code handles the "how". The agent orchestrates both.

**Structured Data Over Text Parsing:** All tool outputs are JSON with predictable schemas. The agent receives facts (three versions) not opinions (conflict markers).

**Explicit Decision Framework:** Every type of conflict has a defined strategy in instructions.md with documented fallback behavior.

**Safety Through Validation:** Syntax validation is mandatory before staging to prevent broken commits.

**Transparency and Traceability:** Optional resolution template encourages documenting reasoning, and TODO comments preserve context when full resolution is not possible.

## Integration

To add this skill to your agent configuration:

1. Place `git_tools.py` in the root or a dedicated `scripts/` directory.
2. Add the content of `instructions.md` to the agent's context or system prompt.
3. Optionally add `resolution_template.md` and `examples/conflict_scenarios.md` to the context.
4. Ensure the agent has permission to execute shell commands (specifically `python` and `git`).

## Expected Outcomes

With this skill properly configured, the agent should be able to:

* Detect all merge conflicts in a repository
* Successfully resolve the majority of simple conflicts (independent changes, imports, renames)
* Identify complex conflicts that require human review and add appropriate TODO comments
* Never stage syntactically invalid code
* Preserve the intent of changes from both branches when merging
* Defer to humans for semantic conflicts requiring deep domain knowledge