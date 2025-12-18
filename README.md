# Jest Helper MCP Server

An MCP (Model Context Protocol) server that enables Claude to write **consistent, team-standard test cases** across all developers. Designed for enterprise environments using Claude with Bedrock in DevSpaces.

## The Problem This Solves

When multiple developers use AI to write tests:
- Different developers ask questions differently
- Each session may produce different formats
- No enforcement of team standards
- Inconsistent test quality across the codebase

## The Solution

This MCP provides:
1. **Explicit style guides** that Claude follows
2. **Canonical templates** for different test types
3. **Deep pattern analysis** from existing tests
4. **Validation tools** to ensure compliance
5. **Team-customizable configuration** via `.jest-helper.json`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude (via Bedrock)                        │
│                                                                 │
│  "Write a test for UserProfile component"                       │
│                                                                 │
│  1. get_test_style_guide()    → Load team standards             │
│  2. get_test_template()       → Get canonical structure         │
│  3. analyze_test_patterns()   → Study existing tests            │
│  4. read_file("UserProfile")  → Understand the component        │
│  5. write_test_file()         → Write test in YOUR style        │
│  6. validate_test_style()     → Verify it meets standards       │
│  7. run_tests()               → Confirm it works                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Jest MCP Server (Tools)                      │
│                                                                 │
│  CONSISTENCY TOOLS          READ TOOLS         WRITE TOOLS      │
│  ─────────────────          ──────────         ───────────      │
│  • get_test_style_guide     • find_test_files  • write_test_file│
│  • get_test_template        • read_file        • update_section │
│  • validate_test_style      • analyze_patterns                  │
│  • init_style_config        • get_example_tests                 │
│  • get_example_tests        • get_jest_config                   │
│                                                                 │
│  RUN TOOLS                  UTILITY TOOLS                       │
│  ─────────                  ─────────────                       │
│  • run_tests                • list_project_structure            │
│  • run_single_test          • find_source_for_test              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tools Reference

### Consistency Enforcement Tools (NEW)

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `get_test_style_guide` | Returns team's test writing rules | **Before** writing any test |
| `get_test_template` | Returns canonical test templates | When creating new test files |
| `validate_test_style` | Checks if test follows standards | **After** writing a test |
| `init_style_config` | Creates `.jest-helper.json` config | First-time setup |
| `get_example_tests` | Extracts real examples from codebase | Learning existing patterns |

### Reading Tools

| Tool | Purpose |
|------|---------|
| `find_test_files` | Lists all test files in project |
| `read_file` | Reads any file content |
| `find_source_for_test` | Maps test → source file |
| `analyze_test_patterns` | Deep analysis of existing test patterns |
| `get_jest_config` | Reads Jest configuration |
| `list_project_structure` | Shows folder structure |

### Writing Tools

| Tool | Purpose | Safety |
|------|---------|--------|
| `write_test_file` | Creates/overwrites test | Only `.test.*` or `.spec.*` files |
| `update_test_section` | Edits part of a test | Surgical updates only |

### Running Tools

| Tool | Purpose |
|------|---------|
| `run_tests` | Runs Jest with options |
| `run_single_test` | Runs specific test file |

---

## Quick Start

### 1. Install

```bash
# Clone/download the project
cd jest-helper

# Install dependencies
uv sync
```

### 2. Add to Claude Code CLI

```bash
claude mcp add jest-helper \
  -e PROJECT_ROOT=/path/to/your/react/project \
  -- uv --directory /path/to/jest-helper run jest_helper.py
```

### 3. Initialize Team Config (Optional but Recommended)

Ask Claude: "Initialize the jest-helper config for our team"

This creates `.jest-helper.json` in your project root.

---

## Team Configuration

### The `.jest-helper.json` File

Create this file in your project root to enforce team standards:

```json
{
  "style_guide": {
    "test_structure": "describe + it",
    "it_naming": "should + verb",
    "describe_naming": "component/function name",
    "arrangement": "AAA (Arrange-Act-Assert)",
    "comments": true,
    "imports_order": ["react", "testing-library", "components", "utils", "mocks"],
    "mock_location": "top of file after imports",
    "assertions_per_test": "1-3 related assertions",
    "edge_cases_required": ["null/undefined", "empty values", "error states"],
    "custom_rules": [
      "Always mock API calls",
      "Use data-testid only as last resort",
      "Prefer userEvent over fireEvent"
    ]
  },
  "validation_rules": [
    {"id": "has_describe", "description": "Test must use describe() blocks", "pattern": "describe\\s*\\("},
    {"id": "it_uses_should", "description": "it() should start with 'should'", "pattern": "it\\s*\\(\\s*['\"]should"},
    {"id": "has_aaa_comments", "description": "Test should have AAA comments", "pattern": "//\\s*(Arrange|Act|Assert)", "warning": true},
    {"id": "no_only", "description": "No .only() in tests", "pattern": "\\.(only|skip)\\s*\\(", "must_not_match": true}
  ]
}
```

