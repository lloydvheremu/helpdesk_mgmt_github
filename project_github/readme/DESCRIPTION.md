This module imports the issues of a GitHub repository as tasks of a
project, and keeps them up to date with a scheduled job. It does not need
the Helpdesk modules.

A project is linked to one GitHub repository. Every issue becomes a task
of that project and is updated on later runs. Pull requests are skipped.

| GitHub | Project task |
| --- | --- |
| Title | Title |
| Body | Description (plain text) |
| Labels | Tags (reused by name, created when missing) |
| Assignees | Assignees: every assignee whose GitHub Login matches an internal user |
| Closed as completed | State *Done* |
| Closed as not planned | State *Cancelled* |
| Reopened | State *In Progress* |
| Number, URL, state | Read-only GitHub tab on the task |

New tasks start in the project's first stage, and the sync never moves
tasks between stages, so you can use the stages as you like. GitHub is the
source of truth for the title, description, tags and assignees: changes
made in Odoo are overwritten the next time the issue changes on GitHub.
Creating tasks does not notify the assignees.
