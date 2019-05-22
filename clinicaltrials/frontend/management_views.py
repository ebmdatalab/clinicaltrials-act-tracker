from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.conf import settings
from ctconvert import create_instance
from ctconvert.convert_data import get_csv_path


def valid_secret(func):
    def wrapper(*args, **kwargs):
        secret = args[0].GET.get('secret')
        if not secret \
           or not settings.SECRET_MANAGEMENT_KEY \
           or settings.SECRET_MANAGEMENT_KEY != secret:
            raise PermissionDenied
        return func(*args, *kwargs)
    return wrapper


@valid_secret
def process_data(request, path=None):
    command = "process_data"
    result = call_command(command, input_csv=path)
    context = {
        'command': command,
        'args': 'path={}'.format(path),
        'result': result
    }
    return render(request, "command.html", context=context)


@valid_secret
def load_data(request):
    callback = "https://{}/management/process_data/{}?secret={}".format(
        request.get_host(),
        "https://storage.googleapis.com/" + get_csv_path(),
        settings.SECRET_MANAGEMENT_KEY)
    result = create_instance.main(
        "ebmdatalab",
        "europe-west2-a",
        "ctgov-converter",
        callback,
        wait=False)
    context = {
        'command': ('create_instance.main("ebmdatalab", '
                    '"europe-west2-a", "ctgov-converter")'),
        'result': result
    }
    return render(request, "command.html", context=context)
