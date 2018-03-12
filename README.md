# ClinicalTrials.gov ACT Tracker

[![Build Status](https://travis-ci.org/ebmdatalab/clinicaltrials-act-tracker.svg?branch=master)](https://travis-ci.org/ebmdatalab/clinicaltrials-act-tracker)

[![Coverage Status](https://coveralls.io/repos/github/ebmdatalab/clinicaltrials-act-tracker/badge.svg?branch=master)](https://coveralls.io/github/ebmdatalab/clinicaltrials-act-tracker?branch=master)



Overview
========

This software is designed to process a subset of trial registry data
from ClinicalTrials.gov that are subject to FDAAA 2017, i.e. which
come with a legal obligation to report results.  Such trials are known
as ACTs (Applicable Clinical Trials) or pACTs (probable ACTS).

This subset is displayed in a website that makes tracking and
reporting easier.

Operational overview:

1. Python script `load_data.py`:
 * downloads a zip clinical trials registry data from ClinicalTrials.gov
 * converts the XML to JSON
 * uploads it to BigQuery
 * runs SQL to transform it to tabular format including fields to
   indentify ACTs and their lateness
 * downloads SQL as a CSV file

2. Django management command `process_data`:
  * imports CSV file into Django models
  * precomputes aggregate statistics and turns these into rankings
  * handles other metadata (in particular, hiding trials that are no
    longer ACTs)
  * directly scrapes the website for metadata not in the zip
    (specifically, trials which have been submitted but are under a QA
    process).

These two commands are run daily via a `fab` script, and the results
loaded into a staging database / website.

A separate command copies new data from staging to production
(following moderation).

Static Pages
============

There is a simple system to allow non-technical users to generate pages using markdown. It is documented [here](../master/clinicaltrials/frontend/pages/readme.md)

Development
===========

Install these Python development packages before you begin. For
example, on a Debian-based system:

```
apt install python3
```

Using Python 3, create and enter a virtualenv, as [described
here](https://docs.djangoproject.com/en/1.10/intro/contributing/).
For example:

    python3 -m venv venv
    . venv/bin/activate

Install required Python packages.

    pip install pip-tools
    pip-sync

Set environment variables required (edit `environment` and then run `source environment`).


Checkout the data respository.

    cd ..
    git clone git@github.com:ebmdatalab/clinicaltrials-act-tracker.git
    cd -

Run the application.

    cd clinicaltrials
    ./manage.py runserver

There are a few tests.

    coverage run --source='.' manage.py test

Make a coverage report:

    coverage html -d /tmp/coverage_html

Deployment
==========

We use fabric to deploy over SSH to a pet server.  Deploy with

    fab deploy:staging

Or

    fab deploy:live

The code and data are updated via git from the master branch
of their repositories.

The configuration is in `fabfile.py` and the `deploy` directory.

When setting up a new server, put environment settings live in
`/etc/profile.d/fdaaa.sh`.

Updating data takes around 2 hours. To do it manually, first run (from
your local sandbox):

    fab update:staging

This downloads and processes the data and puts it on the staging site.
It is launched as a background process using `dtach`. If you're happy
with this, copy data across to the live database (warning: overwrites
existing data!) with:

    fab update:live

The target server
requires
[`gcloud` client libraries](https://cloud.google.com/storage/docs/gsutil_install#deb) and
`dtach` (`apt-get install dtach`) to be installed by any users who
might run fabric scripts, e.g. you (the developer) and the `ebmbot`
user (see below)


EBMBot
======

This is a Python [slackbot](https://github.com/lins05/slackbot). To start it:

    python ebmbot_runner.py

On the live server, it's managed by `supervisord`.

The bot does things like deployment by executing fabric tasks. In turn, this requires two things:

* The user it runs as must have passwordless ssh access to the live server, from the live server
* The user must have passwordless `sudo` access to the scripts in `deploy/fabric_scripts/`. We accomplish this via membership of a group called `fabric`.
* Fabric commands that require root must use a modified `sudo` method (specifically, `run("sudo <cmd>")` rather than `sudo(<cmd>)`.  See `sudo_script()` in `fabfile.py` for more.
