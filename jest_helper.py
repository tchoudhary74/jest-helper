# ============================================================
# JEST HELPER MCP SERVER
#
# This MCP gives Claude tools to:
# - Read and understand your existing test patterns
# - Run tests and see results
# - Write/fix tests matching YOUR style
# - Enforce consistent test patterns across all developers
# ============================================================

import os
import subprocess
import json
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ------------------------------------------------------------
# INITIALIZE MCP SERVER
# ------------------------------------------------------------
mcp = FastMCP("jest-helper")

# ------------------------------------------------------------
# CONFIGURATION
#
# The project path is passed via environment variable.
# This allows the same MCP to work with any project.
#
# Team settings are loaded from .jest-helper.json in project root.
# ------------------------------------------------------------
def get_project_root() -> str:
    """Get the project root from environment variable or current directory."""
    return os.environ.get("PROJECT_ROOT", os.getcwd())


# Default configuration - used when no .jest-helper.json exists
DEFAULT_CONFIG = {
    "style_guide": {
        "test_structure": "describe + it",
        "it_naming": "should + verb",
        "describe_naming": "component/function name",
        "arrangement": "AAA (Arrange-Act-Assert)",
        "comments": True,
        "imports_order": ["react", "testing-library", "components", "utils", "mocks"],
        "mock_location": "top of file after imports",
        "assertions_per_test": "1-3 related assertions",
        "edge_cases_required": ["null/undefined", "empty values", "error states"],
        "custom_rules": []
    },
    "templates": {
        "react_component": '''import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ComponentName } from './ComponentName';

describe('ComponentName', () => {
  // Arrange: Common setup
  const defaultProps = {};

  describe('rendering', () => {
    it('should render without crashing', () => {
      // Arrange
      const props = { ...defaultProps };

      // Act
      render(<ComponentName {...props} />);

      // Assert
      expect(screen.getByRole('...')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('should handle click events', async () => {
      // Arrange
      const user = userEvent.setup();
      const mockHandler = jest.fn();
      render(<ComponentName onClick={mockHandler} />);

      // Act
      await user.click(screen.getByRole('button'));

      // Assert
      expect(mockHandler).toHaveBeenCalledTimes(1);
    });
  });

  describe('edge cases', () => {
    it('should handle empty props gracefully', () => {
      // Arrange & Act
      render(<ComponentName />);

      // Assert
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });
});''',
        "hook": '''import { renderHook, act } from '@testing-library/react';
import { useHookName } from './useHookName';

describe('useHookName', () => {
  describe('initialization', () => {
    it('should return initial state', () => {
      // Arrange & Act
      const { result } = renderHook(() => useHookName());

      // Assert
      expect(result.current.value).toBe(initialValue);
    });
  });

  describe('actions', () => {
    it('should update state when action is called', () => {
      // Arrange
      const { result } = renderHook(() => useHookName());

      // Act
      act(() => {
        result.current.doAction();
      });

      // Assert
      expect(result.current.value).toBe(expectedValue);
    });
  });
});''',
        "utility_function": '''import { functionName } from './utils';

describe('functionName', () => {
  describe('valid inputs', () => {
    it('should return expected result for valid input', () => {
      // Arrange
      const input = validInput;

      // Act
      const result = functionName(input);

      // Assert
      expect(result).toBe(expectedOutput);
    });
  });

  describe('edge cases', () => {
    it('should handle null input', () => {
      // Arrange & Act & Assert
      expect(functionName(null)).toBe(defaultValue);
    });

    it('should handle undefined input', () => {
      // Arrange & Act & Assert
      expect(functionName(undefined)).toBe(defaultValue);
    });

    it('should handle empty input', () => {
      // Arrange & Act & Assert
      expect(functionName('')).toBe(defaultValue);
    });
  });

  describe('error cases', () => {
    it('should throw for invalid input', () => {
      // Arrange & Act & Assert
      expect(() => functionName(invalidInput)).toThrow();
    });
  });
});''',
        "api_service": '''import { apiFunction } from './api';

// Mock dependencies
jest.mock('./httpClient');

describe('apiFunction', () => {
  // Arrange: Common setup
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('successful requests', () => {
    it('should return data on success', async () => {
      // Arrange
      const mockResponse = { data: 'test' };
      httpClient.get.mockResolvedValue(mockResponse);

      // Act
      const result = await apiFunction();

      // Assert
      expect(result).toEqual(mockResponse);
      expect(httpClient.get).toHaveBeenCalledWith('/endpoint');
    });
  });

  describe('error handling', () => {
    it('should handle network errors', async () => {
      // Arrange
      httpClient.get.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(apiFunction()).rejects.toThrow('Network error');
    });
  });
});'''
    },
    "validation_rules": [
        {"id": "has_describe", "description": "Test must use describe() blocks", "pattern": r"describe\s*\("},
        {"id": "has_it_or_test", "description": "Test must use it() or test()", "pattern": r"(it|test)\s*\("},
        {"id": "it_uses_should", "description": "it() should start with 'should'", "pattern": r"it\s*\(\s*['\"]should"},
        {"id": "has_assertions", "description": "Test must have assertions", "pattern": r"expect\s*\("},
        {"id": "has_aaa_comments", "description": "Test should have AAA comments", "pattern": r"//\s*(Arrange|Act|Assert)"},
        {"id": "no_only", "description": "No .only() in tests", "pattern": r"\.(only|skip)\s*\(", "must_not_match": True},
        {"id": "has_edge_cases", "description": "Should test edge cases", "pattern": r"(null|undefined|empty|error)"}
    ]
}


