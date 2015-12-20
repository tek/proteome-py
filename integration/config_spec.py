import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List

from tek.test import fixture_path

from integration._support.base import VimIntegrationSpec


class _ConfigSpec(VimIntegrationSpec):

    def _setup_handlers(self):
        plug_path = fixture_path(
            'nvim_plugin', 'rplugin', 'python3', 'proteome_nvim.py')
        handlers = [
            {
                'sync': 1,
                'name': 'ProteomeStart',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProteomePostStartup',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProAdd',
                'type': 'command',
                'opts': {'nargs': '+'}
            },
            {
                'sync': 0,
                'name': 'ProTo',
                'type': 'command',
                'opts': {'nargs': 1}
            }
        ]
        self.vim.call(
            'remote#host#RegisterPlugin',
            'python3',
            str(plug_path),
            handlers,
        )

    def _pre_start(self):
        pass

    @property
    def _plugins(self):
        return List('proteome.plugins.config')


class ChangeProjectSpec(_ConfigSpec):

    def change_project(self):
        self._wait_for(lambda: self.vim.pvar('root_name').contains(self.name1))
        self.vim.cmd('ProTo dep')
        self._wait_for(lambda: self.vim.pvar('root_name').contains(self.name2))


class AdditionalLangsSpec(_ConfigSpec):

    def _pre_start(self):
        pass

    def additional_langs(self):
        self._wait_for(lambda: self.vim.pvar('root_name').contains(self.name1))
        self.vim.cmd('ProTo dep')
        self._wait_for(lambda: self.vim.pvar('root_name').contains(self.name2))

__all__ = ('VimSpec')
