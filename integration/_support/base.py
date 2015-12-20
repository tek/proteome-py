import os
from pathlib import Path
from threading import Thread
import asyncio
from functools import wraps
import logging

import neovim  # type: ignore

from tek.test import fixture_path, temp_dir  # type: ignore

import tryp.logging
from tryp import List, Map, Just

from integration._support.spec import Spec

from proteome.project import Project
from proteome.nvim import NvimFacade


class IntegrationSpec(Spec):

    def setup(self, *a, **kw):
        super(IntegrationSpec, self).setup(*a, **kw)
        self.config = fixture_path('conf')
        self.type1_base = temp_dir('projects', 'type1')
        self.type_bases = Map({self.type1_base: List('type1')})
        self.history_base = temp_dir('history')

    def mk_project(self, tpe, name):
        root = temp_dir(str(self.base / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def add_projects(self, *pros):
        return List(*pros).smap(self.mk_project)


class VimIntegrationSpec(Spec):

    def setup(self):
        self.cwd = Path.cwd()
        super().setup()
        self.base = temp_dir('projects', 'base')
        self.type1_base = temp_dir('projects', 'type1')
        self.type_bases = Map({self.type1_base: List('type1')})
        self.history_base = temp_dir('history')
        self.logfile = temp_dir('log') / 'proteome_spec'
        self.vimlog = temp_dir('log') / 'vim'
        self.logfile.touch()
        tryp.logging.logfile = self.logfile
        tryp.logging.tryp_file_logging(handler_level=logging.WARN)
        self._start_neovim()
        self._set_vars()
        rtp = fixture_path('config', 'rtp')
        self.vim.amend_optionl('runtimepath', rtp)
        self._setup_handlers()
        self.name1 = 'pro'
        self.name2 = 'dep'
        project = self.base / 'tpe' / self.name1
        dep = self.base / 'tpe2' / self.name2
        project.mkdir(parents=True)
        dep.mkdir(parents=True)
        self.vim.cd(str(project))
        self._pre_start()
        self.vim.cmd('ProteomeStart')
        self._wait_for(lambda: self.vim.pvar('projects').is_just)
        self.vim.cmd('ProteomePostStartup')

    def _start_neovim(self):
        argv = ['nvim', '--embed', '-V{}'.format(self.vimlog), '-u', 'NONE']
        self.neovim = neovim.attach('child', argv=argv)
        self.vim = NvimFacade(self.neovim)

    def _set_vars(self):
        self.vim.set_pvar('config_path', str(self._config_path))
        self.vim.set_pvar('base_dirs', List(str(self.base)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', self._plugins)

    def teardown(self):
        self.neovim.quit()
        os.chdir(str(self.cwd))

    @property
    def _plugins(self):
        return List()

    @property
    def _config_path(self):
        return Path('/dev/null')


def main_looped(fun):
    @wraps(fun)
    def wrapper(self):
        loop = asyncio.get_event_loop()
        done = asyncio.Future()
        def runner():
            fun(self)
            loop.call_soon_threadsafe(lambda: done.set_result(True))
        Thread(target=runner).start()
        loop.run_until_complete(done)
    return wrapper

__all__ = ['IntegrationSpec']
