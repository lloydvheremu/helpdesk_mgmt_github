from odoo import fields, models


class GithubIssueMixin(models.AbstractModel):
    """Fields of a record that mirrors one GitHub issue (a ticket, a task)."""

    _name = "github.issue.mixin"
    _description = "GitHub Issue Mixin"

    # GitHub issue ids no longer fit in a 32-bit integer, so keep them as text.
    github_issue_id = fields.Char(string="GitHub Issue ID", readonly=True, copy=False)
    github_issue_number = fields.Integer(
        string="GitHub Issue Number", readonly=True, copy=False
    )
    github_issue_url = fields.Char(string="GitHub Issue", readonly=True, copy=False)
    github_issue_state = fields.Selection(
        [("open", "Open"), ("closed", "Closed")],
        string="GitHub State",
        readonly=True,
        copy=False,
    )
    github_last_sync = fields.Datetime(
        string="Last GitHub Sync", readonly=True, copy=False
    )
