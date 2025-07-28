

# RD Team Agent

The RDTeamAgent is a comprehensive agent that functions as a complete R&D team, covering roles like Coordinator, Product Owner, Architect, Developer, Tester, and Validator. This agent is designed to:

1. **Autonomous Operation**: Progress through phases independently
2. **Task Management**: Generate tasks in `.openhands/backlog`
3. **Validation**: Validate each phase before proceeding
4. **Test Coverage**: Ensure all components are covered by tests
5. **Agent Delegation**: Delegate implementation and testing to CodeActAgent

## Features

- **Multi-role coordination**: Handles multiple R&D roles in a single agent
- **Phase-based development**: Moves through defined phases with validation:
  - Requirements Gathering: Product Owner engages with users
  - Planning: Define project scope and milestones
  - Architecture: Design system architecture
  - Development: Delegate coding tasks to CodeActAgent
  - Testing: Delegate test creation/execution to CodeActAgent
  - Validation: Ensure quality standards before progression
- **Backlog management**: Automatically generates and manages task backlogs
- **Comprehensive testing**: Ensures test coverage for all components
- **Agent delegation**: Uses AgentDelegateAction to offload implementation tasks

## Configuration

The RDTeamAgent can be configured through standard OpenHands agent configuration mechanisms.
