import json
import os
from typing import Any, Optional
BACKLOG_DIR = os.path.join(os.getcwd(), ".openhands", "backlog")

class BacklogTool:
    """Tool for managing backlog tasks in the RD Team Agent."""

    @staticmethod
    def create_backlog_task(
        title: str,
        description: str,
        phase: str,
        status: str = 'not_started',
        acceptance_criteria: Optional[str] = None,
    ) -> str:
        """
        Creates a new task in the backlog.

        Args:
            title: Title of the task
            description: Detailed description of the task
            phase: Development phase this task belongs to (planning, development, testing, validation)
            status: Current status of the task (not_started, in_progress, completed)
            acceptance_criteria: Criteria for considering the task complete

        Returns:
            str: Path to the created task file
        """
        os.makedirs(BACKLOG_DIR, exist_ok=True)

        task_data = {
            'title': title,
            'description': description,
            'phase': phase,
            'status': status,
            'acceptance_criteria': acceptance_criteria or '',
            'created_by': 'RDTeamAgent',
        }

        # Create a safe filename
        safe_title = title.replace(' ', '_').replace('/', '_').replace('\\', '_')
        task_file = os.path.join(BACKLOG_DIR, f'{safe_title}.json')
        with open(task_file, 'w') as f:
            json.dump(task_data, f, indent=2)

        return task_file

    @staticmethod
    def update_task_status(task_title: str, new_status: str) -> bool:
        """
        Updates the status of an existing task.

        Args:
            task_title: Title of the task (used to find the corresponding file)
            new_status: New status (e.g., "in_progress", "completed")

        Returns:
            bool: True if task was found and updated, False otherwise
        """
        # Create a safe filename matching the one used in create_backlog_task
        safe_title = task_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
        task_file = os.path.join(BACKLOG_DIR, f'{safe_title}.json')

        if not os.path.exists(task_file):
            return False

        with open(task_file, 'r') as f:
            task_data = json.load(f)

        task_data['status'] = new_status
        with open(task_file, 'w') as f:
            json.dump(task_data, f, indent=2)

        return True

    @staticmethod
    def get_backlog_tasks() -> list[dict[str, Any]]:
        """
        Gets all tasks in the backlog.

        Returns:
            list[Dict]: List of all task dictionaries
        """
        tasks: list[dict[str, Any]] = []

        if not os.path.exists(BACKLOG_DIR):
            return tasks

        for filename in os.listdir(BACKLOG_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(BACKLOG_DIR, filename), 'r') as f:
                    try:
                        tasks.append(json.load(f))
                    except json.JSONDecodeError:
                        continue

        return tasks

    @staticmethod
    def update_task(
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        acceptance_criteria: Optional[str] = None,
    ) -> bool:
        """Updates an existing backlog task. Returns True if successful."""
        task_path = os.path.join(BACKLOG_DIR, f"{task_id}.json")
        if not os.path.exists(task_path):
            return False
        with open(task_path, "r", encoding="utf-8") as f:
            task = json.load(f)
        if title is not None:
            task["title"] = title
        if description is not None:
            task["description"] = description
        if phase is not None:
            task["phase"] = phase
        if status is not None:
            task["status"] = status
        if acceptance_criteria is not None:
            task["acceptance_criteria"] = acceptance_criteria
        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(task, f, indent=2, ensure_ascii=False)
        return True

    @staticmethod
    def get_tasks_by_phase(phase: str) -> list[dict[str, Any]]:
        """
        Gets all tasks for a specific development phase.

        Args:
            phase: Development phase to filter by

        Returns:
            list[Dict]: List of task dictionaries
        """
        tasks: list[dict[str, Any]] = []

        if not os.path.exists(BACKLOG_DIR):
            return tasks

        for filename in os.listdir(BACKLOG_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(BACKLOG_DIR, filename), 'r') as f:
                    try:
                        task = json.load(f)
                        if task.get('phase', '').lower() == phase.lower():
                            tasks.append(task)
                    except json.JSONDecodeError:
                        continue

        return tasks
