import logging
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..github_client import GithubClient, GithubError

_logger = logging.getLogger(__name__)

GITHUB_REPO_PATTERN = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")
# Fetch a little before the last sync, in case the clocks of Odoo and GitHub
# differ. Issues seen twice are simply updated again.
SYNC_OVERLAP = timedelta(minutes=5)


class GithubIssueSyncMixin(models.AbstractModel):
    """Link a record (a helpdesk team, a project) to a GitHub repository.

    The issues of the repository are imported as records of
    ``_github_record_model``, which must inherit ``github.issue.mixin`` and
    point back to this record with its ``_github_record_link_field``. The
    model using this mixin must also inherit ``mail.thread``, because sync
    errors are posted in its chatter.

    To map an issue to a record, override ``_github_record_values``.
    """

    _name = "github.issue.sync.mixin"
    _description = "GitHub Issue Sync Mixin"

    # Set these on the model that inherits the mixin.
    _github_record_model = None
    _github_record_link_field = None

    github_repo = fields.Char(
        string="GitHub Repository",
        help="Repository to sync with, written as owner/name, for example odoo/odoo.",
        copy=False,
    )
    github_sync_enabled = fields.Boolean(
        string="Sync with GitHub",
        help="Include this record in the scheduled GitHub sync.",
        copy=False,
    )
    github_last_sync = fields.Datetime(
        string="Last GitHub Sync",
        readonly=True,
        copy=False,
    )

    @api.constrains("github_repo")
    def _check_github_repo(self):
        for record in self:
            if record.github_repo and not GITHUB_REPO_PATTERN.fullmatch(
                record.github_repo
            ):
                raise ValidationError(
                    self.env._(
                        "The GitHub repository must be written as owner/name, "
                        "for example odoo/odoo."
                    )
                )

    @api.constrains("github_sync_enabled", "github_repo")
    def _check_github_sync_has_repo(self):
        for record in self:
            if record.github_sync_enabled and not record.github_repo:
                raise ValidationError(
                    self.env._("Set a GitHub repository before turning on the sync.")
                )

    def action_github_sync(self):
        """Sync now button: import the issues and report the result."""
        self.ensure_one()
        result = self._github_sync()
        if result is None:
            message = self.env._("The sync failed. The error is logged in the chatter.")
            notification_type = "danger"
        else:
            message = self._github_sync_message(result)
            notification_type = "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("GitHub Sync"),
                "message": message,
                "type": notification_type,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _github_sync_message(self, result):
        """Text of the notification shown after a successful Sync now."""
        return self.env._(
            "%(created)s records created, %(updated)s records updated.", **result
        )

    @api.model
    def _github_sync_domain(self):
        """Records that the scheduled action syncs."""
        return [("github_sync_enabled", "=", True), ("github_repo", "!=", False)]

    @api.model
    def _cron_github_sync(self):
        records = self.search(self._github_sync_domain())
        self.env["ir.cron"]._commit_progress(remaining=len(records))
        for record in records:
            try:
                with self.env.cr.savepoint():
                    record._github_sync()
            except Exception:
                _logger.exception("GitHub sync failed for %s", record)
                record._github_log_error(
                    self.env._("Unexpected error, see the server log for details.")
                )
            self.env["ir.cron"]._commit_progress(1)

    def _github_get_client(self):
        token = (
            self.env["ir.config_parameter"].sudo().get_param("github_issue_sync.token")
        )
        return GithubClient(token or None)

    def _github_sync(self):
        """Import the issues updated since the last sync.

        Returns a dict with the number of records created and updated, or None
        when GitHub returned an error. Errors are posted in the chatter.
        """
        self.ensure_one()
        sync_started = fields.Datetime.now()
        since = self.github_last_sync and self.github_last_sync - SYNC_OVERLAP
        client = self._github_get_client()
        cache = self._github_sync_cache()
        created = updated = 0
        try:
            for issue in client.iter_issues(self.github_repo, since=since):
                if self._github_import_issue(issue, cache):
                    created += 1
                else:
                    updated += 1
        except GithubError as error:
            # Records imported before the error are kept. The next run fetches
            # the same issues again, which is safe.
            _logger.warning("GitHub sync failed for %s: %s", self, error)
            self._github_log_error(str(error))
            return None
        self.github_last_sync = sync_started
        return {"created": created, "updated": updated}

    def _github_sync_cache(self):
        """Data looked up once per sync and shared by all issues of the run."""
        return {"users": self._github_users_by_login()}

    def _github_import_issue(self, issue, cache):
        """Create or update the record of one issue. Returns True if created."""
        Record = self.env[self._github_record_model].with_context(
            active_test=False, mail_auto_subscribe_no_notify=True
        )
        link_field = self._github_record_link_field
        record = Record.search(
            [
                (link_field, "=", self.id),
                ("github_issue_id", "=", str(issue["id"])),
            ],
            limit=1,
        )
        values = self._github_record_values(issue, record, cache)
        if record:
            record.write(values)
            return False
        Record.create({link_field: self.id, **values})
        return True

    def _github_record_values(self, issue, record, cache):
        """Values to write on the record of ``issue``.

        ``record`` is the existing record, or an empty recordset when the
        issue is new. Override to add the fields of the target model.
        """
        return {
            "github_issue_id": str(issue["id"]),
            "github_issue_number": issue["number"],
            "github_issue_url": issue["html_url"],
            "github_issue_state": issue["state"],
            "github_last_sync": fields.Datetime.now(),
        }

    def _github_users_by_login(self):
        users = self.env["res.users"].search(
            [("github_login", "!=", False), ("share", "=", False)]
        )
        return {user.github_login.lower(): user for user in users}

    def _github_assignees(self, issue, cache):
        """The internal users whose GitHub Login is among the issue assignees."""
        users = self.env["res.users"]
        for assignee in issue.get("assignees") or []:
            user = cache["users"].get(assignee["login"].lower())
            if user:
                users |= user
        return users

    @api.model
    def _github_label_names(self, issue):
        return [
            label["name"] if isinstance(label, dict) else label
            for label in issue.get("labels") or []
        ]

    def _github_log_error(self, message):
        self.message_post(
            body=self.env._("GitHub sync failed: %(error)s", error=message),
            subtype_xmlid="mail.mt_note",
        )
