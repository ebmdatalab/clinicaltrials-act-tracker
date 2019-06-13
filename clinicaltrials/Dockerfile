# This Dockerfile is to support pre-deploy steps that write to the
# filesystem, such as running `collectstatic`.  It is used by Google
# Cloud Build, and referenced in `cloudbuild.yaml`.

# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3

COPY . .

# Install production dependencies.
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "manage.py"]