from odoo import models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = ["helpdesk.ticket", "github.issue.mixin"]

    _github_issue_unique = models.Constraint(
        "UNIQUE(team_id, github_issue_id)",
        "This GitHub issue is already linked to a ticket in this team.",
    )
