# euctr-tracker

Development
===========

Install these Python development packages before you begin. For
example, on a Debian-based system:

```
apt install python3 python3-venv
```

Using Python 3, create and enter a virtualenv, as [described
here](https://docs.djangoproject.com/en/1.10/intro/contributing/).
For example:

```
python3.5 -m venv venv
. venv/bin/activate
```

Install required Python packages.

```
pip install -r requirements.txt
```

Set environment variables required (edit `environment` and then run `source environment`).


Checkout the data respository.

```
cd ..
git clone git@github.com:ebmdatalab/clinicaltrials-act-tracker.git
cd -
```
Run the application.

```
cd clinicaltrials
./manage.py runserver
```

There are a few tests.

```
./manage.py test
```

Deployment
==========

We use fabric to deploy over SSH to a pet server.

```
fab deploy:live
```

The code and data are updated via git from the master branch
of their repositories.

The configuration is in `fabfile.py` and the `deploy` directory.

When settings up a new server:
* Put environment settings live in `/etc/profile.d/fdaaa.sh`


Loading new data
================

TBD
