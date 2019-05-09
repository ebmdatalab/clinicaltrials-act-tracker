# Moving to Heroku

1. Convert logging to write to STDOUT
2. Support data updates
  - is it OK to store CSV during build process
    - yes: in /tmp BUT slug Size: 500MB - Hard
  - how can we promote staging to production data
    - two databases; toggle between them. maintain state in a separate database.
    - this involves three databases: the one for current state, plus two versions of the data one.
    - or the data one has a "current version" table in both versions which is the same in both.
    - so the update goes:
       1) import into "staging" (free dyno)
       2) review
       3) change config on production to point at different database
