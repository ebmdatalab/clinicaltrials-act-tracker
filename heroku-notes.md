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
i


* Storage solution
  * no heroku bandwidth costs
  * GCS: ingress is free; egress is 0.12/GB
    * The zipfile is 1.3GB
    * Unzipped it is 8.4GB
    * So the process of turning it into JSON and CSV requires 10GB of space
    * About $5 a month
  * So I would probably design the heroku app to pull the latest CSV from a URL
  * And a google compute instance to generate the CSV
  * I like this because it separates the web app nicely
  * However it does require a separate process to generate the files
  * I think I can live with this


  gcloud compute instances create <instance name> \
    --metadata-from-file startup-script=examples/scripts/install.sh

  gcutil --project=<project-id> addinstance <instance name> --service_account_scopes=compute-rw

  or sudo shutdown -h now


  gcutil deleteinstance -f <instance name>
