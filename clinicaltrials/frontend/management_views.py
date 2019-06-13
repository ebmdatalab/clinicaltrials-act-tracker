import io
import os
import re
from contextlib import redirect_stdout

from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.conf import settings

from ctconvert import create_instance
from ctconvert.convert_data import get_csv_path


from googleapiclient.discovery import build


def valid_secret(func):
    def wrapper(*args, **kwargs):
        secret = args[0].GET.get("secret")
        if (
            not secret
            or not settings.HTTP_MANAGEMENT_SECRET
            or settings.HTTP_MANAGEMENT_SECRET != secret
        ):
            raise PermissionDenied
        return func(*args, **kwargs)

    return wrapper


def stop_instance():
    # Requires App Engine Admin API to be enabled for the project
    if "GAE_SERVICE" in os.environ:
        service = build("appengine", "v1")
        # Work around https://issuetracker.google.com/issues/135051375
        application_id = re.sub(r"^.~", "", os.environ["GAE_APPLICATION"])
        result = (
            service.apps()
            .services()
            .versions()
            .instances()
            .delete(
                appsId=application_id,
                servicesId=os.environ["GAE_SERVICE"],
                versionsId=os.environ["GAE_VERSION"],
                instancesId=os.environ["GAE_INSTANCE"],
            )
            .execute()
        )
        if "done" in result and "error" in result:
            raise Exception(
                "Problem shutting down instance: {}".format(result["error"])
            )


def stop_instance_on_completion(func):
    """If we're running in GAE, shut ourselves down
    """

    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
        finally:
            stop_instance()
        return response

    return wrapper


@valid_secret
@stop_instance_on_completion
def general_view(request, args):
    parts = args.split("/")
    command_name = parts[0]
    if command_name not in settings.HTTP_MANAGEMENT_WHITELIST:
        raise PermissionDenied

    args = [
        x for x in parts[1:] if x
    ]  # remove empty strings caused by trailing slashes
    kwargs = {}
    for k, v in request.GET.items():
        if k in kwargs:
            raise Exception("Can't handle duplicate values from query string")
        if k != "secret":
            kwargs[k] = v
    f = io.StringIO()
    with redirect_stdout(f):
        call_command(command_name, *args, **kwargs)
    result = f.getvalue()

    # Build representation of command-as-called
    command_args_str = ""
    if args:
        command_args_str += ", ".join(args)
    if kwargs:
        command_args_str += ", ".join([k + "=" + v for k, v in kwargs.items()])
    if args or kwargs:
        command_as_called = command_name + "({})".format(command_args_str)
    else:
        command_as_called = command_name + "()"

    context = {"command": command_as_called, "result": result}
    return render(request, "command.txt", context=context, content_type="text/plain")
