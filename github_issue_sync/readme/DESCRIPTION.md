This module is the shared base of the GitHub modules in this repository.
On its own it adds no menu. Install one of the modules that use it:

- `helpdesk_mgmt_github`: GitHub issues become Helpdesk tickets (OCA
  [Helpdesk Management](https://github.com/OCA/helpdesk/tree/19.0/helpdesk_mgmt)).
- `project_github`: GitHub issues become project tasks.

It provides:

- A small client for the GitHub REST API. It pages through the issues of
  a repository, skips pull requests and turns rate limits, bad tokens and
  timeouts into clear error messages.
- One GitHub access token for the whole database, in the general
  settings.
- A *GitHub Login* on users, so issue assignees can be matched to Odoo
  users.
- Two mixins that hold the sync logic, so each module only maps an issue
  to its own records:
  - `github.issue.sync.mixin`, for the record linked to a repository (a
    Helpdesk team, a project): repository fields, *Sync now*, the
    scheduled sync and error logging in the chatter.
  - `github.issue.mixin`, for the records that mirror an issue (a ticket,
    a task): issue id, number, URL, state and last sync time.
