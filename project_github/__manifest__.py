# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Project GitHub Sync",
    "summary": "Import GitHub issues as project tasks",
    "author": "Lloyd Vheremu",
    "website": "https://github.com/lloydvheremu/helpdesk_mgmt_github",
    "license": "AGPL-3",
    "category": "Services/Project",
    "development_status": "Beta",
    "maintainers": ["lloydvheremu"],
    "version": "19.0.1.0.0",
    "depends": ["project", "github_issue_sync"],
    "data": [
        "data/ir_cron_data.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
    ],
}
