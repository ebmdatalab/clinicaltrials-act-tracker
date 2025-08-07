set dotenv-load := true
set positional-arguments

_env:
    @test -f .env || copy environment-example .env

_venv:
    #!/bin/bash
    test -d venv && exit 0
    python3.7 -m venv ./venv
    ./venv/bin/pip install pip-tools
    ./venv/bin/pip-sync

# create local dev db
create-dev-db: _env
    ./createdb.sh

# run management commands
manage *args: _venv
    {{ just_executable() }} clinicaltrials/manage {{ args }}

test *args: _venv
    {{ just_executable() }} clinicaltrials/manage test {{ args }}
