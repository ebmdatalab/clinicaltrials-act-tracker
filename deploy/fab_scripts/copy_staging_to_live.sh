#!/bin/bash

# This must be run with root privileges

set -e

su -c '/usr/bin/pg_dump --clean -t frontend_trial -t frontend_sponsor -t frontend_ranking -t frontend_trialqa clinicaltrials_staging | psql clinicaltrials' postgres