def load_config() -> dict:
    """Load configuration from .jest-helper.json or use defaults."""
    project_root = get_project_root()
    config_path = Path(project_root) / ".jest-helper.json"

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            # Merge with defaults (user config takes precedence)
            merged = DEFAULT_CONFIG.copy()
            for key in user_config:
                if isinstance(user_config[key], dict) and key in merged:
                    merged[key] = {**merged[key], **user_config[key]}
                else:
                    merged[key] = user_config[key]
            return merged
        except (json.JSONDecodeError, IOError):
            pass

    return DEFAULT_CONFIG


# ============================================================
# SECTION 1: READING TOOLS
# These tools help Claude understand your codebase
# ============================================================

@mcp.tool()
def find_test_files(directory: str = "") -> str:
    """
    Find all test files in the project.

    Args:
        directory: Subdirectory to search in (relative to project root).
                   Leave empty to search entire project.

    Returns:
        List of test file paths, one per line.
    """
    project_root = get_project_root()
    search_path = Path(project_root) / directory if directory else Path(project_root)

    if not search_path.exists():
        return f"Error: Directory not found: {search_path}"

    # Find files matching common test patterns
    test_patterns = [
        "**/*.test.ts",
        "**/*.test.tsx",
        "**/*.test.js",
        "**/*.test.jsx",
        "**/*.spec.ts",
        "**/*.spec.tsx",
        "**/*.spec.js",
        "**/*.spec.jsx",
    ]

    test_files = []
    for pattern in test_patterns:
        test_files.extend(search_path.glob(pattern))

    # Filter out node_modules
    test_files = [f for f in test_files if "node_modules" not in str(f)]

    # Return relative paths for readability
    relative_paths = [str(f.relative_to(project_root)) for f in sorted(test_files)]

    if not relative_paths:
        return "No test files found."

    return f"Found {len(relative_paths)} test files:\n" + "\n".join(relative_paths)


@mcp.tool()
def read_file(file_path: str) -> str:
    """
    Read a file from the project.

    Args:
        file_path: Path to the file (relative to project root or absolute)

    Returns:
        The file contents.
    """
    project_root = get_project_root()

    # Handle both relative and absolute paths
    if os.path.isabs(file_path):
        full_path = Path(file_path)
    else:
        full_path = Path(project_root) / file_path

    if not full_path.exists():
        return f"Error: File not found: {full_path}"

    if not full_path.is_file():
        return f"Error: Not a file: {full_path}"

    try:
        content = full_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool()
