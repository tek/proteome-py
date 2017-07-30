import os

from neovim.api import Nvim

from amino import List, Map, Just, Maybe, Right, Either, Path, _, __
from amino.test import fixture_path, temp_dir

from ribosome.test.integration.spec_spec import VimIntegrationSureHelpers, PluginIntegrationSpecSpec
from ribosome.test.integration.spec import IntegrationSpecBase

from proteome.project import Project
from proteome.nvim import NvimFacade
from proteome.test import Spec
from proteome.nvim_plugin import ProteomeNvimPlugin


class IntegrationCommon(Spec):

    def setup(self) -> None:
        self.cwd = Maybe.from_call(Path.cwd, exc=IOError)
        Spec.setup(self)

    def _cd_back(self) -> None:
        try:
            self.cwd.map(str).foreach(os.chdir)
        except Exception as e:
            self.log.error('error changing back to project root: {}'.format(e))

    def teardown(self) -> None:
        self._cd_back()


class ProteomeIntegrationSpec(IntegrationCommon, IntegrationSpecBase, VimIntegrationSureHelpers):

    def setup(self) -> None:
        IntegrationCommon.setup(self)
        IntegrationSpecBase.setup(self)
        self.base = temp_dir('projects', 'base')
        self.config = fixture_path('conf')
        self.type1 = 'type1'
        self.type1_base = temp_dir('projects', self.type1)
        self.type_bases = Map({self.type1_base: List(self.type1)})

    def mk_project(self, tpe: str, name: str) -> Project:
        root = temp_dir(str(self.base / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def add_projects(self, *pros: str) -> List[Project]:
        return List(*pros).map2(self.mk_project)


class ProteomePluginIntegrationSpec(IntegrationCommon, PluginIntegrationSpecSpec):

    def __init__(self) -> None:
        PluginIntegrationSpecSpec.__init__(self)
        self.log_format = '{message}'

    def setup(self) -> None:
        IntegrationCommon.setup(self)
        PluginIntegrationSpecSpec.setup(self)
        self.vim.cmd_sync('ProteomeStart')
        self._wait_for(lambda: self.vim.vars.p('projects').present)
        self.vim.cmd('ProteomePostStartup')
        self._pvar_becomes('root_dir', str(self.main_project))

    def _nvim_facade(self, vim: Nvim) -> NvimFacade:
        return NvimFacade(vim)

    def _pre_start_neovim(self) -> None:
        super()._pre_start_neovim()
        self.base = temp_dir('projects', 'base')
        self.base2 = temp_dir('projects', 'base2')
        self.typed1 = 'type1'
        self.type1_base = temp_dir('projects', self.typed1)
        self.type_bases = Map({self.type1_base: List(self.typed1)})

    def _post_start_neovim(self) -> None:
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

    def teardown(self) -> None:
        IntegrationCommon.teardown(self)
        PluginIntegrationSpecSpec.teardown(self)

    def _set_vars(self) -> None:
        self.vim.vars.set_p('config_path', str(self._config_path))
        self.vim.vars.set_p('base_dirs', List(str(self.base), str(self.base2)))
        self.vim.vars.set_p('type_base_dirs', self.type_bases.keymap(str))
        self.vim.vars.set_p('history_base', str(self.history_base))
        self.vim.vars.set_p('plugins', self._plugins)

    @property
    def plugin_class(self) -> Either[str, type]:
        return Right(ProteomeNvimPlugin)

    @property
    def _plugins(self) -> List[str]:
        return List()

    def _pre_start(self) -> None:
        pass

    @property
    def _config_path(self) -> Path:
        return Path('/dev/null')

    def _project_becomes(self, name: str) -> None:
        self._pvar_becomes_map('active', name, __['name'])

__all__ = ('ProteomeIntegrationSpec', 'ProteomePluginIntegrationSpec')
