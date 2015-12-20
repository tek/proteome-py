import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List

from tek.test import fixture_path

from integration._support.base import VimIntegrationSpec


class _ConfigSpec(VimIntegrationSpec):

    @property
    def _plugins(self):
        return List('proteome.plugins.config')


class ChangeProjectSpec(_ConfigSpec):

    def change_project(self):
        self._pvar_becomes('root_name', self.name1)
        self.vim.cmd('ProTo dep')
        self._pvar_becomes('root_name', self.name2)


class AdditionalLangsSpec(_ConfigSpec):

    @property
    def _config_path(self):
        return fixture_path('additional_langs', 'conf.json')

    def additional_langs(self):
        self._pvar_becomes('root_name', self.name1)
        self._pvar_becomes('main_types', List('tpe1', 'tpe2'))

__all__ = ('AdditionalLangsSpec', 'ChangeProjectSpec')
