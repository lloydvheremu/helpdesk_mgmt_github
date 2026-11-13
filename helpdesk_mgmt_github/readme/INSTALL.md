To install this module, you need to:

1.  Install the OCA [Helpdesk Management](https://github.com/OCA/helpdesk/tree/19.0/helpdesk_mgmt)
    module (`helpdesk_mgmt`, branch `19.0`).
2.  Clone this repository and add the repository folder to the Odoo
    `addons_path`. Each module is a folder of the repository, and this
    module needs `github_issue_sync` from the same repository.
3.  Install the Python dependency: `pip install requests`.
4.  Update the apps list and install *Helpdesk GitHub Sync*.

When you upgrade from version 19.0.2, `github_issue_sync` is installed
during the upgrade. The token you saved and the GitHub logins of your
users are kept.
