from amino import List, Path

from amino.test import fixture_path

from kallikrein.matchers import equal, contain
from kallikrein import Expectation
from kallikrein.matchers.maybe import be_just

from integration._support.base import DefaultSpec


class _ConfigSpec(DefaultSpec):

    @property
    def components(self) -> List[str]:
        return List('proteome.components.config')


class ChangeProjectSpec(_ConfigSpec):
    '''change the current project $change_project
    '''

    def change_project(self) -> Expectation:
        self.project_becomes(self.name1)
        self.vim.cmd('ProTo dep')
        return self.project_becomes(self.name2)


class ConfigErrorSpec(_ConfigSpec):
    '''print message for error occuring in project config $error
    '''

    def _post_start_neovim(self):
        super()._post_start_neovim()
        rtp = fixture_path('config', 'error', 'rtp')
        self.vim.options.amend_l('runtimepath', rtp)

    def error(self) -> Expectation:
        self.project_becomes(self.name1)
        return self._log_line(-1, be_just(contain('Not an editor command')))


class AdditionalLangsSpec(_ConfigSpec):
    '''read additional langs from config $additional_langs
    '''

    @property
    def _config_path(self) -> Path:
        return fixture_path('additional_langs', 'conf.json')

    def additional_langs(self) -> Expectation:
        return self.pvar_becomes('main_types', equal(List('tpe', 'tpe1', 'tpe2')))

__all__ = ('AdditionalLangsSpec', 'ChangeProjectSpec', 'ConfigErrorSpec')
