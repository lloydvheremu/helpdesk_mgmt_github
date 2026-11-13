from datetime import datetime
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger

from odoo.addons.github_issue_sync.github_client import GithubClient
from odoo.addons.github_issue_sync.tests.github_mocks import (
    fake_session,
    make_issue,
    make_pull_request,
    make_response,
)

LOGGER = "odoo.addons.github_issue_sync.models.github_issue_sync_mixin"


@tagged("post_install", "-at_install")
class TestProjectGithubSync(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Synced",
                "github_repo": "owner/repo",
                "github_sync_enabled": True,
            }
        )
        cls.stage_todo = cls.env["project.task.type"].create(
            {"name": "To Do", "sequence": 1, "project_ids": cls.project.ids}
        )
        cls.stage_doing = cls.env["project.task.type"].create(
            {"name": "Doing", "sequence": 2, "project_ids": cls.project.ids}
        )
        cls.alice = new_test_user(
            cls.env, login="alice", groups="project.group_project_user"
        )
        cls.alice.github_login = "Alice-GH"
        cls.bob = new_test_user(
            cls.env, login="bob", groups="project.group_project_user"
        )
        cls.bob.github_login = "bob-gh"

    def _sync(self, *responses, project=None):
        """Run the sync with GitHub answering ``responses`` in order."""
        session = fake_session(*responses)
        client = GithubClient("token", session=session)
        Project = self.registry["project.project"]
        with patch.object(Project, "_github_get_client", return_value=client):
            result = (project or self.project)._github_sync()
        return result, session

    def _tasks(self, project=None):
        return (
            self.env["project.task"]
            .with_context(active_test=False)
            .search([("project_id", "=", (project or self.project).id)])
        )

    def test_issues_become_tasks(self):
        issue = make_issue(
            1,
            title="Fix login",
            body="Steps:\n1. open <page>",
            labels=[{"name": "gh-bug"}, {"name": "gh-backend"}],
            assignees=[
                {"login": "stranger"},
                {"login": "alice-gh"},
                {"login": "BOB-GH"},
            ],
        )
        result, _session = self._sync(make_response(body=[issue, make_pull_request(2)]))
        self.assertEqual(result, {"created": 1, "updated": 0})
        task = self._tasks()
        self.assertEqual(len(task), 1, "the pull request must not become a task")
        self.assertEqual(task.name, "Fix login")
        self.assertEqual(task.github_issue_id, str(issue["id"]))
        self.assertEqual(task.github_issue_number, 1)
        self.assertEqual(task.github_issue_url, issue["html_url"])
        self.assertEqual(task.github_issue_state, "open")
        self.assertTrue(task.github_last_sync)
        self.assertIn("open &lt;page&gt;", task.description)
        self.assertEqual(sorted(task.tag_ids.mapped("name")), ["gh-backend", "gh-bug"])
        self.assertEqual(task.user_ids, self.alice | self.bob, "every known assignee")
        self.assertEqual(task.stage_id, self.stage_todo, "the project's first stage")
        self.assertEqual(task.state, "01_in_progress")

    def test_sync_is_safe_to_repeat(self):
        self._sync(make_response(body=[make_issue(1), make_issue(2)]))
        result, _session = self._sync(
            make_response(body=[make_issue(1, title="Renamed"), make_issue(3)])
        )
        self.assertEqual(result, {"created": 1, "updated": 1})
        tasks = self._tasks()
        self.assertEqual(len(tasks), 3)
        self.assertIn("Renamed", tasks.mapped("name"))

    def test_tags_are_reused_and_created_once(self):
        tag = self.env["project.tags"].create({"name": "gh-existing"})
        labels = [{"name": "gh-existing"}, {"name": "gh-brand-new"}]
        self._sync(make_response(body=[make_issue(1, labels=labels)]))
        self._sync(make_response(body=[make_issue(2, labels=labels)]))
        for task in self._tasks():
            self.assertIn(tag, task.tag_ids)
        self.assertEqual(
            self.env["project.tags"].search_count([("name", "=", "gh-brand-new")]), 1
        )

    def test_github_is_source_of_truth_for_labels_and_assignees(self):
        self._sync(
            make_response(
                body=[
                    make_issue(
                        1,
                        labels=[{"name": "gh-bug"}],
                        assignees=[{"login": "alice-gh"}],
                    )
                ]
            )
        )
        self._sync(make_response(body=[make_issue(1, body="")]))
        task = self._tasks()
        self.assertFalse(task.tag_ids)
        self.assertFalse(task.user_ids)
        self.assertFalse(task.description)

    def test_closed_issue_closes_the_task(self):
        self._sync(make_response(body=[make_issue(1)]))
        task = self._tasks()
        self._sync(
            make_response(
                body=[make_issue(1, state="closed", state_reason="completed")]
            )
        )
        self.assertEqual(task.state, "1_done")
        self.assertEqual(task.github_issue_state, "closed")
        self.assertTrue(task.is_closed)

        self._sync(make_response(body=[make_issue(1, state="open")]))
        self.assertEqual(task.state, "01_in_progress")

    def test_not_planned_issue_cancels_the_task(self):
        self._sync(
            make_response(
                body=[make_issue(1, state="closed", state_reason="not_planned")]
            )
        )
        self.assertEqual(self._tasks().state, "1_canceled")

    def test_open_issue_keeps_state_and_stage_chosen_in_odoo(self):
        self._sync(make_response(body=[make_issue(1)]))
        task = self._tasks()
        task.write({"state": "03_approved", "stage_id": self.stage_doing.id})
        self._sync(make_response(body=[make_issue(1, title="Edited on GitHub")]))
        self.assertEqual(task.name, "Edited on GitHub")
        self.assertEqual(task.state, "03_approved")
        self.assertEqual(task.stage_id, self.stage_doing)

    def test_archived_task_is_updated_not_duplicated(self):
        self._sync(make_response(body=[make_issue(1)]))
        self._tasks().active = False
        result, _session = self._sync(make_response(body=[make_issue(1, title="New")]))
        self.assertEqual(result, {"created": 0, "updated": 1})
        self.assertEqual(self._tasks().name, "New")

    def test_projects_sync_independently(self):
        other = self.env["project.project"].create(
            {"name": "Other", "github_repo": "owner/other"}
        )
        self._sync(make_response(body=[make_issue(1)]))
        self._sync(make_response(body=[make_issue(1)]), project=other)
        self.assertEqual(len(self._tasks()), 1)
        self.assertEqual(len(self._tasks(other)), 1)

    @mute_logger("odoo.sql_db")
    def test_issue_linked_once_per_project(self):
        Task = self.env["project.task"]
        Task.create(
            {"name": "A", "project_id": self.project.id, "github_issue_id": "7"}
        )
        with self.assertRaises(IntegrityError):
            Task.create(
                {"name": "B", "project_id": self.project.id, "github_issue_id": "7"}
            )
            self.env.flush_all()

    def test_github_error_is_logged_and_progress_kept(self):
        self.project.github_last_sync = datetime(2026, 10, 1)
        with self.assertLogs(LOGGER, "WARNING"):
            result, _session = self._sync(make_response(404, {"message": "Not Found"}))
        self.assertIsNone(result)
        self.assertEqual(self.project.github_last_sync, datetime(2026, 10, 1))
        self.assertIn("Repository not found", self.project.message_ids[0].body)

    def test_sync_now_button_as_project_manager(self):
        manager = new_test_user(
            self.env, login="pm", groups="project.group_project_manager"
        )
        client = GithubClient(
            "token", session=fake_session(make_response(body=[make_issue(1)]))
        )
        Project = self.registry["project.project"]
        with patch.object(Project, "_github_get_client", return_value=client):
            action = self.project.with_user(manager).action_github_sync()
        self.assertEqual(action["params"]["type"], "success")
        self.assertIn("1 tasks created", action["params"]["message"])
        self.assertEqual(len(self._tasks()), 1)

    def test_cron_syncs_enabled_projects_only(self):
        Projects = self.env["project.project"]
        Projects.search([("id", "!=", self.project.id)]).write(
            {"github_sync_enabled": False}
        )
        disabled = Projects.create(
            {"name": "Off", "github_repo": "owner/off", "github_sync_enabled": False}
        )
        Project = self.registry["project.project"]
        synced = self.env["project.project"]

        def fake_sync(project):
            nonlocal synced
            synced |= project
            return {"created": 0, "updated": 0}

        with (
            patch.object(Project, "_github_sync", fake_sync),
            patch.object(self.registry["ir.cron"], "_commit_progress"),
        ):
            Project._cron_github_sync(self.env["project.project"])
        self.assertEqual(synced, self.project)
        self.assertNotIn(disabled, synced)

    def test_cron_is_installed(self):
        cron = self.env.ref("project_github.ir_cron_github_sync")
        self.assertEqual(cron.model_id.model, "project.project")

    def test_repo_is_validated_and_not_copied(self):
        with self.assertRaises(ValidationError):
            self.project.github_repo = "not a repo"
        with self.assertRaises(ValidationError):
            self.env["project.project"].create(
                {"name": "No repo", "github_sync_enabled": True}
            )
        copy = self.project.copy()
        self.assertFalse(copy.github_repo)
        self.assertFalse(copy.github_sync_enabled)
