from odoo import models
from odoo.fields import Command
from odoo.tools import plaintext2html


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "github.issue.sync.mixin"]

    _github_record_model = "project.task"
    _github_record_link_field = "project_id"

    def _github_sync_message(self, result):
        return self.env._(
            "%(created)s tasks created, %(updated)s tasks updated.", **result
        )

    def _github_sync_cache(self):
        return {**super()._github_sync_cache(), "tags": {}}

    def _github_record_values(self, issue, record, cache):
        values = super()._github_record_values(issue, record, cache)
        body = (issue.get("body") or "").strip()
        values.update(
            {
                "name": issue["title"],
                "description": plaintext2html(body) if body else False,
                "tag_ids": [Command.set(self._github_tags(issue, cache).ids)],
                "user_ids": [Command.set(self._github_assignees(issue, cache).ids)],
            }
        )
        if issue["state"] == "closed":
            # GitHub closes an issue as "completed" or as "not planned".
            values["state"] = (
                "1_canceled" if issue.get("state_reason") == "not_planned" else "1_done"
            )
        elif record and record.github_issue_state == "closed":
            values["state"] = "01_in_progress"
        return values

    def _github_tags(self, issue, cache):
        Tag = self.env["project.tags"]
        tags = Tag
        for name in self._github_label_names(issue):
            tag = cache["tags"].get(name)
            if not tag:
                tag = Tag.search([("name", "=", name)], limit=1) or Tag.create(
                    {"name": name}
                )
                cache["tags"][name] = tag
            tags |= tag
        return tags
