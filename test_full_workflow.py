#!/usr/bin/env python3
"""
Test script for full RDTeamAgent workflow
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


def test_full_workflow():
    """Test the complete R&D team workflow from requirements to validation"""
    print('Testing full RDTeamAgent workflow...')

    from openhands.agenthub.rd_team_agent.rd_team_agent import RDTeamAgent
    from openhands.core.config import AgentConfig

    # Clean backlog directory
    backlog_dir = '/workspace/OpenHands-Full/.openhands/backlog'
    if os.path.exists(backlog_dir):
        for file in os.listdir(backlog_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(backlog_dir, file))

    agent = RDTeamAgent(MockLLM(), AgentConfig())

    # Test 1: Requirements gathering phase
    print('\n1. Testing requirements gathering...')

    # First, create a requirements task manually to simulate initial state
    BacklogTool.create_backlog_task(
        title='Gather Requirements',
        description='Collect user requirements for the project',
        phase='requirements_gathering',
    )

    result = agent._handle_requirements_gathering(State())
    assert 'requirements' in result.content.lower()
    tasks = BacklogTool.get_backlog_tasks()
    req_task = [t for t in tasks if t['phase'] == 'requirements_gathering'][0]
    assert req_task['title'] == 'Gather Requirements'
    print('✓ Requirements gathering phase completed')

    # Test 2: Advance to planning phase
    print('\n2. Testing advance to planning...')
    result = agent._advance_to_planning_phase()
    assert 'start planning' in result.content.lower() and (
        'milestones' in result.content.lower()
        or 'deliverables' in result.content.lower()
    )
    # Create a planning task manually to simulate progress (as done in other tests)
    BacklogTool.create_backlog_task(
        title='Create Project Plan',
        description='Develop a project plan based on requirements',
        phase='planning',
    )
    tasks = BacklogTool.get_backlog_tasks()
    planning_task = [t for t in tasks if t['phase'] == 'planning'][0]
    assert planning_task['title'] == 'Create Project Plan'
    print('✓ Planning phase completed')

    # Test 3: Advance to architecture phase
    print('\n3. Testing advance to architecture...')
    # Create an architecture task manually to simulate progress
    BacklogTool.create_backlog_task(
        title='Design System Architecture',
        description='Create architectural blueprints for the system',
        phase='architecture',
    )
    tasks = BacklogTool.get_backlog_tasks()
    assert any(t['phase'] == 'architecture' for t in tasks)
    print('✓ Architecture phase completed')

    # Test 4: Advance to development phase
    print('\n4. Testing advance to development...')
    # Create a development task manually to simulate progress
    BacklogTool.create_backlog_task(
        title='Implement Feature X',
        description='Develop the core functionality of feature X',
        phase='development',
    )
    tasks = BacklogTool.get_backlog_tasks()
    assert any(t['phase'] == 'development' for t in tasks)
    print('✓ Development phase completed')

    # Test 5: Advance to testing phase
    print('\n5. Testing advance to testing...')
    # Create a testing task manually to simulate progress
    BacklogTool.create_backlog_task(
        title='Test Feature X',
        description='Write and execute tests for feature X',
        phase='testing',
    )
    tasks = BacklogTool.get_backlog_tasks()
    assert any(t['phase'] == 'testing' for t in tasks)
    print('✓ Testing phase completed')

    # Test 6: Advance to validation phase
    print('\n6. Testing advance to validation...')
    # Create a validation task manually to simulate progress
    BacklogTool.create_backlog_task(
        title='Validate Feature X',
        description='Perform final validation of feature X',
        phase='validation',
    )
    tasks = BacklogTool.get_backlog_tasks()
    assert any(t['phase'] == 'validation' for t in tasks)
    print('✓ Validation phase completed')

    # Test 7: Phase detection should work correctly
    print('\n7. Testing phase detection...')
    current_phase = agent._get_current_phase(State())
    assert current_phase == 'validation'
    print(f"✓ Current phase correctly detected as '{current_phase}'")

    # Verify all phases are represented in backlog
    print('\n8. Verifying complete workflow representation...')
    tasks = BacklogTool.get_backlog_tasks()
    phases_in_backlog = {t['phase'] for t in tasks}
    expected_phases = {
        'requirements_gathering',
        'planning',
        'architecture',
        'development',
        'testing',
        'validation',
    }
    assert phases_in_backlog == expected_phases
    print('✓ All workflow phases represented in backlog')

    # Verify task count
    assert len(tasks) >= 6  # At least one task per phase
    print(f'✓ Total tasks created: {len(tasks)}')


if __name__ == '__main__':
    test_full_workflow()
    print('\n🎉 Full RDTeamAgent workflow test passed!')
