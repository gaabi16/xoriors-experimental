#!/bin/bash

# Setup script for Git merge conflict resolution demo
# Run this from llm-git-conflict-resolve/ directory

echo "Setting up Git merge conflict playground..."
echo ""

# 1. Create and enter playground directory
mkdir -p playground
cd playground

# 2. Initialize git repo
echo "Initializing Git repository..."
git init
git config user.email "test@example.com"
git config user.name "Test User"

# 3. Copy git_tools.py & instructions.md from skill directory
echo "Copying git_tools.py..."
cp ../skill/git_tools.py .
echo "Copying instructions.md..."
cp ../skill/instructions.md .

# 4. Create initial file with base implementation
echo "Creating base file..."
cat > utils.py << 'EOF'
import os
import sys

def process_data(data):
    """Process the input data."""
    result = []
    for item in data:
        result.append(item * 2)
    return result

def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total
EOF

git add utils.py
git commit -m "Initial commit: Base implementation"

# 5. Create feature branch (Remote) - adds new functionality
echo "Creating feature branch..."
git checkout -b feature
cat > utils.py << 'EOF'
import os
import sys
import json

def process_data(data):
    """Process the input data with enhanced logging."""
    result = []
    for item in data:
        print(f"Processing: {item}")
        result.append(item * 2)
    return result

def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total

def export_to_json(data, filename):
    """Export data to JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
EOF

git commit -a -m "Feature: Add JSON export and logging to process_data"

# 6. Go back to master - refactor function names
echo "Switching to master and refactoring..."
git checkout master
cat > utils.py << 'EOF'
import os
import sys

def transform_data(data):
    """Transform the input data (renamed from process_data)."""
    result = []
    for item in data:
        result.append(item * 2)
    return result

def sum_numbers(numbers):
    """Calculate sum of numbers (renamed from calculate_sum)."""
    total = 0
    for num in numbers:
        total += num
    return total
EOF

git commit -a -m "Refactor: Rename functions for clarity (process_data -> transform_data, calculate_sum -> sum_numbers)"

# 7. Create the conflict!
echo "Creating merge conflict..."
git merge feature --no-edit 2>/dev/null || true

echo ""
echo "=================================="
echo "Conflict playground created!"
echo "=================================="
echo ""
echo "Location: playground/"
echo ""
echo "Conflict Summary:"
echo "  - Local (master): Refactored function names"
echo "  - Remote (feature): Added JSON export + logging"
echo ""
echo "Test the tool with:"
echo "  cd playground"
echo "  python3 git_tools.py list"
echo "  python3 git_tools.py extract utils.py"
echo "  python3 git_tools.py verify utils.py"
echo ""
echo "Expected resolution:"
echo "  - Keep new function names from Local (transform_data, sum_numbers)"
echo "  - Add JSON export function from Remote"
echo "  - Add logging to transform_data (but use new name)"
echo "  - Keep json import from Remote"
echo ""
