#!/bin/bash

# Setup script for Git merge conflict demo (Scenario: Multi-file Conflict)
# Conflict: Infrastructure changes (Local) vs Feature enhancements (Remote)

# 1. Create directory
mkdir -p conflict-multi-file
cd conflict-multi-file

# 2. Initialize git quietly
git init -q
git config user.email "dev@example.com"
git config user.name "Dev User"

# 3. Copy tools and setup GEMINI.md
if [ -d "../skill" ]; then
    cp ../skill/git_tools.py .
    cp ../skill/instructions.md GEMINI.md
else
    echo "Error: '../skill' directory not found."
    exit 1
fi

# 4. Base Commit (Create 2 files)
cat > database.py << 'EOF'
def connect_to_db():
    """Basic connection setup."""
    host = "localhost"
    port = 5432
    return f"Connecting to {host}:{port}"
EOF

cat > utils.py << 'EOF'
def format_date(date_obj):
    """Simple date formatter."""
    return date_obj.strftime("%Y-%m-%d")
EOF

git add .
git commit -q -m "Initial commit: Core modules"

# 5. Remote Branch (Feature): Add Timeout & Timezones
git checkout -q -b feature-enhanced
cat > database.py << 'EOF'
def connect_to_db():
    """Connection with timeout safety."""
    host = "localhost"
    port = 5432
    timeout = 30 # Added timeout
    return f"Connecting to {host}:{port} (timeout={timeout}s)"
EOF

cat > utils.py << 'EOF'
def format_date(date_obj):
    """Formatter with UTC conversion."""
    # Convert to UTC before printing
    utc_date = date_obj.astimezone(timezone.utc)
    return utc_date.strftime("%Y-%m-%d %H:%M:%S")
EOF

git commit -a -q -m "Feature: Add DB timeout and UTC dates"

# 6. Local Branch (Master): Switch to Production & US Format
git checkout -q master
cat > database.py << 'EOF'
import os

def connect_to_db():
    """Production connection setup."""
    # Switched to ENV variables for security
    host = os.getenv("DB_HOST", "prod-db")
    port = 5432
    return f"Connecting to {host}:{port}"
EOF

cat > utils.py << 'EOF'
def format_date(date_obj):
    """Formatter for US reports."""
    return date_obj.strftime("%m/%d/%Y")
EOF

git commit -a -q -m "Update: Prod config and US date format"

# 7. Create Conflict
git merge feature-enhanced --no-edit > /dev/null 2>&1 || true

echo "=================================="
echo "Conflicted Repo Ready (Multi-File)"
echo "Folder: conflict-multi-file/"
echo "Files in conflict: database.py, utils.py"
echo "To start: cd conflict-multi-file && gemini"
echo "=================================="