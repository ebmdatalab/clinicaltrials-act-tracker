import os
import django.core.exceptions


Unset = object()  # Explicit default value None is not the same as lacking a default.


def get_env_setting(setting, default=Unset):
    """ Get the environment setting.

    Return the default, or raise an exception if none supplied
    """
    try:
        return os.environ[setting]
    except KeyError:
        if default is Unset:
            error_msg = "Set the %s env variable" % setting
            raise django.core.exceptions.ImproperlyConfigured(error_msg)

        return default
