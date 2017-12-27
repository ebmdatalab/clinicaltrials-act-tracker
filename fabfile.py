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
    'live': 'eutrialstracker_live',
    #'staging': 'eutrialstracker_staging'
}

def make_directory():
    run('mkdir -p %s' % (env.path))

def venv_init():
    run('[ -e venv ] || python3.5 -m venv venv')

def pip_install():
    with prefix('source venv/bin/activate'):
	run('pip install -q -r euctr-tracker-code/requirements.txt')

def update_from_git():
    # clone or update code
    if not exists('euctr-tracker-code/.git'):
	run(env.git_code_key + "git clone -q git@github.com:ebmdatalab/euctr-tracker-code.git")
    else:
	with cd("euctr-tracker-code"):
	    run(env.git_code_key + "git pull -q")

    # clone or update data
    if not exists('euctr-tracker-data/.git'):
	run(env.git_data_key + "git clone -q git@github.com:ebmdatalab/euctr-tracker-data.git")
    else:
	with cd("euctr-tracker-data"):
	    run(env.git_data_key + "git pull -q")

def setup_nginx():
    run('ln -sf %s/euctr-tracker-code/deploy/supervisor-%s.conf /etc/supervisor/conf.d/%s.conf' % (env.path, env.app, env.app))
    run('ln -sf %s/euctr-tracker-code/deploy/nginx-%s /etc/nginx/sites-enabled/%s' % (env.path, env.app, env.app))
    run('chown -R www-data:www-data /var/www/%s/{euctr-tracker-code,euctr-tracker-data,letsencrypt,venv}' % (env.app,))
    run('%s/euctr-tracker-code/deploy/restart-web-services.sh' % (env.path,))

def setup_cron():
    run('cp %s/euctr-tracker-code/deploy/crontab-%s /etc/cron.d/' % (env.path, env.app))

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

    # assumes these are manually made on the server first time setup, and added
    # as repository keys to github
    env.git_code_key = "GIT_SSH_COMMAND='ssh -i %s/ssh-keys/id_rsa_eutrialtracker_code' " % env.path
    env.git_data_key = "GIT_SSH_COMMAND='ssh -i %s/ssh-keys/id_rsa_eutrialtracker_data' " % env.path

    make_directory()
    with cd(env.path):
	venv_init()
	update_from_git()
        pip_install()
	setup_nginx()
	setup_cron()




