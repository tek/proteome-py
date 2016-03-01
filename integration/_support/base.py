import os
from pathlib import Path

from fn import _  # type: ignore

from tryp.test import fixture_path, temp_dir  # type: ignore

from tryp import List, Map, Just, Maybe
from trypnv.test import IntegrationSpec as TrypnvIntegrationSpec
from trypnv.test import VimIntegrationSpec as TrypnvVimIntegrationSpec

from proteome.project import Project
from proteome.nvim import NvimFacade
from proteome.logging import Logging
from proteome.test import Spec


class IntegrationCommon(Spec):

    def setup(self):
        self.cwd = Maybe.from_call(Path.cwd, exc=IOError)
        super().setup()

    def _cd_back(self):
        try:
            self.cwd.map(str).foreach(os.chdir)
        except Exception as e:
            self.log.error('error changing back to project root: {}'.format(e))

    def teardown(self):
        super().teardown()
        self._cd_back()


class IntegrationSpec(TrypnvIntegrationSpec, IntegrationCommon):

    def setup(self):
        super().setup()
        self.base = temp_dir('projects', 'base')
        self.config = fixture_path('conf')
        self.type1_base = temp_dir('projects', 'type1')
        self.type_bases = Map({self.type1_base: List('type1')})

    def mk_project(self, tpe, name):
        root = temp_dir(str(self.base / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def add_projects(self, *pros):
        return List(*pros).smap(self.mk_project)


class VimIntegrationSpec(TrypnvVimIntegrationSpec, IntegrationCommon, Logging):

    def setup(self):
        super().setup()
        self.vim.cmd_sync('ProteomeStart')
        self._wait_for(lambda: self.vim.pvar('projects').is_just)
        self.vim.cmd('ProteomePostStartup')
        self._pvar_becomes('root_dir', str(self.main_project))

    def _nvim_facade(self, vim):
        return NvimFacade(vim)

    def _pre_start_neovim(self):
        self.base = temp_dir('projects', 'base')
        self.type1_base = temp_dir('projects', 'type1')
        self.type_bases = Map({self.type1_base: List('type1')})
        self._setup_plugin()

    def _post_start_neovim(self):
        self._set_vars()
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

    def _set_vars(self):
        self.vim.set_pvar('config_path', str(self._config_path))
        self.vim.set_pvar('base_dirs', List(str(self.base)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', self._plugins)

    def _setup_plugin(self):
        self._rplugin_path = fixture_path(
            'nvim_plugin', 'rplugin', 'python3', 'proteome_nvim.py')
        self._handlers = [
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
            {
                'sync': 0,
                'name': 'ProNext',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProPrev',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProHistoryPrev',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProHistoryNext',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProHistoryLog',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProHistoryBrowse',
                'type': 'command',
                'opts': {'nargs': 0}
            },
            {
                'sync': 0,
                'name': 'ProHistoryBrowseInput',
                'type': 'command',
                'opts': {'nargs': 1}
            },
            {
                'sync': 0,
                'name': 'ProHistorySwitch',
                'type': 'command',
                'opts': {'nargs': 1}
            },
            {
                'sync': 0,
                'name': 'ProHistoryPick',
                'type': 'command',
                'opts': {'nargs': 1}
            },
            {
                'sync': 0,
                'name': 'BufEnter',
                'type': 'autocmd',
                'opts': {'pattern': '*'}
            },
        ]

    # FIXME quitting neovim blocks sometimes
    # without quitting, specs with subprocesses block in the end
    def teardown(self):
        # self.neovim.quit()
        super().teardown()
        if self._debug:
            self._log_out.foreach(self.log.info)

    @property
    def _plugins(self):
        return List()

    def _pre_start(self):
        pass

    @property
    def _config_path(self):
        return Path('/dev/null')

    def _project_becomes(self, name):
        self._pvar_becomes_map('active', name, _['name'])

__all__ = ['IntegrationSpec']
