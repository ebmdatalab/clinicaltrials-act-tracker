from fabric.api import run, sudo, put
from fabric.api import prefix, warn, abort
from fabric.api import settings, task, env, shell_env
from fabric.contrib.files import exists
from fabric.context_managers import cd

from datetime import datetime
import json
import os
import requests
import sys

env.hosts = ['smallweb1.openprescribing.net']
env.forward_agent = True
env.colorize_errors = True
env.user = 'root'

environments = {
    'live': 'fdaaa',
    'staging': 'fdaaa_staging',
}

def make_directory():
    run('mkdir -p %s' % (env.path))

def venv_init():
    run('[ -e venv ] || python3.5 -m venv venv')

def pip_install():
    with prefix('source venv/bin/activate'):
        run('pip install -q -r clinicaltrials-act-tracker/requirements.txt')

def update_from_git():
    # clone or update code
    if not exists('clinicaltrials-act-tracker/.git'):
        run("git clone -q git@github.com:ebmdatalab/clinicaltrials-act-tracker.git")
    else:
        with cd("clinicaltrials-act-tracker"):
            run("git pull -q")


def setup_nginx():
    run('ln -sf %s/clinicaltrials-act-tracker/deploy/supervisor-%s.conf /etc/supervisor/conf.d/%s.conf' % (env.path, env.app, env.app))
    run('ln -sf %s/clinicaltrials-act-tracker/deploy/nginx-%s /etc/nginx/sites-enabled/%s' % (env.path, env.app, env.app))
    run('chown -R www-data:www-data /var/www/%s/{clinicaltrials-act-tracker,venv}' % (env.app,))

def setup_django():
    with prefix('source venv/bin/activate'):
        run('cd clinicaltrials-act-tracker/clinicaltrials/ && python manage.py collectstatic --noinput --settings=clinicaltrials.settings')
        run('cd clinicaltrials-act-tracker/clinicaltrials/ && python manage.py migrate --settings=clinicaltrials.settings')

def restart_gunicorn():
    run("supervisorctl restart %s" % env.app)

#def run_migrations():
#    if env.environment == 'live':
#        with prefix('source .venv/bin/activate'):
#            run('cd openprescribing/ && python manage.py migrate '
#                '--settings=openprescribing.settings.live')
#    else:
#        warn("Refusing to run migrations in staging environment")

@task
def deploy(environment, branch='master'):
    if environment not in environments:
        abort("Specified environment must be one of %s" %
              ",".join(environments.keys()))
    env.app = environments[environment]
    env.environment = environment
    env.path = "/var/www/%s" % env.app
    env.branch = branch
    make_directory()
    with cd(env.path):
        with prefix("source /etc/profile.d/%s.sh" % env.app):
            venv_init()
            update_from_git()
            pip_install()
            setup_django()
            setup_nginx()
            restart_gunicorn()
