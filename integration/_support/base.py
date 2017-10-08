import os

from amino import List, Map, Just, Right, Either, Path, __

from kallikrein import kf, Expectation
from kallikrein.matchers.either import be_right
from amino.test import fixture_path, temp_dir

from ribosome.test.integration.spec_spec import VimIntegrationSureHelpers, PluginIntegrationSpecSpec
from ribosome.test.integration.spec import IntegrationSpecBase
from ribosome.test.integration.klk import AutoPluginIntegrationKlkSpec, later

from proteome.project import Project
from proteome.test import Spec
from proteome.nvim_plugin import ProteomeNvimPlugin
from proteome.components.core.message import Initialized


class IntegrationCommon(Spec):

    def setup(self) -> None:
        self.cwd = Either.catch(Path.cwd, exc=IOError)
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


class ProteomePluginIntegrationSpecBase(IntegrationCommon):

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
        self.vim.cd(self.main_project)

    def _set_vars(self) -> None:
        self.vim.vars.set_p('config_path', str(self._config_path))
        self.vim.vars.set_p('base_dirs', List(str(self.base), str(self.base2)))
        self.vim.vars.set_p('type_base_dirs', self.type_bases.keymap(str))
        self.vim.vars.set_p('history_base', str(self.history_base))
        self.vim.vars.set_p('components', self.components)

    @property
    def components(self) -> List[str]:
        return List()

    def project_becomes(self, name: str) -> Expectation:
        return self.pvar_becomes_map('active', name, __['name'])

    @property
    def _config_path(self) -> Path:
        return Path('/dev/null')

    @property
    def _prefix(self) -> str:
        return 'proteome'


class ProteomePluginIntegrationSpec(ProteomePluginIntegrationSpecBase, PluginIntegrationSpecSpec):

    def __init__(self) -> None:
        PluginIntegrationSpecSpec.__init__(self)
        self.log_format = '{message}'

    def setup(self) -> None:
        IntegrationCommon.setup(self)
        PluginIntegrationSpecSpec.setup(self)
        self.vim.cmd_once_defined('ProteomeStage1')
        self.cmd_sync('ProteomeStage2')
        self.cmd_sync('ProteomeStage3')
        self.cmd_sync('ProteomeStage4')
        self._wait_for(lambda: self.vim.vars.p('projects').present)
        self._pvar_becomes('root_dir', str(self.main_project))

    def teardown(self) -> None:
        IntegrationCommon.teardown(self)
        PluginIntegrationSpecSpec.teardown(self)

    @property
    def plugin_class(self) -> Either[str, type]:
        return Right(ProteomeNvimPlugin)

    def _pre_start(self) -> None:
        pass


class AISpec(ProteomePluginIntegrationSpecBase, AutoPluginIntegrationKlkSpec):

    def setup(self) -> None:
        IntegrationCommon.setup(self)
        AutoPluginIntegrationKlkSpec.setup(self)
        self.vim.cmd_once_defined('ProteomeStage1')
        self.cmd_sync('ProteomeStage2')
        self.cmd_sync('ProteomeStage3')
        self.cmd_sync('ProteomeStage4')
        later(kf(self.vim.vars.p, 'projects').must(be_right))
        self.pvar_becomes('root_dir', str(self.main_project))
        # self.seen_message(Initialized)

    def teardown(self) -> None:
        IntegrationCommon.teardown(self)
        AutoPluginIntegrationKlkSpec.teardown(self)


class DefaultSpec(AISpec):

    def config_name(self) -> str:
        return 'config'

    def module(self) -> str:
        return 'proteome.nvim_plugin'

    @property
    def plugin_prefix(self) -> str:
        return 'Pro'

__all__ = ('ProteomeIntegrationSpec', 'ProteomePluginIntegrationSpec', 'AISpec', 'DefaultSpec')
