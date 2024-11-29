from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from . import __version__


class PluginApp(AppConfig):
    name = 'samaware'
    verbose_name = 'SamAware'

    class PretalxPluginMeta:
        name = 'SamAware'
        description = _('pretalx plugin with enhanced features for speaker care during a conference')
        version = __version__
        author = 'Felix Dreissig'
        visible = True
        category = 'FEATURE'

    def ready(self):
        from . import signals  # noqa: F401, pylint: disable=C0415, W0611
