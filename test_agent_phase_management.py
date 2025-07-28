#!/usr/bin/env python3

"""
Test script for RDTeamAgent phase management
"""

import os

from openhands.agenthub.rd_team_agent.tools.backlog import BacklogTool
from openhands.controller.state.state import State


# Create a minimal mock LLM and config for testing
class MockLLM:
    def __init__(self, config=None):
        pass  # Skip parent init to avoid dependency issues

    def format_messages_for_llm(self, messages):
        return messages


def test_phase_detection():
    """Test the phase detection functionality"""
    print('Testing phase detection...')
    from openhands.agenthub.rd_team_agent.rd_team_agent import RDTeamAgent
    from openhands.core.config import AgentConfig

    # Clean backlog directory
    backlog_dir = '.openhands/backlog'
    if os.path.exists(backlog_dir):
        for file in os.listdir(backlog_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(backlog_dir, file))

    agent = RDTeamAgent(MockLLM(), AgentConfig())

    # Test no tasks -> requirements_gathering
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks before phase detection: {tasks}')
    phase = agent._get_current_phase(State())
    print(f'Phase with no tasks: {phase}')
    assert phase == 'requirements_gathering'
    print('✓ No tasks -> requirements_gathering')

    # Test requirements task -> requirements_gathering
    BacklogTool.create_backlog_task(
        title='Gather Requirements',
        description='Collect user requirements for the project',
        phase='requirements_gathering',
    )
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after creating requirements task: {tasks}')
    phase = agent._get_current_phase(State())
    assert phase == 'requirements_gathering'
    print('✓ Requirements task -> requirements_gathering')

    # Test planning task -> planning
    BacklogTool.create_backlog_task(
        title='Create Project Plan',
        description='Develop a project plan based on requirements',
        phase='planning',
    )
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after creating planning task: {tasks}')
    phase = agent._get_current_phase(State())
    assert phase == 'planning'
    print('✓ Planning task -> planning')

    # Test architecture task -> architecture
    BacklogTool.create_backlog_task(
        title='Design System Architecture',
        description='Create architectural blueprints for the system',
        phase='architecture',
    )
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after creating architecture task: {tasks}')
    phase = agent._get_current_phase(State())
    assert phase == 'architecture'
    print('✓ Architecture task -> architecture')

    # Test development task -> development
    BacklogTool.create_backlog_task(
        title='Implement Feature X',
        description='Develop the core functionality of feature X',
        phase='development',
    )
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after creating development task: {tasks}')
    phase = agent._get_current_phase(State())
    assert phase == 'development'
    print('✓ Development task -> development')

    # Test testing task -> testing
    BacklogTool.create_backlog_task(
        title='Test Feature X',
        description='Write and execute tests for feature X',
        phase='testing',
    )
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after creating testing task: {tasks}')
    phase = agent._get_current_phase(State())
    assert phase == 'testing'
    print('✓ Testing task -> testing')

    # Test validation task -> validation
    BacklogTool.create_backlog_task(
        title='Validate Feature X',
        description='Perform final validation of feature X',
        phase='validation',
    )
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after creating validation task: {tasks}')
    phase = agent._get_current_phase(State())
    assert phase == 'validation'
    print('✓ Validation task -> validation')


def test_requirements_gathering():
    """Test requirements gathering functionality"""
    print('\nTesting requirements gathering...')

    # Clean backlog directory
    backlog_dir = os.path.expanduser('~/.openhands/backlog')
    if os.path.exists(backlog_dir):
        for file in os.listdir(backlog_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(backlog_dir, file))

    from openhands.agenthub.rd_team_agent.rd_team_agent import RDTeamAgent
    from openhands.core.config import AgentConfig

    agent = RDTeamAgent(MockLLM(), AgentConfig())

    # Test requirements gathering with no existing tasks
    result = agent._handle_requirements_gathering(State())
    print(f'Result: {result}')
    print(f'Result type: {type(result)}')
    if hasattr(result, 'content'):
        assert 'requirements' in result.content.lower()
        print('✓ Requirements gathering initiated')

        # Verify task was created
        tasks = BacklogTool.get_backlog_tasks()
        req_task = [t for t in tasks if t['phase'] == 'requirements_gathering'][0]
        print(f'Requirements task: {req_task}')
        assert req_task['title'] == 'Gather Requirements'
        print('✓ Requirements gathering task created')


def test_advance_to_planning():
    """Test advance to planning functionality"""
    # Clean backlog directory
    backlog_dir = os.path.expanduser('~/.openhands/backlog')
    if os.path.exists(backlog_dir):
        for file in os.listdir(backlog_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(backlog_dir, file))

    from openhands.agenthub.rd_team_agent.rd_team_agent import RDTeamAgent
    from openhands.core.config import AgentConfig

    agent = RDTeamAgent(MockLLM(), AgentConfig())

    # First create a requirements gathering task
    BacklogTool.create_backlog_task(
        title='Gather Requirements',
        description='Collect user requirements for the project',
        phase='requirements_gathering',
    )

    # Now advance to planning
    result = agent._advance_to_planning_phase()
    assert 'start planning' in result.content.lower() and (
        'milestones' in result.content.lower()
        or 'deliverables' in result.content.lower()
    )
    print(f'Planning result: {result}')
    print('✓ Planning phase initiated')

    # Verify task was created
    tasks = BacklogTool.get_backlog_tasks()
    tasks = BacklogTool.get_backlog_tasks()
    print(f'Tasks after planning: {len(tasks)}')
    for t in tasks:
        print(f'  - {t["title"]} ({t["phase"]})')
    print(f'Tasks after planning: {len(tasks)}')
    planning_task = [t for t in tasks if t['phase'] == 'planning'][0]
    assert planning_task['title'] == 'Create Project Plan'
    print('✓ Planning task created')


if __name__ == '__main__':
    test_phase_detection()
    test_requirements_gathering()
    test_advance_to_planning()

    print('\nAll phase management tests passed!')
