from pathlib import Path

from toolz.itertoolz import cons

from amino import List, Map, Maybe, Empty

from ribosome.nvim import NvimFacade

from proteome.env import Env
from proteome.state import ProteomeState
from proteome.project import Projects


class Proteome(ProteomeState):

    def __init__(
            self,
            vim: NvimFacade,
            config_path: Path,
            components: List[str],
            bases: List[Path],
            type_bases: Map[Path, List[str]],
            initial_projects: Maybe[Projects]=Empty()
    ) -> None:
        self._config_path = config_path
        self._bases = bases
        self._type_bases = type_bases
        self._initial_projects = initial_projects
        core = 'proteome.components.core'
        ProteomeState.__init__(self, vim, List.wrap(cons(core, components)))

    @property
    def init(self):
        return Env(
            config_path=self._config_path,
            bases=self._bases,
            type_bases=self._type_bases,
            projects=self._initial_projects | Projects()
        )

    @property
    def projects(self):
        return self.env.projects

__all__ = ('Proteome',)
