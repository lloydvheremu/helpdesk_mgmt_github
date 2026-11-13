To sync GitHub issues into another model, inherit the two mixins and map
an issue to your record. For example, for a model `my.board` whose
records hold `my.card` records:

``` python
class MyCard(models.Model):
    _name = "my.card"
    _inherit = ["my.card", "github.issue.mixin"]

    _github_issue_unique = models.Constraint(
        "UNIQUE(board_id, github_issue_id)",
        "This GitHub issue is already linked to a card of this board.",
    )


class MyBoard(models.Model):
    _name = "my.board"
    _inherit = ["my.board", "github.issue.sync.mixin"]  # my.board uses mail.thread

    _github_record_model = "my.card"
    _github_record_link_field = "board_id"

    def _github_record_values(self, issue, record, cache):
        values = super()._github_record_values(issue, record, cache)
        values["name"] = issue["title"]
        return values
```

Then add a scheduled action that runs `model._cron_github_sync()` on
`my.board`, and a *Sync now* button that calls `action_github_sync`.

The tests mock GitHub, so they work offline. The helpers in
`tests/github_mocks.py` build fake API responses for the tests of the
other modules too.
