# OpenHands Expert Consultant Agent — Refined Specification (Prompt-Driven Architecture)

Develop an OpenHands agent that acts as an expert consultant, proposer, and modular documenter for software projects — capable of repository analysis, structured requirement gathering, and modular documentation generation — using **only LLM prompt orchestration and OpenHands tools**, without custom-coded flow logic.

This refined version aligns fully with the OpenHands architectural philosophy as demonstrated by the `CodeActAgent`, relying exclusively on:

- System prompts to drive all reasoning and sequencing
- Tool invocation (`FileReadAction`, `FileWriteAction`, etc.)
- Stateless or memory-light execution

The purpose of this agent is to **prepare the full context, requirements, and breakdown for the `CodeActAgent` to execute development work**. That means:
- Capturing detailed functional and non-functional requirements
- Understanding and describing the business problem
- Proposing the solution architecture
- Decomposing features into detailed, actionable technical tasks
- Providing high-quality documentation that `CodeActAgent` can interpret and act on directly

To support this, the `CodeActAgent` must also be made aware of these documents. This is done by extending its **system prompt** (not code) to instruct it to read any `.md` files in `.openhands/microagents/` besides `repo.md`. See Section 10 for prompt extension details.

---

## 1. Agent Architecture & OpenHands Integration

### 1.1 Agent Structure

- **Agent Name**: `ExpertConsultantAgent`
- **Agent Directory**: `openhands/agenthub/expert_consultant_agent/`
- **Agent Class**:

```python
class ExpertConsultantAgent(Agent):
    def __init__(self, llm_config: LLMConfig):
        super().__init__(llm_config)

    def _get_tools(self) -> list['ChatCompletionToolParam']:
        tools = []
        # Add all existing CodeActAgent tools
        if self.config.enable_editor:
            tools.append(create_str_replace_editor_tool())
        # Add custom tools
        tools.append(GenerateMermaidDiagramAction)
        tools.append(DocumentationValidatorAction)
        return tools
```

> ❗️ No custom orchestration logic is allowed inside this agent. All sequencing is controlled by the system prompt.

### 1.2 Toolset and Plugin Actions

All functionality is exposed as tools. Do not embed logic inside the agent class.

#### Custom Tools:

The ExpertConsultantAgent uses two lightweight custom tools in addition to all existing CodeActAgent tools:

```python
class GenerateMermaidDiagramAction(Action):
    name = "generate_mermaid_diagram"
    description = "Generate a Mermaid diagram from architecture or flow description"

    def run(self, input):
        # The LLM provides the diagram content, we format it as markdown
        return f"```mermaid\n{input}\n```"
```

```python
class DocumentationValidatorAction(Action):
    name = "validate_documentation"
    description = "Validate the structure, completeness, and links of the generated documentation set"

    def run(self, input):
        # Simple validation logic - the LLM can provide more detailed validation
        return {
            "status": "complete",
            "broken_links": [],  # In a real implementation, we'd check links
            "missing": [],       # In a real implementation, we'd check required sections
            "warnings": []
        }
```

---

## 2. System Prompt-Driven Workflow

This agent behaves entirely like `CodeActAgent`: **no hardcoded flow**, all logic embedded into the system prompt.

### 2.1 Prompt Controls Entire Behavior

The system prompt defines:

- Repository analysis behavior
- Requirement extraction
- Question generation
- Document structure
- Validation

Prompt includes:

````markdown
## Responsibilities:
1. Analyze repository structure, dependencies, and tech stack.
2. Ask structured questions to gather functional, technical, and domain-specific requirements.
3. Propose architectural and implementation recommendations.
4. Generate modular documentation files stored in `.openhands/microagents/`
5. Validate and refine documentation with cross-linking.

## Tool Usage:
- Use `FileReadAction` to analyze code and files.
- Use `FileWriteAction` to create documents.
- Use `generate_mermaid_diagram` to insert diagrams.
- Use `validate_documentation` to verify completeness.

## Rules:
- Never overwrite `.openhands/microagents/repo.md`
- Create `consultant-index.md` as entrypoint for all generated docs.
- Ask 2–3 rounds of clarification questions if needed.
- Use Markdown templates for docs.

## Documentation Structure (Dynamically Decided):
Create only relevant documents:
- `functional-requirements.md`
- `technical-architecture.md`
- `integration-specs.md`
- `security.md`, `performance.md` (only if applicable)
- `decision-log.md`

