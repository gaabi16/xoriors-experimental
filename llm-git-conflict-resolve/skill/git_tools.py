#!/usr/bin/env python3
"""
Git Merge Conflict Tools - Interface for Claude Code Agent
Provides deterministic, structured data about Git conflicts without resolution logic.
"""

import subprocess
import json
import sys
import re
import argparse
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ConflictType(Enum):
    """Classification of conflict types"""
    IMPORT = "IMPORT"
    WHITESPACE = "WHITESPACE"
    RENAME = "RENAME"
    REFACTOR = "REFACTOR"
    LOGIC = "LOGIC"
    FUNCTION_SIGNATURE = "FUNCTION_SIGNATURE"
    UNKNOWN = "UNKNOWN"


class Difficulty(Enum):
    """Estimated difficulty of resolution"""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    ESCALATE = "ESCALATE"

    # FIX: Această metodă permite funcției max() să compare dificultățile
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            order = ["EASY", "MEDIUM", "HARD", "ESCALATE"]
            try:
                return order.index(self.value) < order.index(other.value)
            except ValueError:
                return False
        return NotImplemented


@dataclass
class ConflictBlock:
    """Represents a single conflict block in a file"""
    start_line: int
    end_line: int
    ours: str
    theirs: str
    base: Optional[str] = None
    markers: Dict[str, int] = None


@dataclass
class FileConflict:
    """Complete conflict information for a file"""
    filepath: str
    conflict_type: ConflictType
    difficulty: Difficulty
    blocks: List[ConflictBlock]
    auto_resolvable: bool


