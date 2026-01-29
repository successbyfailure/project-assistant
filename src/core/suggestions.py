from typing import List, Dict, Any
from src.models.project import GitInfo, GitHubInfo, Suggestion
from src.models.task import Task, TaskStatus

class SuggestionsEngine:
    def generate_suggestions(self, git_info: GitInfo, github_info: GitHubInfo, tasks: List[Task]) -> List[Suggestion]:
        suggestions = []
        
        # 1. Check Git status
        if git_info.is_dirty:
            suggestions.append(Suggestion(
                priority="high",
                action="commit_changes",
                description=f"You have {len(git_info.modified_files)} modified files that need to be committed.",
                files=git_info.modified_files
            ))
        
        if git_info.ahead > 0:
            suggestions.append(Suggestion(
                priority="medium",
                action="push_changes",
                description=f"Your local branch is ahead of origin by {git_info.ahead} commits."
            ))

        # 1b. Check for stale branches
        from datetime import datetime, timedelta
        now = datetime.now()
        for b in git_info.branches:
            if b.get("name") == git_info.branch:
                continue
            
            # last_commit_date format depends on mcp-server-git, usually ISO string
            last_date_str = b.get("last_commit_date")
            if last_date_str:
                try:
                    # Strip Z if present for fromisoformat in older python
                    last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
                    if now - last_date.replace(tzinfo=None) > timedelta(days=30):
                        suggestions.append(Suggestion(
                            priority="low",
                            action="cleanup_branch",
                            description=f"Branch '{b['name']}' hasn't been updated in over 30 days."
                        ))
                except (ValueError, TypeError):
                    pass

        # 2. Check GitHub issues
        for issue in github_info.issues:
            # If an issue is open and not linked to any task
            linked = any(t.github_issue_number == issue["number"] for t in tasks)
            if not linked:
                suggestions.append(Suggestion(
                    priority="medium",
                    action="create_task_from_issue",
                    description=f"New GitHub issue: {issue['title']}",
                    issue_number=issue["number"]
                ))

        # 3. Check Tasks
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        if not in_progress and any(t for t in tasks if t.status == TaskStatus.TODO):
            suggestions.append(Suggestion(
                priority="low",
                action="start_task",
                description="You don't have any tasks in progress. Consider starting a new one."
            ))

        return suggestions
