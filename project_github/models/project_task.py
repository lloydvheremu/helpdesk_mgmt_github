from odoo import models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "github.issue.mixin"]

    _github_issue_unique = models.Constraint(
        "UNIQUE(project_id, github_issue_id)",
        "This GitHub issue is already linked to a task in this project.",
    )
