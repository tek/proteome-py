import os
from pathlib import Path
from threading import Thread
import asyncio
from functools import wraps

import neovim  # type: ignore

from tek.test import fixture_path, temp_dir  # type: ignore

from tryp import List, Map, Just

from integration._support.spec import Spec

from proteome.project import Project
from proteome.nvim import NvimFacade


class IntegrationSpec(Spec):

    def setup(self, *a, **kw):
        super(IntegrationSpec, self).setup(*a, **kw)
        self.base = temp_dir('projects', 'base')
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
        self.logfile = temp_dir('log') / self.__class__.__name__
        os.environ['PROTEOME_LOG_FILE'] = str(self.logfile)
        self.vimlog = temp_dir('log') / 'vim'
        self._start_neovim()
        self._set_vars()
        rtp = fixture_path('config', 'rtp')
        self.vim.amend_optionl('runtimepath', rtp)
        self._setup_handlers()
        self.tpe1 = 'tpe'
        self.tpe2 = 'tpe2'
        self.name1 = 'pro'
        self.name2 = 'dep'
        self.ident1 = '{}/{}'.format(self.tpe1, self.name1)
        self.ident2 = '{}/{}'.format(self.tpe2, self.name2)
        self.main_project = self.base / self.tpe1 / self.name1
        dep = self.base / self.tpe2 / self.name2
        self.main_project.mkdir(parents=True)
        dep.mkdir(parents=True)
        self.vim.cd(str(self.main_project))
        self._pre_start()
        self.vim.cmd('ProteomeStart')
        self._wait_for(lambda: self.vim.pvar('projects').is_just)
        self.vim.cmd('ProteomePostStartup')

    def _start_neovim(self):
        ''' start an embedded vim session that loads no init.vim.
        **self.vimlog** is set as log file. aside from being convenient,
        this is crucially necessary, as the first use of the session
        will block if stdout is used for output.
        '''
        argv = ['nvim', '--embed', '-V{}'.format(self.vimlog), '-u', 'NONE']
        self.neovim = neovim.attach('child', argv=argv)
        self.vim = NvimFacade(self.neovim)

    def _set_vars(self):
        self.vim.set_pvar('config_path', str(self._config_path))
        self.vim.set_pvar('base_dirs', List(str(self.base)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', self._plugins)

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
            },
            {
                'sync': 0,
                'name': 'ProSave',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProShow',
                'type': 'command',
                'opts': {'nargs': 0}
            },
        ]
        self.vim.call(
            'remote#host#RegisterPlugin',
            'python3',
            str(plug_path),
            handlers,
        )

    def teardown(self):
        self.neovim.quit()
        os.chdir(str(self.cwd))

    @property
    def _plugins(self):
        return List()

    def _pre_start(self):
        pass

    @property
    def _config_path(self):
        return Path('/dev/null')

    def _pvar_becomes(self, name, value):
        return self._wait_for(lambda: self.vim.pvar(name).contains(value))

    @property
    def _log_out(self):
        return List.wrap(self.logfile.read_text().splitlines())


def main_looped(fun):
    @wraps(fun)
    def wrapper(self):
        def runner():
            fun(self)
            loop.call_soon_threadsafe(lambda: done.set_result(True))
        loop = asyncio.get_event_loop()
        done = asyncio.Future()
        Thread(target=runner).start()
        loop.run_until_complete(done)
    return wrapper

__all__ = ['IntegrationSpec']
