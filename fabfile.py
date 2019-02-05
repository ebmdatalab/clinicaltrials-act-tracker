import os

from fabric.api import run, sudo
from fabric.api import prefix, warn, abort
from fabric.api import task, env
from fabric.contrib.files import exists
from fabric.context_managers import cd

env.hosts = ['smallweb1.openprescribing.net']
env.forward_agent = True
env.colorize_errors = True

environments = {
    'live': 'fdaaa',
    'staging': 'fdaaa_staging',
    'test': 'fdaaa_test',
}

def sudo_script(script, www_user=False):
    """Run script under `deploy/fab_scripts/` as sudo.

    We don't use the `fabric` `sudo()` command, because instead we
    expect the user that is running fabric to have passwordless sudo
    access.  In this configuration, that is achieved by the user being
    a member of the `fabric` group (see `setup_sudo()`, below).

    """
    if www_user:
        sudo_cmd = 'sudo -u www-data '
    else:
        sudo_cmd = 'sudo '
    return run(sudo_cmd +
        os.path.join(
            env.path,
            'clinicaltrials-act-tracker/deploy/fab_scripts/%s' % script)
    )

def setup_sudo():
    """Ensures members of `fabric` group can execute deployment scripts as
    root without passwords

    """
    sudoer_file = '/etc/sudoers.d/fdaaa_fabric_{}'.format(env.app)
    if not exists(sudoer_file):
        sudo('echo "%fabric ALL = (www-data) NOPASSWD: {}/clinicaltrials-act-tracker/deploy/fab_scripts/" > {}'.format(env.path, sudoer_file))

def make_directory():
    if not exists(env.path):
        sudo("mkdir -p %s" % env.path)
        sudo("chown -R www-data:www-data %s" % env.path)
        sudo("chmod  g+w %s" % env.path)

def venv_init():
    run('[ -e venv ] || python3.5 -m venv venv')

def pip_install():
    with prefix('source venv/bin/activate'):
        run('pip install --upgrade pip setuptools')
        run('pip install -q -r clinicaltrials-act-tracker/requirements.txt')

def update_from_git(branch):
    # clone or update code
    if not exists('clinicaltrials-act-tracker/.git'):
        run("git clone -q git@github.com:ebmdatalab/clinicaltrials-act-tracker.git")
    with cd("clinicaltrials-act-tracker"):
        run("git fetch --all")
        run("git reset --hard origin/{}".format(branch))

def setup_nginx():
    sudo_script('setup_nginx.sh %s %s' % (env.path, env.app))

def setup_cron():
    if env.environment == 'live':
        sudo_script('setup_cron.sh %s' % (env.path))

def setup_ebmbot():
    sudo_script('setup_ebmbot.sh %s' % env.app)

def setup_django():
    with prefix('source venv/bin/activate'):
        run('cd clinicaltrials-act-tracker/clinicaltrials/ && python manage.py collectstatic --noinput --settings=frontend.settings')
        run('cd clinicaltrials-act-tracker/clinicaltrials/ && python manage.py migrate --settings=frontend.settings')

def restart_gunicorn():
    sudo_script("restart.sh %s" % env.app)

def reload_nginx():
    sudo_script("reload_nginx.sh")

def setup(environment, branch='master'):
    if environment not in environments:
        abort("Specified environment must be one of %s" %
              ",".join(environments.keys()))
    env.app = environments[environment]
    env.environment = environment
    env.path = "/var/www/%s" % env.app
    env.branch = branch
    return env


@task
def deploy(environment, branch='master'):
    env = setup(environment, branch)
    if environment == 'live':
        # Always deploy to staging first, thanks to our update
        # workflow (below)
        deploy('staging', branch=branch)

    make_directory()
    setup_sudo()
    with cd(env.path):
        with prefix("source /etc/profile.d/%s.sh" % env.app):
            venv_init()
            update_from_git(branch)
            setup_ebmbot()
            setup_cron()
            pip_install()
            setup_django()
            setup_nginx()
            restart_gunicorn()
            reload_nginx()


@task
def update(environment):
    # This currently assumes a workflow where data is first deployed
    # to staging, then reviewed, then copied to live.  Longer term we
    # may miss out the moderation step and scrape directly to live.
    env = setup(environment)
    if environment == 'staging':
        sudo_script(
            'kickoff_background_data_load.sh %s' % env.app, www_user=True)
    elif environment == 'live':
        sudo_script('copy_staging_to_live.sh')


@task
def send_tweet(environment):
    env = setup(environment)
    with cd(env.path):
        with prefix("source /etc/profile.d/%s.sh" % env.app):
            with prefix('source venv/bin/activate'):
                run('cd clinicaltrials-act-tracker/clinicaltrials/ && python manage.py tweet_today --settings=frontend.settings')