def run_git_command(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Execute git command and return result"""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        # Don't crash immediately on git errors, allow handling
        if check:
            print(f"Git command failed: {e.stderr}", file=sys.stderr)
            raise
        return e


def list_conflicts() -> List[str]:
    """
    List all files with merge conflicts.
    """
    result = run_git_command(['status', '--porcelain'])
    conflicts = []
    
    if result.stdout:
        for line in result.stdout.splitlines():
            # UU = both modified, AA = both added
            if line.startswith('UU ') or line.startswith('AA '):
                filepath = line[3:].strip()
                conflicts.append(filepath)
    
    return conflicts


def extract_three_way(filepath: str) -> Dict:
    """
    Extract Base, Ours, and Theirs versions from Git stages.
    """
    # Git stages: :1 = base, :2 = ours (HEAD), :3 = theirs (incoming)
    stages = {}
    
    for stage_num, stage_name in [('1', 'base'), ('2', 'ours'), ('3', 'theirs')]:
        try:
            result = run_git_command(['show', f':{stage_num}:{filepath}'], check=False)
            stages[stage_name] = result.stdout if result.returncode == 0 else None
        except Exception:
            stages[stage_name] = None
    
    # Parse conflict markers from working tree
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        markers = parse_conflict_markers(content)
    except Exception as e:
        markers = []
        print(f"Warning: Could not parse markers: {e}", file=sys.stderr)
    
    return {
        'filepath': filepath,
        'base': stages['base'],
        'ours': stages['ours'],
        'theirs': stages['theirs'],
        'markers': markers
    }


def parse_conflict_markers(content: str) -> List[Dict]:
    """
    Parse conflict markers from file content.
    """
    lines = content.splitlines(keepends=True)
    conflicts = []
    i = 0
    
    while i < len(lines):
        # Look for conflict start marker
        if lines[i].startswith('<<<<<<<'):
            start = i
            ours_lines = []
            theirs_lines = []
            separator_idx = None
            end_idx = None
            
            # Find separator
            i += 1
            while i < len(lines):
                if lines[i].startswith('======='):
                    separator_idx = i
                    break
                ours_lines.append(lines[i])
                i += 1
            
            # Find end marker
            if separator_idx:
                i += 1
                while i < len(lines):
                    if lines[i].startswith('>>>>>>>'):
                        end_idx = i
                        break
                    theirs_lines.append(lines[i])
                    i += 1
            
            if separator_idx and end_idx:
                conflicts.append({
                    'start_line': start + 1,
                    'end_line': end_idx + 1,
                    'ours': ''.join(ours_lines),
                    'theirs': ''.join(theirs_lines),
                    'ours_label': lines[start].strip(),
                    'theirs_label': lines[end_idx].strip()
                })
        
        i += 1
    
    return conflicts


def get_context(filepath: str, lines_context: int = 5) -> Dict:
    """
    Get commit history and context for conflicted file.
    """
    # Get merge base
    try:
        merge_base = run_git_command(['merge-base', 'HEAD', 'MERGE_HEAD']).stdout.strip()
    except Exception:
        merge_base = None
    
    # Get commits from both branches
    ours_commits = []
    theirs_commits = []
    
    if merge_base:
        try:
            # Commits in our branch
            result = run_git_command([
                'log', '--oneline', '--no-merges',
                f'{merge_base}..HEAD', '--', filepath
            ], check=False)
            if result.stdout:
                ours_commits = [line.strip() for line in result.stdout.splitlines()]
            
            # Commits in their branch
            result = run_git_command([
                'log', '--oneline', '--no-merges',
                f'{merge_base}..MERGE_HEAD', '--', filepath
            ], check=False)
            if result.stdout:
                theirs_commits = [line.strip() for line in result.stdout.splitlines()]
        except Exception as e:
            print(f"Warning: Could not fetch commit history: {e}", file=sys.stderr)
    
    # Analyze dependencies (basic implementation)
    dependencies = analyze_dependencies(filepath)
    
    return {
        'filepath': filepath,
        'merge_base': merge_base,
        'ours_commits': ours_commits,
        'theirs_commits': theirs_commits,
        'dependencies': dependencies
    }


def analyze_dependencies(filepath: str) -> Dict[str, List[str]]:
    """
    Analyze code dependencies (imports, functions, variables).
    """
    try:
        # Try to read local file, might have markers
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return {'imports': [], 'functions': [], 'variables': []}
    
    imports = []
    functions = []
    
    # Basic pattern matching
    import_patterns = [
        r'^\s*import\s+[\w., ]+',
        r'^\s*from\s+[\w.]+\s+import\s+',
        r'^\s*#include\s*[<"][\w./]+[>"]',
    ]
    
    for pattern in import_patterns:
        imports.extend(re.findall(pattern, content, re.MULTILINE))
    
    # Function definitions (simplified)
    func_pattern = r'\b(?:def|function|func)\s+(\w+)\s*\('
    functions = re.findall(func_pattern, content)
    
    return {
        'imports': imports[:20],
        'functions': functions[:20],
        'variables': []
    }


def categorize_conflict(filepath: str) -> Dict:
    """
    Automatically categorize conflict type and difficulty.
    """
    data = extract_three_way(filepath)
    markers = data.get('markers', [])
    
    if not markers:
        return {
            'type': ConflictType.UNKNOWN.value,
            'difficulty': Difficulty.MEDIUM.value,
            'auto_resolvable': False,
            'reason': 'No conflict markers found'
        }
    
    # Analyze all conflict blocks
    conflict_types = []
    max_difficulty = Difficulty.EASY
    
    for marker in markers:
        ours = marker['ours'].strip()
        theirs = marker['theirs'].strip()
        
        # 1. IMPORT
        if any(keyword in ours + theirs for keyword in ['import ', 'from ', '#include', 'require(']):
            conflict_types.append(ConflictType.IMPORT)
            continue
        
        # 2. WHITESPACE
        if ours.replace(' ', '').replace('\t', '').replace('\n', '') == \
           theirs.replace(' ', '').replace('\t', '').replace('\n', ''):
            conflict_types.append(ConflictType.WHITESPACE)
            continue
        
        # 3. FUNCTION SIGNATURE
        if any(keyword in ours + theirs for keyword in ['def ', 'function ', 'func ', 'class ']):
            conflict_types.append(ConflictType.FUNCTION_SIGNATURE)
            max_difficulty = max(max_difficulty, Difficulty.MEDIUM)
            continue

        # 4. RENAME DETECTOR (Logic Nou)
        ours_words = set(re.findall(r'\w+', ours))
        theirs_words = set(re.findall(r'\w+', theirs))
        diff = ours_words.symmetric_difference(theirs_words)
        
        # Verificăm dacă schimbarea implică cifre (ex: value=2 vs value=3)
        is_numeric_change = any(d.isdigit() for d in diff)
        
        # Euristică: E rename doar dacă NU sunt cifre implicate
        if not is_numeric_change and len(diff) < 3 and len(ours_words) > 0:
            conflict_types.append(ConflictType.RENAME)
            max_difficulty = max(max_difficulty, Difficulty.MEDIUM)
            continue
        
        # 5. Default: LOGIC
        conflict_types.append(ConflictType.LOGIC)
        max_difficulty = Difficulty.HARD
    
    # Determine primary type
    if not conflict_types:
        primary_type = ConflictType.UNKNOWN
    else:
        priority = [ConflictType.LOGIC, ConflictType.FUNCTION_SIGNATURE, 
                   ConflictType.REFACTOR, ConflictType.RENAME, 
                   ConflictType.IMPORT, ConflictType.WHITESPACE]
        primary_type = conflict_types[0]
        for t in priority:
            if t in conflict_types:
                primary_type = t
                break
    
    auto_resolvable = all(
        t in [ConflictType.IMPORT, ConflictType.WHITESPACE] 
        for t in conflict_types
    )
    
    # Escalate logic
    if primary_type == ConflictType.LOGIC:
        max_difficulty = Difficulty.HARD
        if len(markers) > 3:
            max_difficulty = Difficulty.ESCALATE
    
    return {
        'type': primary_type.value,
        'difficulty': max_difficulty.value,
        'auto_resolvable': auto_resolvable,
        'all_types': [t.value for t in conflict_types],
        'num_conflicts': len(markers)
    }


def validate_file(filepath: str, language: Optional[str] = None) -> Dict:
    """
    Validate syntax and semantics of resolved file.
    """
    if language is None:
        ext = Path(filepath).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript', '.ts': 'typescript',
            '.go': 'go', '.rs': 'rust',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c'
        }
        language = lang_map.get(ext, 'unknown')
    
    results = {
        'filepath': filepath,
        'language': language,
        'syntax_valid': None,
        'semantic_errors': [],
        'warnings': []
    }
    
    # Python syntax validation
    if language == 'python':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            results['syntax_valid'] = True
        except SyntaxError as e:
            results['syntax_valid'] = False
            results['semantic_errors'].append(f"Line {e.lineno}: {e.msg}")
        except Exception as e:
            results['warnings'].append(f"Validation error: {str(e)}")
    
    # Other languages - placeholders
    else:
        results['warnings'].append(f'No syntax validator available for {language}')
        results['syntax_valid'] = True # Assume valid if we can't check
    
    # Check for remaining conflict markers
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if any(marker in content for marker in ['<<<<<<<', '=======', '>>>>>>>']):
            results['semantic_errors'].append('Conflict markers still present')
            results['syntax_valid'] = False
    except Exception as e:
        results['warnings'].append(f'Could not check for markers: {e}')
    
    return results


def create_backup(branch_name: Optional[str] = None) -> str:
    """
    Create backup branch before resolution.
    """
    if branch_name is None:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f'backup-merge-{timestamp}'
    
    try:
        run_git_command(['branch', branch_name])
        return branch_name
    except Exception as e:
        # Branch might exist, try to checkout logic or simple fail
        raise RuntimeError(f"Failed to create backup branch: {e}")


def main():
    """CLI interface for git_tools"""
    parser = argparse.ArgumentParser(
        description='Git merge conflict analysis tools for Claude Code'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List conflicts
    subparsers.add_parser('list', help='List all files with conflicts')
    
    # Extract three-way diff
    extract_parser = subparsers.add_parser('extract', help='Extract 3-way diff')
    extract_parser.add_argument('filepath', help='File to extract')
    extract_parser.add_argument('--with-context', action='store_true',
                               help='Include commit history context')
    
    # Get context
    context_parser = subparsers.add_parser('context', help='Get commit context')
    context_parser.add_argument('filepath', help='File to analyze')
    
    # Categorize conflict
    categorize_parser = subparsers.add_parser('categorize', help='Categorize conflict')
    categorize_parser.add_argument('filepath', help='File to categorize')
    
    # Validate file
    validate_parser = subparsers.add_parser('validate', help='Validate resolved file')
    validate_parser.add_argument('filepath', help='File to validate')
    validate_parser.add_argument('--language', help='Programming language')
    
    # Create backup
    backup_parser = subparsers.add_parser('backup', help='Create backup branch')
    backup_parser.add_argument('--name', help='Custom branch name')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'list':
            conflicts = list_conflicts()
            print(json.dumps(conflicts, indent=2))
        
        elif args.command == 'extract':
            data = extract_three_way(args.filepath)
            if args.with_context:
                context = get_context(args.filepath)
                data['context'] = context
                category = categorize_conflict(args.filepath)
                data['category'] = category
            print(json.dumps(data, indent=2))
        
        elif args.command == 'context':
            context = get_context(args.filepath)
            print(json.dumps(context, indent=2))
        
        elif args.command == 'categorize':
            category = categorize_conflict(args.filepath)
            print(json.dumps(category, indent=2))
        
        elif args.command == 'validate':
            results = validate_file(args.filepath, args.language)
            print(json.dumps(results, indent=2))
        
        elif args.command == 'backup':
            branch_name = create_backup(args.name)
            print(json.dumps({'backup_branch': branch_name}, indent=2))
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except Exception as e:
        # Return structured error for the AI to handle
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()