def find_source_for_test(test_file_path: str) -> str:
    """
    Find the source file that a test file is testing.

    Args:
        test_file_path: Path to the test file

    Returns:
        The likely source file path, or candidates if multiple found.
    """
    project_root = get_project_root()
    test_path = Path(project_root) / test_file_path

    # Remove test suffix to find source file
    # Button.test.tsx -> Button.tsx
    # Button.spec.tsx -> Button.tsx
    source_name = re.sub(r'\.(test|spec)\.(tsx?|jsx?)$', '', test_path.name)

    # Add back extension
    possible_extensions = ['.tsx', '.ts', '.jsx', '.js']
    candidates = []

    for ext in possible_extensions:
        # Check same directory
        same_dir = test_path.parent / f"{source_name}{ext}"
        if same_dir.exists():
            candidates.append(str(same_dir.relative_to(project_root)))

        # Check parent directory (for __tests__ folders)
        parent_dir = test_path.parent.parent / f"{source_name}{ext}"
        if parent_dir.exists():
            candidates.append(str(parent_dir.relative_to(project_root)))

    if not candidates:
        return f"Could not find source file for {test_file_path}. Expected something like {source_name}.tsx"

    if len(candidates) == 1:
        return f"Source file: {candidates[0]}"

    return "Multiple candidates found:\n" + "\n".join(candidates)


