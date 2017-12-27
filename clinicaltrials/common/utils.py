import os
import django.core.exceptions


# Originally taken from openprescribing
def get_env_setting(setting, default=None):
    """ Get the environment setting.

    Return the default, or raise an exception if none supplied
    """
    try:
        return os.environ[setting]
    except KeyError:
        if default:
            return default
        else:
            error_msg = "Set the %s env variable" % setting
            raise django.core.exceptions.ImproperlyConfigured(error_msg)
