#!/usr/bin/env python3
"""
Test script for RDTeamAgent CodeActAgent delegation
"""

import os

from openhands.agenthub.rd_team_agent.tools.backlog import BacklogTool


def test_codeact_delegation():
    """Test that RDTeamAgent properly delegates tasks to CodeActAgent"""
    print('Testing CodeActAgent delegation...')

    from openhands.agenthub.rd_team_agent.rd_team_agent import RDTeamAgent
    from openhands.core.config import AgentConfig

    # Clean backlog directory
    backlog_dir = '/workspace/OpenHands-Full/.openhands/backlog'
    if os.path.exists(backlog_dir):
        for file in os.listdir(backlog_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(backlog_dir, file))

    # Create a mock LLM
    class MockLLM:
        def __init__(self, config=None):
            pass

        def format_messages_for_llm(self, messages):
            return messages

    agent = RDTeamAgent(MockLLM(), AgentConfig())

    # Test 1: Development phase delegation
    print('\n1. Testing development phase delegation...')
    BacklogTool.create_backlog_task(
        title='Implement Feature X',
        description='Develop the core functionality of feature X',
        phase='development',
    )

    action = agent._handle_development_phase(None)  # None for state since we're mocking
    print(f'Action type: {type(action)}')
    print(f'Action content: {action}')

    from openhands.events.action.agent import AgentDelegateAction

    assert isinstance(action, AgentDelegateAction)
    assert action.agent == 'codeact_agent'
    assert 'Implement Feature X' in str(action.inputs.get('title', ''))
    print('✓ Development phase correctly delegates to CodeActAgent')

    # Test 2: Testing phase delegation
    print('\n2. Testing testing phase delegation...')
    BacklogTool.create_backlog_task(
        title='Test Feature X',
        description='Write and execute tests for feature X',
        phase='testing',
    )

    action = agent._handle_testing_phase(None)  # None for state since we're mocking
    print(f'Action type: {type(action)}')
    print(f'Action content: {action}')

    assert isinstance(action, AgentDelegateAction)
    assert action.agent == 'codeact_agent'
    assert 'Test Feature X' in str(action.inputs.get('title', ''))
    print('✓ Testing phase correctly delegates to CodeActAgent')

    # Test 3: Delegate method directly
    print('\n3. Testing delegate_to_codeact_agent method...')
    action = agent.delegate_to_codeact_agent(
        'Test Task', 'This is a test task for delegation'
    )
    assert isinstance(action, AgentDelegateAction)
    assert action.agent == 'codeact_agent'
    assert action.inputs['title'] == 'Test Task'
    print('✓ delegate_to_codeact_agent method works correctly')


if __name__ == '__main__':
    test_codeact_delegation()
    print('\n🎉 All CodeActAgent delegation tests passed!')