@mcp.tool()
def analyze_test_patterns(sample_count: int = 5) -> str:
    """
    Deeply analyze existing tests to understand the testing patterns used.

    This reads test files and extracts DETAILED patterns including:
    - Import patterns and order
    - Describe/it/test naming conventions
    - AAA pattern usage
    - Mocking patterns
    - Assertion styles
    - Actual code examples

    IMPORTANT: Claude should use this to understand and replicate
    the EXACT style used in this codebase.

    Args:
        sample_count: Number of test files to sample (default 5)

    Returns:
        Comprehensive analysis with real code examples.
    """
    project_root = get_project_root()

    # Find test files
    test_patterns = ["**/*.test.tsx", "**/*.test.ts", "**/*.test.jsx", "**/*.test.js"]
    test_files = []
    for pattern in test_patterns:
        test_files.extend(Path(project_root).glob(pattern))

    test_files = [f for f in test_files if "node_modules" not in str(f)]

    if not test_files:
        return "No test files found to analyze. Use get_test_template() for canonical examples."

    # Get most recent files (likely most up-to-date style)
    test_files = sorted(test_files, key=lambda x: x.stat().st_mtime, reverse=True)
    sample = test_files[:sample_count]

    analysis = {
        "files_analyzed": [],
        "import_patterns": [],
        "test_structure": set(),
        "describe_naming": [],
        "it_naming": [],
        "mocking_patterns": set(),
        "common_utilities": set(),
        "assertion_patterns": set(),
        "uses_aaa_comments": False,
        "beforeEach_usage": False,
        "afterEach_usage": False,
        "example_imports": "",
        "example_describe": "",
        "example_it": "",
    }

    for test_file in sample:
        try:
            content = test_file.read_text(encoding="utf-8")
            relative_path = str(test_file.relative_to(project_root))
            analysis["files_analyzed"].append(relative_path)

            lines = content.split('\n')

            # Extract import section
            import_lines = []
            for line in lines:
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_lines.append(line)
                elif import_lines and not line.strip():
                    continue
                elif import_lines:
                    break
            if import_lines and not analysis["example_imports"]:
                analysis["example_imports"] = '\n'.join(import_lines[:10])

            # Detect import patterns
            if "@testing-library/react" in content:
                analysis["import_patterns"].append("@testing-library/react")
            if "@testing-library/user-event" in content:
                analysis["import_patterns"].append("@testing-library/user-event")
            if "@testing-library/jest-dom" in content:
                analysis["import_patterns"].append("@testing-library/jest-dom")

            # Detect common utilities
            for util in ["render", "screen", "fireEvent", "userEvent", "waitFor", "act", "within"]:
                if util in content:
                    analysis["common_utilities"].add(util)

            # Detect test structure
            if "describe(" in content and "it(" in content:
                analysis["test_structure"].add("describe + it")
            if "describe(" in content and "test(" in content:
                analysis["test_structure"].add("describe + test")
            if re.search(r'^test\(', content, re.MULTILINE):
                analysis["test_structure"].add("standalone test()")

            # Extract describe naming examples
            describe_matches = re.findall(r"describe\s*\(\s*['\"]([^'\"]+)['\"]", content)
            analysis["describe_naming"].extend(describe_matches[:3])

            # Extract it/test naming examples
            it_matches = re.findall(r"it\s*\(\s*['\"]([^'\"]+)['\"]", content)
            analysis["it_naming"].extend(it_matches[:5])
            test_matches = re.findall(r"test\s*\(\s*['\"]([^'\"]+)['\"]", content)
            analysis["it_naming"].extend(test_matches[:5])

            # Check for AAA comments
            if re.search(r'//\s*(Arrange|Act|Assert)', content):
                analysis["uses_aaa_comments"] = True

            # Detect setup/teardown
            if "beforeEach(" in content:
                analysis["beforeEach_usage"] = True
            if "afterEach(" in content:
                analysis["afterEach_usage"] = True

            # Detect mocking patterns
            if "jest.mock(" in content:
                analysis["mocking_patterns"].add("jest.mock() - module mocking")
            if "jest.fn()" in content:
                analysis["mocking_patterns"].add("jest.fn() - function mocks")
            if "jest.spyOn(" in content:
                analysis["mocking_patterns"].add("jest.spyOn() - spy on methods")
            if "mockImplementation" in content:
                analysis["mocking_patterns"].add("mockImplementation()")
            if "mockResolvedValue" in content:
                analysis["mocking_patterns"].add("mockResolvedValue() - async mocks")
            if "mockReturnValue" in content:
                analysis["mocking_patterns"].add("mockReturnValue()")

            # Detect assertion patterns
            if "toBeInTheDocument" in content:
                analysis["assertion_patterns"].add("toBeInTheDocument()")
            if "toHaveBeenCalled" in content:
                analysis["assertion_patterns"].add("toHaveBeenCalled()")
            if "toHaveBeenCalledWith" in content:
                analysis["assertion_patterns"].add("toHaveBeenCalledWith()")
            if "toEqual" in content:
                analysis["assertion_patterns"].add("toEqual()")
            if "toBe(" in content:
                analysis["assertion_patterns"].add("toBe()")
            if "toMatchSnapshot" in content:
                analysis["assertion_patterns"].add("toMatchSnapshot()")
            if "toThrow" in content:
                analysis["assertion_patterns"].add("toThrow()")

            # Extract a full describe block example
            if not analysis["example_describe"]:
                describe_match = re.search(
                    r"(describe\s*\(['\"][^'\"]+['\"],\s*\(\)\s*=>\s*\{[\s\S]*?^\});)",
                    content,
                    re.MULTILINE
                )
                if describe_match:
                    example = describe_match.group(1)
                    if len(example) < 1500:  # Not too long
                        analysis["example_describe"] = example

            # Extract an it block example
            if not analysis["example_it"]:
                it_match = re.search(
                    r"(it\s*\(['\"][^'\"]+['\"],\s*(?:async\s*)?\(\)\s*=>\s*\{[\s\S]*?^\s*\});)",
                    content,
                    re.MULTILINE
                )
                if it_match:
                    example = it_match.group(1)
                    if len(example) < 800:  # Not too long
                        analysis["example_it"] = example

        except Exception:
            continue

    # Format output
    output = [
        "# 🔬 DEEP TEST PATTERN ANALYSIS",
        "",
        "**IMPORTANT: Claude MUST follow these patterns exactly when writing tests.**",
        "",
        f"## Files Analyzed: {len(analysis['files_analyzed'])}",
    ]
    for f in analysis["files_analyzed"]:
        output.append(f"  - `{f}`")
    output.append("")

    # Test structure
    output.append("## Test Structure")
    output.append(f"- **Pattern Used:** `{' / '.join(analysis['test_structure']) or 'Unknown'}`")
    output.append(f"- **Uses AAA Comments:** `{analysis['uses_aaa_comments']}`")
    output.append(f"- **Uses beforeEach:** `{analysis['beforeEach_usage']}`")
    output.append(f"- **Uses afterEach:** `{analysis['afterEach_usage']}`")
    output.append("")

    # Naming conventions
    output.append("## Naming Conventions")
    output.append("**describe() names used:**")
    for name in list(set(analysis["describe_naming"]))[:5]:
        output.append(f"  - `{name}`")
    output.append("")
    output.append("**it()/test() names used:**")
    for name in list(set(analysis["it_naming"]))[:8]:
        output.append(f"  - `{name}`")
    output.append("")

    # Imports
    output.append("## Import Patterns")
    output.append("**Libraries used:**")
    for lib in set(analysis["import_patterns"]):
        output.append(f"  - `{lib}`")
    output.append("")
    output.append("**Common utilities:**")
    output.append(f"  `{', '.join(sorted(analysis['common_utilities']))}`")
    output.append("")

    if analysis["example_imports"]:
        output.append("**Example import block:**")
        output.append("```typescript")
        output.append(analysis["example_imports"])
        output.append("```")
        output.append("")

    # Mocking
    output.append("## Mocking Patterns")
    for mock in analysis["mocking_patterns"]:
        output.append(f"  - `{mock}`")
    output.append("")

    # Assertions
    output.append("## Assertion Patterns")
    for assertion in analysis["assertion_patterns"]:
        output.append(f"  - `{assertion}`")
    output.append("")

    # Real examples
    if analysis["example_it"]:
        output.append("## Real Example: it() block from codebase")
        output.append("```typescript")
        output.append(analysis["example_it"])
        output.append("```")
        output.append("")

    output.append("---")
    output.append("**Use these exact patterns when writing new tests.**")

    return "\n".join(output)


