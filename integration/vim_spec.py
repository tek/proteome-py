from pathlib import Path
import os
import logging
from contextlib import contextmanager
import json

import sure  # NOQA
from flexmock import flexmock  # NOQA

import neovim  # type: ignore

from tryp import List, Map, Just
import tryp.logging

from tek.test import temp_dir, fixture_path

from proteome.nvim_plugin import ProteomeNvimPlugin
from proteome.project import Project
from proteome.nvim import NvimFacade

from integration._support.base import IntegrationSpec


class VimSpec(IntegrationSpec):

    def setup(self):
        self.cwd = Path.cwd()
        super(VimSpec, self).setup()
        self.logfile = temp_dir('log') / 'proteome_spec'
        self.vimlog = temp_dir('log') / 'vim'
        self.logfile.touch()
        tryp.logging.logfile = self.logfile
        tryp.logging.tryp_file_logging(handler_level=logging.WARN)
        argv = ['nvim', '--embed', '-V{}'.format(self.vimlog), '-u', 'NONE']
        self.neovim = neovim.attach('child', argv=argv)
        self.vim = NvimFacade(self.neovim)
        self.vim.set_pvar('config_path', str(self.config))
        self.vim.set_pvar('base_dirs', List(str(self.base)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', List('proteome.plugins.history',
                                          'proteome.plugins.ctags',
                                          'proteome.plugins.config',
                                          ))
        self._setup_handlers()

    def teardown(self):
        self.neovim.quit()
        os.chdir(str(self.cwd))

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

    def config(self):
        self.vim.set_pvar('plugins', List('proteome.plugins.config'))
        rtp = fixture_path('config', 'rtp')
        project = self.base / 'tpe' / 'pro'
        dep = self.base / 'tpe2' / 'dep'
        project.mkdir(parents=True)
        dep.mkdir(parents=True)
        self.vim.amend_optionl('runtimepath', rtp)
        self.vim.cd(str(project))
        self.vim.cmd('ProteomeStart')
        self._wait_for(lambda: self.vim.pvar('projects').is_just)
        self.vim.cmd('ProteomePostStartup')
        self._wait_for(lambda: self.vim.pvar('root_name').contains('pro'))
        self.vim.cmd('ProTo dep')
        self._wait_for(lambda: self.vim.pvar('root_name').contains('dep'))

__all__ = ('VimSpec')
