from odoo import fields, models
from odoo.fields import Command
from odoo.tools import plaintext2html


class HelpdeskTicketTeam(models.Model):
    _name = "helpdesk.ticket.team"
    _inherit = ["helpdesk.ticket.team", "github.issue.sync.mixin"]

    _github_record_model = "helpdesk.ticket"
    _github_record_link_field = "team_id"

    github_open_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Stage for Open Issues",
        domain="['|', ('team_ids', '=', False), ('team_ids', 'in', id)]",
        copy=False,
        help="Stage for new tickets and for issues that are reopened. "
        "Leave empty to use the team's first open stage.",
    )
    github_closed_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Stage for Closed Issues",
        domain="['|', ('team_ids', '=', False), ('team_ids', 'in', id)]",
        copy=False,
        help="Stage for tickets whose issue is closed. "
        "Leave empty to use the team's first closed stage.",
    )

    def _github_sync_message(self, result):
        return self.env._(
            "%(created)s tickets created, %(updated)s tickets updated.", **result
        )

    def _github_sync_cache(self):
        return {**super()._github_sync_cache(), "tags": {}}

    def _github_record_values(self, issue, record, cache):
        values = super()._github_record_values(issue, record, cache)
        body = (issue.get("body") or "").strip()
        values.update(
            {
                "name": issue["title"],
                # The description is required, so an empty issue gets a
                # placeholder.
                "description": plaintext2html(
                    body or self.env._("No description on GitHub.")
                ),
                "tag_ids": [Command.set(self._github_tags(issue, cache).ids)],
                "user_id": self._github_assignee(issue, cache).id,
            }
        )
        if issue["state"] == "closed":
            stage = self._github_closed_stage()
        elif not record or record.github_issue_state == "closed":
            stage = self._github_open_stage()
        else:
            stage = self.env["helpdesk.ticket.stage"]
        if stage:
            values["stage_id"] = stage.id
        return values

    def _github_open_stage(self):
        return (
            self.github_open_stage_id
            or self._get_applicable_stages().filtered(lambda stage: not stage.closed)[
                :1
            ]
        )

    def _github_closed_stage(self):
        return (
            self.github_closed_stage_id
            or self._get_applicable_stages().filtered("closed")[:1]
        )

    def _github_tags(self, issue, cache):
        Tag = self.env["helpdesk.ticket.tag"]
        tags = Tag
        for name in self._github_label_names(issue):
            tag = cache["tags"].get(name)
            if not tag:
                tag = Tag.search(
                    [
                        ("name", "=", name),
                        ("company_id", "in", [False, self.company_id.id]),
                    ],
                    limit=1,
                ) or Tag.create({"name": name, "company_id": self.company_id.id})
                cache["tags"][name] = tag
            tags |= tag
        return tags

    def _github_assignee(self, issue, cache):
        """The first assignee who is an Odoo user allowed on this team.

        A ticket has a single assignee. When the team has members, only they
        can be assigned, as on the ticket form.
        """
        for user in self._github_assignees(issue, cache):
            if not self.user_ids or user in self.user_ids:
                return user
        return self.env["res.users"]