# ============================================================
# SECTION 2: RUNNING TOOLS
# These tools execute Jest and return results
# ============================================================

@mcp.tool()
def run_tests(
    test_path: str = "",
    test_name_pattern: str = "",
    coverage: bool = False,
    watch: bool = False
) -> str:
    """
    Run Jest tests.

    Args:
        test_path: Specific test file or directory to run (optional)
        test_name_pattern: Only run tests matching this pattern (optional)
        coverage: Include coverage report (default False)
        watch: Run in watch mode (default False, usually False for MCP)

    Returns:
        Test results including passes, failures, and error messages.
    """
    project_root = get_project_root()

    # Build the Jest command
    cmd = ["npm", "test", "--"]

    if test_path:
        cmd.append(test_path)

    if test_name_pattern:
        cmd.extend(["-t", test_name_pattern])

    if coverage:
        cmd.append("--coverage")

    if not watch:
        cmd.append("--watchAll=false")

    # Add verbose output for better error messages
    cmd.append("--verbose")

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        output = result.stdout + "\n" + result.stderr

        # Add summary at the top
        if result.returncode == 0:
            return "✅ All tests passed!\n\n" + output
        else:
            return "❌ Some tests failed!\n\n" + output

    except subprocess.TimeoutExpired:
        return "Error: Tests timed out after 2 minutes"
    except Exception as e:
        return f"Error running tests: {e}"


@mcp.tool()
def run_single_test(test_file: str, test_name: str = "") -> str:
    """
    Run a single test file with detailed output.

    Args:
        test_file: Path to the test file
        test_name: Specific test name to run (optional)

    Returns:
        Detailed test results.
    """
    return run_tests(test_path=test_file, test_name_pattern=test_name)


# ============================================================
# SECTION 3: WRITING TOOLS
# These tools let Claude write and update tests
# ============================================================

@mcp.tool()
def write_test_file(file_path: str, content: str) -> str:
    """
    Write a test file.

    Args:
        file_path: Path where to write the test (relative to project root)
        content: The test file content

    Returns:
        Success or error message.
    """
    project_root = get_project_root()
    full_path = Path(project_root) / file_path

    # Safety check: only allow test files
    if not any(pattern in file_path for pattern in ['.test.', '.spec.']):
        return "Error: Can only write test files (.test.* or .spec.*)"

    # Safety check: don't write outside project
    try:
        full_path.resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return "Error: Cannot write outside project directory"

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        full_path.write_text(content, encoding="utf-8")
        return f"✅ Successfully wrote test file: {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


@mcp.tool()
def update_test_section(
    file_path: str,
    old_content: str,
    new_content: str
) -> str:
    """
    Update a specific section of a test file.

    Args:
        file_path: Path to the test file
        old_content: The exact content to replace
        new_content: The new content

    Returns:
        Success or error message.
    """
    project_root = get_project_root()
    full_path = Path(project_root) / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        content = full_path.read_text(encoding="utf-8")

        if old_content not in content:
            return "Error: Could not find the content to replace. Make sure it matches exactly."

        updated_content = content.replace(old_content, new_content, 1)
        full_path.write_text(updated_content, encoding="utf-8")

        return f"✅ Successfully updated: {file_path}"
    except Exception as e:
        return f"Error updating file: {e}"


# ============================================================
# SECTION 4: UTILITY TOOLS
# ============================================================

