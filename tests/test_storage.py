import os
import pytest
from src.storage.db import TaskStorage
from src.models.task import Task, TaskType, TaskStatus, TaskPriority
from datetime import datetime

@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    return TaskStorage(str(db_path))

def test_create_and_get_task(storage):
    task = Task(
        id="task-1",
        project_name="test-project",
        type=TaskType.STANDARD,
        title="Test Task",
        description="Test Description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM
    )
    
    storage.create_task(task)
    retrieved = storage.get_task("task-1")
    
    assert retrieved is not None
    assert retrieved.title == "Test Task"
    assert retrieved.project_name == "test-project"

def test_list_tasks(storage):
    task1 = Task(id="t1", project_name="p1", type=TaskType.STANDARD, title="T1")
    task2 = Task(id="t2", project_name="p1", type=TaskType.STANDARD, title="T2")
    task3 = Task(id="t3", project_name="p2", type=TaskType.STANDARD, title="T3")
    
    storage.create_task(task1)
    storage.create_task(task2)
    storage.create_task(task3)
    
    p1_tasks = storage.list_tasks(project_name="p1")
    assert len(p1_tasks) == 2
    
    all_tasks = storage.list_tasks()
    assert len(all_tasks) == 3

def test_update_task(storage):
    task = Task(id="t1", project_name="p1", type=TaskType.STANDARD, title="Original")
    storage.create_task(task)
    
    task.title = "Updated"
    task.status = TaskStatus.DONE
    storage.update_task(task)
    
    retrieved = storage.get_task("t1")
    assert retrieved.title == "Updated"
    assert retrieved.status == TaskStatus.DONE

def test_delete_task(storage):
    task = Task(id="t1", project_name="p1", type=TaskType.STANDARD, title="T1")
    storage.create_task(task)
    
    assert storage.get_task("t1") is not None
    
    storage.delete_task("t1")
    assert storage.get_task("t1") is None