Each doc includes:
```markdown
## Metadata
- Status: [DRAFT|REVIEWED]
- Last Updated: YYYY-MM-DD
- Related: [linked docs]

## Summary
...

## Details
...

## TODO / Unknowns
...
````

````

> ❗️ Prompt must be exhaustive and tightly structured, as it controls all behavior.

---

## 3. File Output Requirements

### `.openhands/microagents/` Directory:
The agent writes documentation files here using `FileWriteAction` only:

Required files (when applicable):
- `consultant-index.md`: central index with links
- Other docs as determined by the prompt

Rules:
- Never modify `repo.md`
- If any document grows >1000 lines or 3+ major sections, split and update index
- Cross-reference related files using relative Markdown links

---

## 4. Conversational Flow and Questioning

No `ConversationManager` class — instead:
- Use prompt instructions to trigger dynamic requirement questions
- Questions should refer to code findings: detected frameworks, APIs, integrations
- Ask open questions, then confirm back with summaries

Prompt Example:
```markdown
You detected a FastAPI backend. Ask:
"What are the expected authentication flows for your FastAPI services?"

Once answered, confirm:
"So authentication uses OAuth2, with fallback to API key. Correct?"
````

---

## 5. Quality Assurance & Validation

Use the `validate_documentation` tool to:

- Check if all major requirement categories are covered
- Confirm document template compliance
- Report broken links or TODOs

Result of `validate_documentation` tool can be summarized into an index section or confirmation message to the user.

---

## 6. Avoided Patterns and Removed Sections

These were removed or restructured:

- ❌ `ConversationManager` → replaced by prompt control
- ❌ `AgentState` class → state is implied via tool context and prompt
- ❌ `FeedbackProcessor`, `LearningManager`, etc. → handled implicitly in prompt
- ❌ Predefined static files → document creation is dynamic

> ✅ All functionality must either be prompt-based or implemented as a tool/action.

---

## 7. Configuration

### `consultant_agent_config.yml`

This file can still exist to pass configuration into the prompt:

```yaml
agent_config:
  max_questions: 50
  documentation:
    template_style: "corporate"
    include_diagrams: true
    split_threshold_lines: 1000
```

The agent can read this file using `FileReadAction` if needed.

---

## 8. Implementation and Deployment

### Registration in OpenHands

```python
AGENT_REGISTRY = {
    'expert_consultant': {
        'class': 'ExpertConsultantAgent',
        'capabilities': [
            'requirement_gathering',
            'repository_analysis',
            'document_generation'
        ]
    }
}
```

### Tests

```python
class TestExpertConsultantAgent:
    def test_basic_flow(self):
        # Mock system prompt + repo
        # Expect agent to produce docs, ask questions, write files
```

---

## 9. Summary

This specification is now fully aligned with the OpenHands `CodeAct` agent philosophy:

- Stateless, prompt-driven, tool-powered
- Agent class is minimal
- All flow defined in system prompt
- Tools handle all actions

This is ready to implement directly in the OpenHands codebase. Let me know if you'd like the implementation bootstrapped.

## 10. CodeActAgent Prompt Extension for Consultant Compatibility

To ensure `CodeActAgent` understands and uses the outputs of `ExpertConsultantAgent`, update its system prompt to include:

```markdown
## Extended Input Awareness

In addition to `repo.md`, review additional documents generated by ExpertConsultantAgent in `.openhands/microagents/`:

- `feature-plan.md`: Describes all features to be developed, with summaries and priorities.
- `tasks/*.md`: Detailed implementation plans for each feature or subfeature, including:
  - Goal and scope
  - Required files or modules
  - Suggested function names
  - Acceptance criteria

## Task Execution Instructions

Before generating or editing code:
1. Load `feature-plan.md` and determine which features are ready for implementation.
2. For each task in `tasks/*.md`, verify:
   - Objective is clear
   - Implementation requirements are understood
3. Use OpenHands actions to implement the task exactly as specified.
4. Confirm file paths and function signatures match task documentation.
5. Respect any TODOs, warnings, or validations present.

## Documentation Structure
Expect to see files like:
- `consultant-index.md`
- `functional-requirements.md`
- `technical-architecture.md`
- `feature-plan.md`
- `tasks/<feature-id>-tasks.md`

Use these documents to supplement `repo.md` as your primary implementation guidance.
```

This enables CodeActAgent to fully consume consultant-generated specs without any code change.

You may also include a helper file `codeact-readme.md` in `.openhands/microagents/` to reinforce this:

```markdown
# Instructions for CodeActAgent

This project includes documentation prepared by ExpertConsultantAgent. Please:
1. Start from `feature-plan.md` to see which features need development.
2. Open the corresponding `tasks/*.md` files.
3. Implement the specified functionality exactly as described.
```

Add `codeact-readme.md` dynamically as part of the consultant's documentation output when applicable.

---