@mcp.tool()
def get_jest_config() -> str:
    """
    Get the Jest configuration for the project.

    Returns:
        Jest configuration details.
    """
    project_root = get_project_root()

    config_files = [
        "jest.config.js",
        "jest.config.ts",
        "jest.config.json",
        "jest.config.mjs",
    ]

    for config_file in config_files:
        config_path = Path(project_root) / config_file
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")
            return f"Found {config_file}:\n\n{content}"

    # Check package.json for jest config
    package_json_path = Path(project_root) / "package.json"
    if package_json_path.exists():
        try:
            package_data = json.loads(package_json_path.read_text())
            if "jest" in package_data:
                return "Jest config in package.json:\n\n" + json.dumps(package_data["jest"], indent=2)
        except json.JSONDecodeError:
            pass

    return "No Jest configuration file found. Using default Jest config."


@mcp.tool()
def list_project_structure(directory: str = "src", max_depth: int = 3) -> str:
    """
    List the project structure to understand the codebase layout.

    Args:
        directory: Starting directory (default "src")
        max_depth: Maximum depth to traverse (default 3)

    Returns:
        Tree-like structure of the project.
    """
    project_root = get_project_root()
    start_path = Path(project_root) / directory

    if not start_path.exists():
        return f"Directory not found: {directory}"

    def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list:
        if depth >= max_depth:
            return []

        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = []

        for i, item in enumerate(items):
            if item.name in ["node_modules", ".git", "__pycache__", ".venv"]:
                continue

            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            lines.append(f"{prefix}{current_prefix}{item.name}")

            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                lines.extend(build_tree(item, next_prefix, depth + 1))

        return lines

    tree_lines = [directory + "/"] + build_tree(start_path)
    return "\n".join(tree_lines)


# ============================================================
# SECTION 5: CONSISTENCY ENFORCEMENT TOOLS
# These tools ensure all developers write tests the same way
# ============================================================

@mcp.tool()
def get_test_style_guide() -> str:
    """
    Get the team's official test writing guidelines.

    IMPORTANT: Claude should ALWAYS call this tool before writing any test
    to ensure consistency across all developers.

    Returns:
        The team's test style guide with explicit rules to follow.
    """
    config = load_config()
    style = config.get("style_guide", {})

    guide = [
        "# 📋 TEAM TEST STYLE GUIDE",
        "",
        "**IMPORTANT: Follow these rules exactly for consistency across all developers.**",
        "",
        "## Structure",
        f"- **Test Structure:** Use `{style.get('test_structure', 'describe + it')}`",
        f"- **it() Naming:** `{style.get('it_naming', 'should + verb')}` (e.g., `it('should render button')`)",
        f"- **describe() Naming:** `{style.get('describe_naming', 'component/function name')}`",
        "",
        "## Code Organization",
        f"- **Test Arrangement:** `{style.get('arrangement', 'AAA (Arrange-Act-Assert)')}`",
        f"- **Use AAA Comments:** `{style.get('comments', True)}`",
        f"- **Imports Order:** `{' → '.join(style.get('imports_order', []))}`",
        f"- **Mock Location:** `{style.get('mock_location', 'top of file after imports')}`",
        "",
        "## Test Quality",
        f"- **Assertions per Test:** `{style.get('assertions_per_test', '1-3 related assertions')}`",
        f"- **Required Edge Cases:** `{', '.join(style.get('edge_cases_required', []))}`",
        "",
        "## Example Naming:",
        "```javascript",
        "// ✅ CORRECT",
        "describe('Button', () => {",
        "  it('should render with default props', () => { ... });",
        "  it('should call onClick when clicked', () => { ... });",
        "  it('should be disabled when disabled prop is true', () => { ... });",
        "});",
        "",
        "// ❌ INCORRECT",
        "describe('Button tests', () => {",
        "  it('renders', () => { ... });",
        "  it('click works', () => { ... });",
        "  test('disabled', () => { ... });",
        "});",
        "```",
        "",
        "## Example Structure:",
        "```javascript",
        "it('should handle form submission', async () => {",
        "  // Arrange",
        "  const mockSubmit = jest.fn();",
        "  render(<Form onSubmit={mockSubmit} />);",
        "",
        "  // Act",
        "  await userEvent.click(screen.getByRole('button', { name: 'Submit' }));",
        "",
        "  // Assert",
        "  expect(mockSubmit).toHaveBeenCalledTimes(1);",
        "});",
        "```",
    ]

    # Add custom rules if present
    custom_rules = style.get('custom_rules', [])
    if custom_rules:
        guide.append("")
        guide.append("## Custom Team Rules")
        for rule in custom_rules:
            guide.append(f"- {rule}")

    return "\n".join(guide)


