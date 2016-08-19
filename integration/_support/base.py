import os
from pathlib import Path

from fn import _

from amino.test import fixture_path, temp_dir

from amino import List, Map, Just, Maybe, Right
from ribosome.test import IntegrationSpec, PluginIntegrationSpec

from proteome.project import Project
from proteome.nvim import NvimFacade
from proteome.logging import Logging
from proteome.test import Spec
from proteome.nvim_plugin import ProteomeNvimPlugin


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


class ProteomeIntegrationSpec(IntegrationSpec, IntegrationCommon):

    def setup(self):
        super().setup()
        self.base = temp_dir('projects', 'base')
        self.config = fixture_path('conf')
        self.type1 = 'type1'
        self.type1_base = temp_dir('projects', self.type1)
        self.type_bases = Map({self.type1_base: List(self.type1)})

    def mk_project(self, tpe, name):
        root = temp_dir(str(self.base / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def add_projects(self, *pros):
        return List(*pros).smap(self.mk_project)


class ProteomePluginIntegrationSpec(PluginIntegrationSpec, IntegrationCommon,
                                    Logging):

    def setup(self):
        super().setup()
        self.vim.cmd_sync('ProteomeStart')
        self._wait_for(lambda: self.vim.pvar('projects').is_just)
        self.vim.cmd('ProteomePostStartup')
        self._pvar_becomes('root_dir', str(self.main_project))

    def _nvim_facade(self, vim):
        return NvimFacade(vim)

    def _pre_start_neovim(self):
        super()._pre_start_neovim()
        self.base = temp_dir('projects', 'base')
        self.base2 = temp_dir('projects', 'base2')
        self.typed1 = 'type1'
        self.type1_base = temp_dir('projects', self.typed1)
        self.type_bases = Map({self.type1_base: List(self.typed1)})

    def _post_start_neovim(self):
        super()._post_start_neovim()
        self._set_vars()
        self.tpe1 = 'tpe'
        self.tpe2 = 'tpe2'
        self.name1 = 'pro'
        self.name2 = 'dep'
        self.ident1 = '{}/{}'.format(self.tpe1, self.name1)
        self.ident2 = '{}/{}'.format(self.tpe2, self.name2)
        self.main_tpe = self.base / self.tpe1
        self.main_project = self.main_tpe / self.name1
        dep = self.base / self.tpe2 / self.name2
        self.main_project.mkdir(parents=True)
        dep.mkdir(parents=True)
        self.vim.cd(str(self.main_project))

    def _set_vars(self):
        self.vim.set_pvar('config_path', str(self._config_path))
        self.vim.set_pvar('base_dirs', List(str(self.base), str(self.base2)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', self._plugins)

    @property
    def plugin_class(self):
        return Right(ProteomeNvimPlugin)

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

__all__ = ('ProteomeIntegrationSpec', 'ProteomePluginIntegrationSpec')
