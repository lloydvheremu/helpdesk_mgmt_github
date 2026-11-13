# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "GitHub Issue Sync",
    "summary": "Shared base to import GitHub issues into Odoo records",
    "author": "Lloyd Vheremu",
    "website": "https://github.com/lloydvheremu/helpdesk_mgmt_github",
    "license": "AGPL-3",
    "category": "Hidden/Tools",
    "development_status": "Beta",
    "maintainers": ["lloydvheremu"],
    "version": "19.0.1.0.0",
    "depends": ["base_setup", "mail"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
    ],
}
