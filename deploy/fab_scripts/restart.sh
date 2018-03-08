#!/bin/bash

set -e

supervisorctl restart $1