### Customization Options

**Style Guide Fields:**
- `test_structure`: "describe + it" | "describe + test" | "standalone test()"
- `it_naming`: Convention for it() names (e.g., "should + verb")
- `arrangement`: Test structure pattern (AAA recommended)
- `custom_rules`: Array of team-specific rules as strings

**Validation Rules:**
- `pattern`: Regex pattern to match
- `must_not_match`: Set to `true` if pattern should NOT be found
- `warning`: Set to `true` for non-blocking warnings

---

## How Consistency is Enforced

### Workflow for Every Developer

```
Developer asks: "Write a test for Button.tsx"

Claude automatically:
1. Calls get_test_style_guide() → Loads team rules
2. Calls get_test_template("react_component", "Button") → Gets template
3. Calls analyze_test_patterns() → Studies existing tests
4. Reads Button.tsx → Understands the component
5. Writes test following ALL the above
6. Calls validate_test_style() → Ensures compliance
7. Runs test → Confirms it works
```

### Result: Same Output Regardless of Developer

**Developer A asks:** "Write a test for Button"
**Developer B asks:** "Create unit tests for the Button component"
**Developer C asks:** "I need tests for Button.tsx please"

**All get the same structured output because:**
- Same style guide is loaded
- Same template is used
- Same validation is applied

---

## Templates Available

### React Component (`react_component`)
```typescript
describe('ComponentName', () => {
  describe('rendering', () => {
    it('should render without crashing', () => {
      // Arrange, Act, Assert...
    });
  });
  describe('interactions', () => { ... });
  describe('edge cases', () => { ... });
});
```

### React Hook (`hook`)
```typescript
describe('useHookName', () => {
  describe('initialization', () => { ... });
  describe('actions', () => { ... });
});
```

### Utility Function (`utility_function`)
```typescript
describe('functionName', () => {
  describe('valid inputs', () => { ... });
  describe('edge cases', () => { ... });
  describe('error cases', () => { ... });
});
```

### API Service (`api_service`)
```typescript
describe('apiFunction', () => {
  beforeEach(() => { jest.clearAllMocks(); });
  describe('successful requests', () => { ... });
  describe('error handling', () => { ... });
});
```

---

## DevSpaces Integration

### For Red Hat DevSpaces / Che

1. Add the MCP configuration to your devfile or workspace config
2. Ensure `.jest-helper.json` is committed to your repo
3. All developers automatically get the same config

### Environment Variable

Set `PROJECT_ROOT` to point to your React project:

```bash
export PROJECT_ROOT=/projects/your-react-app
```

---

## Safety Features

```python
# Can only write test files
if not any(pattern in file_path for pattern in ['.test.', '.spec.']):
    return "Error: Can only write test files"

# Can't write outside project
full_path.resolve().relative_to(Path(project_root).resolve())
```

---

## Example Usage

### Ask Claude to write a test:

```
"Write a test for the UserProfile component"
```

### Claude's workflow:

1. **Loads style guide** → Knows to use "describe + it", AAA comments
2. **Gets template** → Uses react_component template structure
3. **Analyzes existing tests** → Sees team uses userEvent, not fireEvent
4. **Reads component** → Understands props and behavior
5. **Writes test** → Following all patterns
6. **Validates** → Confirms it meets all rules
7. **Runs test** → Ensures it passes

### Output is consistent every time, for every developer.

---

## Validation Report Example

```
# 🔍 TEST STYLE VALIDATION REPORT
**File:** src/components/Button.test.tsx

## Results

✅ **PASS:** Test must use describe() blocks
✅ **PASS:** Test must use it() or test()
✅ **PASS:** it() should start with 'should'
✅ **PASS:** Test must have assertions
⚠️ **WARN:** Test should have AAA comments
✅ **PASS:** No .only() in tests

## Summary
- ✅ Passed: 5
- ❌ Failed: 0
- ⚠️ Warnings: 1

🎉 **Test file meets all style requirements!**
```

---

## License

MIT
