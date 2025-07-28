import os
from collections import deque
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from openhands.events.action import Action
    from openhands.llm.llm import ModelResponse

from openhands.agenthub.rd_team_agent.tools.backlog import BacklogTool
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core.config import AgentConfig
from openhands.core.logger import openhands_logger as logger
from openhands.core.message import Message, TextContent
from openhands.events.action.agent import (
    AgentDelegateAction,
    AgentFinishAction,
    AgentFinishTaskCompleted,
)
from openhands.events.action.message import MessageAction
from openhands.events.event import Event, EventSource
from openhands.llm.llm import LLM
from openhands.llm.llm_utils import check_tools
from openhands.memory.conversation_memory import ConversationMemory
from openhands.utils.prompt import PromptManager


class RDTeamAgent(Agent):
    VERSION = '1.0'
    """
    The RD Team Agent is a comprehensive agent that functions as a complete R&D team.
    It coordinates multiple roles (Coordinator, Product Owner, Architect, Developer,
    Tester, Validator) to autonomously progress through development phases, validate
    each phase, and generate tasks in the `.openhands/backlog` folder.

    ## Overview

    This agent implements a multi-role coordination system that:
    1. **Plans**: Defines project scope, features, and milestones
    2. **Architects**: Designs system architecture and components
    3. **Develops**: Implements features with code quality focus
    4. **Tests**: Validates functionality through comprehensive testing
    5. **Validates**: Ensures each phase meets quality standards before progression

    ## Key Features

    - **Autonomous operation**: Moves through phases independently
    - **Backlog management**: Generates tasks in `.openhands/backlog`
    - **Phase validation**: Validates completion before progressing
    - **Test coverage**: Ensures comprehensive test coverage
    """

    def __init__(
        self,
        llm: LLM,
        config: AgentConfig,
    ) -> None:
        """Initializes a new instance of the RDTeamAgent class.

        Parameters:
        - llm (LLM): The language model to be used by this agent
        - config (AgentConfig): The configuration for this agent
        """
        super().__init__(llm, config)

        self.pending_actions: deque['Action'] = deque()
        # Create a ConversationMemory instance
        self.conversation_memory = ConversationMemory(self.config, self.prompt_manager)

    @property
    def prompt_manager(self) -> PromptManager:
        if self._prompt_manager is None:
            self._prompt_manager = PromptManager(
                prompt_dir=os.path.join(os.path.dirname(__file__), 'prompts'),
                system_prompt_filename=self.config.system_prompt_filename,
            )
        return self._prompt_manager

    def reset(self) -> None:
        """Resets the RDTeamAgent's internal state."""
        super().reset()
        # Only clear pending actions, not LLM metrics
        self.pending_actions.clear()

    def step(self, state: State) -> 'Action':
        """Performs one step using the RDTeamAgent.

        This includes gathering info on previous steps and prompting the model to make a decision
        about which role should take the next action (Coordinator, Product Owner, Architect,
        Developer, Tester, or Validator).

        Parameters:
        - state (State): used to get updated info

        Returns:
        - MessageAction(content) - Communication from any team role
        - AgentFinishAction() - end the interaction when complete
        """
        # Continue with pending actions if any
        if self.pending_actions:
            return self.pending_actions.popleft()

        # Check if we're done
        latest_user_message = state.get_last_user_message()
        if latest_user_message and latest_user_message.content.strip() == '/exit':
            return AgentFinishAction(
                final_thought='User requested exit',
                task_completed=AgentFinishTaskCompleted.TRUE,
            )

        # Get the current phase from state or initialize
        current_phase = self._get_current_phase(state)
        logger.info(f'Current phase: {current_phase}')

        # Handle different phases specially
        if current_phase == 'requirements_gathering':
            return self._handle_requirements_gathering(state)
        elif current_phase == 'development':
            return self._handle_development_phase(state)
        elif current_phase == 'testing':
            return self._handle_testing_phase(state)

        # Process events and get messages for LLM
        condensed_history: list[Event] = []
        initial_user_message = self._get_initial_user_message(state.history)

        messages = self._get_messages(condensed_history, initial_user_message)
        params: dict = {
            'messages': self.llm.format_messages_for_llm(messages),
        }

        # Add phase information to the prompt
        if len(messages) > 0 and hasattr(messages[0], 'content'):
            original_content = messages[0].content
            combined_text = ''
            for item in original_content:
                if hasattr(item, 'text'):
                    combined_text += item.text + '\n'

            # Add phase information to the prompt
            current_phase = self._get_current_phase(state)
            phase_prompt = f'Current development phase: {current_phase}'
            combined_text += phase_prompt + '\n'
            messages[0].content = [TextContent(text=combined_text)]

        # Add tools and metadata like codeact_agent does
        params['tools'] = check_tools(self.tools, self.llm.config)
        params['extra_body'] = {'metadata': state.to_llm_metadata(agent_name=self.name)}
        response = self.llm.completion(**params)
        logger.debug(f'Response from LLM: {response}')
        actions = self.response_to_actions(response)
        logger.debug(f'Actions after response_to_actions: {actions}')
        for action in actions:
            self.pending_actions.append(action)
        return self.pending_actions.popleft()

    def _get_current_phase(self, state: State) -> str:
        """Determines the current development phase based on state history."""
        # Check for phase markers in the conversation history
        for event in reversed(state.history):
            if isinstance(event, MessageAction):
                content = event.content.lower()
                if 'phase:' in content:
                    parts = content.split('phase:')
                    if len(parts) > 1:
                        return parts[1].strip().split('\n')[0].strip()

        # Default phases in order

        # Find the current phase based on backlog or state
        try:
            tasks = BacklogTool.get_backlog_tasks()
        except Exception as e:
            logger.warning(f'Error getting backlog tasks: {e}')
            return 'requirements_gathering'

        # Determine phase based on existing tasks - check in reverse order of phases
        if not tasks:
            return 'requirements_gathering'
        elif any('validation' in (t.get('phase', '') or '').lower() for t in tasks):
            return 'validation'
        elif any('testing' in (t.get('phase', '') or '').lower() for t in tasks):
            return 'testing'
        elif any('development' in (t.get('phase', '') or '').lower() for t in tasks):
            return 'development'
        elif any('architecture' in (t.get('phase', '') or '').lower() for t in tasks):
            return 'architecture'
        elif any('planning' in (t.get('phase', '') or '').lower() for t in tasks):
            return 'planning'

        # Return first phase if no tasks found
        return 'requirements_gathering'

    def _get_initial_user_message(self, history: list[Event]) -> MessageAction:
        """Finds the initial user message action from the full history."""
        initial_user_message: MessageAction | None = None
        for event in history:
            if isinstance(event, MessageAction) and event.source == 'user':
                initial_user_message = event
                break

        if initial_user_message is None:
            logger.error(
                f'CRITICAL: Could not find the initial user MessageAction in the full {len(history)} events history.'
            )
            raise ValueError(
                'Initial user message not found in history. Please report this issue.'
            )
        return initial_user_message

    def _handle_requirements_gathering(self, state: State) -> 'Action':
        """
        Handles the requirements gathering phase where Product Owner interacts with user.
        Returns appropriate actions based on the conversation context.
        """
        logger.info('Handling requirements gathering phase')

        # Buscar si ya existe una tarea de requirements gathering
        try:
            all_tasks = BacklogTool.get_backlog_tasks()
            requirements_tasks = [
                task
                for task in all_tasks
                if (task.get('phase', '').lower() == 'requirements_gathering')
            ]
        except Exception as e:
            logger.warning(f'Error getting backlog tasks: {e}')
            requirements_tasks = []

        # Buscar mensajes del usuario relevantes
        user_messages = [
            e
            for e in state.history
            if isinstance(e, MessageAction) and e.source == 'user'
        ]
        last_user_message = user_messages[-1].content.lower() if user_messages else ''

        # Si el usuario indica que terminó ("/done" o similar)
        if any(
            x in last_user_message
            for x in ['no more requirements', '/done', 'listo', 'terminé']
        ):
            # Actualiza la tarea de requirements con los requisitos recogidos
            requirements_text = '\n'.join([m.content for m in user_messages])
            if requirements_tasks:
                BacklogTool.update_task(
                    requirements_tasks[0]['id'],
                    description=requirements_text,
                    status='completed',
                )
            else:
                self.create_backlog_task(
                    title='Gather Requirements',
                    description=requirements_text,
                    phase='requirements_gathering',
                    status='completed',
                    acceptance_criteria='User requirements have been collected and documented',
                )
            self.pending_actions.extend(
                [
                    MessageAction(
                        content="Thank you! All requirements have been documented. Shall we move to planning? (Reply 'yes' to continue)",
                        source=EventSource.AGENT,
                    )
                ]
            )
            return self.pending_actions.popleft()

        # Si ya existe la tarea y está completa, pasar a planning
        if requirements_tasks and requirements_tasks[0].get('status') == 'completed':
            return self._advance_to_planning_phase()

        # Si no hay requisitos aún, preguntar
        if not user_messages or 'requirements' not in last_user_message:
            self.pending_actions.extend(
                [
                    MessageAction(
                        content="As the Product Owner, please describe all the requirements for your project. When finished, reply '/done'.",
                        source=EventSource.AGENT,
                    )
                ]
            )
            return self.pending_actions.popleft()

        # Si el usuario está proporcionando requisitos, seguir preguntando
        self.pending_actions.extend(
            [
                MessageAction(
                    content="Noted. Do you have more requirements? If not, reply '/done'.",
                    source=EventSource.AGENT,
                )
            ]
        )
        return self.pending_actions.popleft()

    def _advance_to_planning_phase(self) -> 'Action':
        """Advances from requirements gathering to planning phase."""
        logger.info('Advancing to planning phase')
        # Aquí puedes interactuar para definir milestones, entregables, etc.
        self.pending_actions.extend(
            [
                MessageAction(
                    content="Let's start planning! Please describe the main milestones and deliverables for your project.",
                    source=EventSource.AGENT,
                )
            ]
        )
        return self.pending_actions.popleft()

    def _handle_development_phase(self, state: State) -> 'Action':
        """Handles the development phase where tasks are delegated to CodeActAgent."""
        logger.info('Handling development phase')

        # Check if there are any development tasks in backlog
        try:
            development_tasks = BacklogTool.get_tasks_by_phase('development')
            if not development_tasks:
                self.pending_actions.extend(
                    [
                        MessageAction(
                            content="No development tasks found. Let's create some based on the requirements.",
                            source=EventSource.AGENT,
                        )
                    ]
                )
                return self.pending_actions.popleft()
        except Exception as e:
            logger.warning(f'Error getting development tasks: {e}')
            development_tasks = []

        # If there are tasks, delegate them to CodeActAgent
        if development_tasks:
            task = development_tasks[0]  # Take the first one for now
            return self.delegate_to_codeact_agent(
                task_title=task['title'], task_description=task['description']
            )

        # If no tasks and no errors, we're done with development
        self.pending_actions.extend(
            [
                MessageAction(
                    content="Development phase completed. Shall we move to testing? (Reply 'yes' to continue)",
                    source=EventSource.AGENT,
                )
            ]
        )
        return self.pending_actions.popleft()

    def _handle_testing_phase(self, state: State) -> 'Action':
        """Handles the testing phase where tasks are delegated to CodeActAgent."""
        logger.info('Handling testing phase')

        # Check if there are any testing tasks in backlog
        try:
            testing_tasks = BacklogTool.get_tasks_by_phase('testing')
            if not testing_tasks:
                self.pending_actions.extend(
                    [
                        MessageAction(
                            content="No testing tasks found. Let's create some based on the implemented features.",
                            source=EventSource.AGENT,
                        )
                    ]
                )
                return self.pending_actions.popleft()
        except Exception as e:
            logger.warning(f'Error getting testing tasks: {e}')
            testing_tasks = []

        # If there are tasks, delegate them to CodeActAgent
        if testing_tasks:
            task = testing_tasks[0]  # Take the first one for now
            return self.delegate_to_codeact_agent(
                task_title=task['title'], task_description=task['description']
            )

        # If no tasks and no errors, we're done with testing
        self.pending_actions.extend(
            [
                MessageAction(
                    content="Testing phase completed. Shall we move to validation? (Reply 'yes' to continue)",
                    source=EventSource.AGENT,
                )
            ]
        )
        return self.pending_actions.popleft()

    def _get_messages(
        self, events: list[Event], initial_user_message: MessageAction
    ) -> list[Message]:
        """Constructs the message history for the LLM conversation."""
        if not self.prompt_manager:
            raise Exception('Prompt Manager not instantiated.')

        # Use ConversationMemory to process events (including SystemMessageAction)
        messages = self.conversation_memory.process_events(
            condensed_history=events,
            initial_user_action=initial_user_message,
            max_message_chars=self.llm.config.max_message_chars,
            vision_is_active=self.llm.vision_is_active(),
        )

        if self.llm.is_caching_prompt_active():
            self.conversation_memory.apply_prompt_caching(messages)

        return messages

    def create_backlog_task(
        self,
        title: str,
        description: str,
        phase: Optional[str] = None,
        status: str = 'not_started',
        acceptance_criteria: Optional[str] = None,
    ) -> str:
        """Creates a backlog task based on the current phase."""
        # Get current phase if not specified
        if phase is None:
            from openhands.controller.state.state import State

            phase = self._get_current_phase(State())

        return BacklogTool.create_backlog_task(
            title=title,
            description=description,
            phase=phase,
            status=status,
            acceptance_criteria=acceptance_criteria,
        )

    def delegate_to_codeact_agent(
        self, task_title: str, task_description: str
    ) -> 'Action':
        """Delegates a development or testing task to the CodeActAgent.

        Args:
            task_title: Title of the task to delegate
            task_description: Detailed description of what needs to be done

        Returns:
            AgentDelegateAction: Action to delegate the task to CodeActAgent
        """
        logger.info(f'Delegating task "{task_title}" to CodeActAgent')

        # Prepare inputs for CodeActAgent
        inputs = {
            'task': task_description,
            'title': task_title,
            'instructions': (
                f"Complete the task '{task_title}' as described. "
                f'This is part of a larger project managed by RDTeamAgent. '
                f'Follow best practices for code quality and testing.'
            ),
        }

        return AgentDelegateAction(
            agent='codeact_agent',
            inputs=inputs,
            thought=f'Delegating implementation/testing task "{task_title}" to CodeActAgent',
        )

    def response_to_actions(self, response: 'ModelResponse') -> list['Action']:
        """
        Converts LLM response to actions.
        Supports multi-action and function-calling style responses.
        """
        # If using function-calling, parse accordingly
        actions = []
        # If response.choices exists, use the first choice's message
        if hasattr(response, 'choices') and response.choices:
            msg = response.choices[0].message
            content = msg.content
            role = getattr(msg, 'role', 'assistant')
        else:
            content = (
                response.content if hasattr(response, 'content') else str(response)
            )
            role = 'assistant'

        # Map role to source
        if role == 'assistant':
            source = EventSource.AGENT
        elif role == 'user':
            source = EventSource.USER
        else:
            source = EventSource.AGENT

        # Check for finish signal
        if any(
            keyword in content.lower()
            for keyword in ['complete', 'finished', 'done', '/exit']
        ):
            actions.append(
                AgentFinishAction(
                    final_thought='Task completed',
                    task_completed=AgentFinishTaskCompleted.TRUE,
                )
            )
            return actions

        actions.append(MessageAction(content=content, source=source))
        return actions
