from amino import List

from amino.test import fixture_path

from integration._support.base import ProteomePluginIntegrationSpec


class _ConfigSpec(ProteomePluginIntegrationSpec):

    @property
    def _plugins(self):
        return List('proteome.plugins.config')


class ChangeProjectSpec(_ConfigSpec):

    def change_project(self):
        self._project_becomes(self.name1)
        self.vim.cmd('ProTo dep')
        self._project_becomes(self.name2)


class ConfigErrorSpec(_ConfigSpec):

    def _post_start_neovim(self):
        super()._post_start_neovim()
        rtp = fixture_path('config', 'error', 'rtp')
        self.vim.options.amend_l('runtimepath', rtp)

    def error(self):
        self._project_becomes(self.name1)
        self._log_line(0, lambda a: 'Not an editor command' in a)


class AdditionalLangsSpec(_ConfigSpec):

    @property
    def _config_path(self):
        return fixture_path('additional_langs', 'conf.json')

    def additional_langs(self):
        self._pvar_becomes('main_types', List('tpe', 'tpe1', 'tpe2'))

__all__ = ('AdditionalLangsSpec', 'ChangeProjectSpec')
