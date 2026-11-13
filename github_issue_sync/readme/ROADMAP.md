- Replace the client, token and GitHub logins with OCA
  [github_connector](https://github.com/OCA/interface-github) once it is
  available for Odoo 19.0. It is not merged for 19.0 yet.
- One token for the whole database, not one per repository or per user.
- Send changes made in Odoo back to GitHub (two-way sync, planned for v2).
- Webhooks, so updates arrive immediately instead of with the next run.