@mcp.tool()
def get_test_template(
    template_type: str,
    component_name: str = ""
) -> str:
    """
    Get a canonical test template for a specific type of code.

    IMPORTANT: Use this template as the exact structure when writing tests.
    This ensures consistency across all developers.

    Args:
        template_type: Type of template needed. Options:
                      - "react_component" (for React components)
                      - "hook" (for React hooks)
                      - "utility_function" (for utility/helper functions)
                      - "api_service" (for API/service functions)
        component_name: Name of the component/function to test (optional)

    Returns:
        A ready-to-use test template following team standards.
    """
    config = load_config()
    templates = config.get("templates", {})

    available_types = list(templates.keys())

    if template_type not in templates:
        return f"Error: Unknown template type '{template_type}'. Available types: {', '.join(available_types)}"

    template = templates[template_type]

    # Replace placeholder names if component_name provided
    if component_name:
        template = template.replace("ComponentName", component_name)
        template = template.replace("useHookName", component_name)
        template = template.replace("functionName", component_name)
        template = template.replace("apiFunction", component_name)

    header = [
        f"# 📄 TEST TEMPLATE: {template_type.upper().replace('_', ' ')}",
        "",
        "**Use this exact structure for consistency.**",
        f"**Component/Function:** {component_name or '[Replace with actual name]'}",
        "",
        "---",
        "",
    ]

    return "\n".join(header) + template


@mcp.tool()
def validate_test_style(test_file_path: str) -> str:
    """
    Validate that a test file follows the team's style guide.

    Use this AFTER writing a test to ensure it meets team standards.

    Args:
        test_file_path: Path to the test file to validate

    Returns:
        Validation results with pass/fail for each rule.
    """
    project_root = get_project_root()
    full_path = Path(project_root) / test_file_path

    if not full_path.exists():
        return f"Error: File not found: {test_file_path}"

    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"

    config = load_config()
    rules = config.get("validation_rules", [])

    results = []
    passed = 0
    failed = 0
    warnings = 0

    results.append("# 🔍 TEST STYLE VALIDATION REPORT")
    results.append(f"**File:** {test_file_path}")
    results.append("")
    results.append("## Results")
    results.append("")

    for rule in rules:
        rule_id = rule.get("id", "unknown")
        description = rule.get("description", "")
        pattern = rule.get("pattern", "")
        must_not_match = rule.get("must_not_match", False)
        is_warning = rule.get("warning", False)

        if not pattern:
            continue

        try:
            matches = bool(re.search(pattern, content, re.MULTILINE | re.IGNORECASE))

            if must_not_match:
                # Rule passes if pattern is NOT found
                if matches:
                    failed += 1
                    results.append(f"❌ **FAIL:** {description}")
                else:
                    passed += 1
                    results.append(f"✅ **PASS:** {description}")
            else:
                # Rule passes if pattern IS found
                if matches:
                    passed += 1
                    results.append(f"✅ **PASS:** {description}")
                else:
                    if is_warning:
                        warnings += 1
                        results.append(f"⚠️ **WARN:** {description}")
                    else:
                        failed += 1
                        results.append(f"❌ **FAIL:** {description}")
        except re.error:
            results.append(f"⚠️ **SKIP:** Invalid pattern for {rule_id}")

    results.append("")
    results.append("## Summary")
    results.append(f"- ✅ Passed: {passed}")
    results.append(f"- ❌ Failed: {failed}")
    results.append(f"- ⚠️ Warnings: {warnings}")

    if failed == 0:
        results.append("")
        results.append("🎉 **Test file meets all style requirements!**")
    else:
        results.append("")
        results.append("⚠️ **Please fix the failed rules before committing.**")

    return "\n".join(results)


