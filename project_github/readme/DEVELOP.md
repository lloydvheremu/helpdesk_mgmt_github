Run the tests on a throwaway database. They mock GitHub, so they work
offline:

``` sh
odoo-bin -d test_project_github -i project_github --test-tags /github_issue_sync,/project_github --stop-after-init
```
