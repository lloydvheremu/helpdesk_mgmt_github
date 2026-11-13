# The GitHub token moved to the github_issue_sync module, which every GitHub
# module now shares. Keep the token that was already saved.


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_config_parameter
           SET key = 'github_issue_sync.token'
         WHERE key = 'helpdesk_mgmt_github.token'
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter
                WHERE key = 'github_issue_sync.token'
           )
        """
    )
    # A token was already set for github_issue_sync: drop the old copy.
    cr.execute(
        "DELETE FROM ir_config_parameter WHERE key = 'helpdesk_mgmt_github.token'"
    )