@mcp.tool()
def init_style_config() -> str:
    """
    Initialize a .jest-helper.json configuration file in the project.

    This creates a customizable config file that teams can modify
    to enforce their specific testing standards.

    Returns:
        Success message with the config file path.
    """
    project_root = get_project_root()
    config_path = Path(project_root) / ".jest-helper.json"

    if config_path.exists():
        return f"Config file already exists at: {config_path}\n\nEdit this file to customize your team's test standards."

    # Create a simplified config for users to customize
    user_config = {
        "style_guide": {
            "test_structure": "describe + it",
            "it_naming": "should + verb",
            "describe_naming": "component/function name",
            "arrangement": "AAA (Arrange-Act-Assert)",
            "comments": True,
            "imports_order": ["react", "testing-library", "components", "utils", "mocks"],
            "mock_location": "top of file after imports",
            "assertions_per_test": "1-3 related assertions",
            "edge_cases_required": ["null/undefined", "empty values", "error states"],
            "custom_rules": [
                "Always mock API calls",
                "Use data-testid only as last resort"
            ]
        },
        "validation_rules": [
            {"id": "has_describe", "description": "Test must use describe() blocks", "pattern": "describe\\s*\\("},
            {"id": "has_it_or_test", "description": "Test must use it() or test()", "pattern": "(it|test)\\s*\\("},
            {"id": "it_uses_should", "description": "it() should start with 'should'", "pattern": "it\\s*\\(\\s*['\"]should"},
            {"id": "has_assertions", "description": "Test must have assertions", "pattern": "expect\\s*\\("},
            {"id": "has_aaa_comments", "description": "Test should have AAA comments", "pattern": "//\\s*(Arrange|Act|Assert)", "warning": True},
            {"id": "no_only", "description": "No .only() in tests", "pattern": "\\.(only|skip)\\s*\\(", "must_not_match": True}
        ]
    }

    try:
        with open(config_path, 'w') as f:
            json.dump(user_config, f, indent=2)
        return f"""✅ Created config file: {config_path}

This file controls how tests are written across your team.

**What to customize:**
1. `style_guide` - Define your naming conventions and structure
2. `validation_rules` - Add/modify rules for test validation
3. `custom_rules` - Add team-specific guidelines

**Next steps:**
1. Edit .jest-helper.json to match your team's preferences
2. Commit this file to your repo so all devs use the same config
3. Claude will now follow these rules when writing tests"""
    except Exception as e:
        return f"Error creating config file: {e}"


@mcp.tool()
def get_example_tests(count: int = 2) -> str:
    """
    Get example test code snippets from the project's existing tests.

    This provides REAL examples from your codebase that Claude should follow
    when writing new tests, ensuring consistency with existing patterns.

    Args:
        count: Number of example test files to extract snippets from (default 2)

    Returns:
        Real code examples showing the team's actual testing patterns.
    """
    project_root = get_project_root()

    # Find test files
    test_patterns = ["**/*.test.tsx", "**/*.test.ts", "**/*.test.jsx", "**/*.test.js"]
    test_files = []
    for pattern in test_patterns:
        test_files.extend(Path(project_root).glob(pattern))

    test_files = [f for f in test_files if "node_modules" not in str(f)]

    if not test_files:
        return "No existing test files found. Use get_test_template() instead for canonical examples."

    # Get the most recently modified test files
    test_files = sorted(test_files, key=lambda x: x.stat().st_mtime, reverse=True)
    sample = test_files[:count]

    output = [
        "# 📚 REAL EXAMPLES FROM YOUR CODEBASE",
        "",
        "**Follow these patterns exactly when writing new tests.**",
        "",
    ]

    for test_file in sample:
        try:
            content = test_file.read_text(encoding="utf-8")
            relative_path = str(test_file.relative_to(project_root))

            # Extract meaningful snippets
            lines = content.split('\n')

            output.append(f"## Example: `{relative_path}`")
            output.append("")
            output.append("```typescript")

            # Try to extract just the first describe block if file is large
            if len(lines) > 80:
                # Find first describe and its content
                in_describe = False
                brace_count = 0
                snippet_lines = []

                for line in lines:
                    if 'describe(' in line or 'describe (' in line:
                        in_describe = True

                    if in_describe:
                        snippet_lines.append(line)
                        brace_count += line.count('{') - line.count('}')

                        if brace_count <= 0 and len(snippet_lines) > 5:
                            break

                        if len(snippet_lines) > 50:
                            snippet_lines.append("  // ... more tests ...")
                            snippet_lines.append("});")
                            break

                output.extend(snippet_lines[:60])
            else:
                output.extend(lines)

            output.append("```")
            output.append("")

        except Exception as e:
            output.append(f"Error reading {test_file}: {e}")
            output.append("")

    return "\n".join(output)


# ============================================================
# RUN THE SERVER
# ============================================================
if __name__ == "__main__":
    mcp.run(transport='stdio')
