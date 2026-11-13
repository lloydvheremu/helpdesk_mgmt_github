from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestGithubSettings(TransactionCase):
    def test_token_is_stored_as_system_parameter(self):
        settings = self.env["res.config.settings"].create({"github_token": "tok"})
        settings.execute()
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param("github_issue_sync.token"),
            "tok",
        )

    def test_github_login_is_unique_ignoring_case(self):
        alice = new_test_user(self.env, login="alice")
        alice.github_login = "Alice-GH"
        bob = new_test_user(self.env, login="bob")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            bob.github_login = "alice-gh"
            self.env.flush_all()

    def test_users_without_login_are_not_constrained(self):
        new_test_user(self.env, login="carol")
        new_test_user(self.env, login="dave")
        self.env.flush_all()
