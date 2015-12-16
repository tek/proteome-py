from pathlib import Path  # type: ignore

from toolz.itertoolz import cons

from fn import _  # type: ignore

from tryp import List, may, Map

from trypnv.nvim import AsyncVimProxy

from proteome.nvim import NvimFacade
from proteome.env import Env
from proteome.state import ProteomeState
from proteome.project import Projects


class Proteome(ProteomeState):

    def __init__(
            self,
            vim: NvimFacade,
            config_path: Path,
            plugins: List[str],
            bases: List[Path],
            type_bases: Map[Path, List[str]],
    ) -> None:
        self._config_path = config_path
        self._bases = bases
        self._type_bases = type_bases
        core = 'proteome.plugins.core'
        ProteomeState.__init__(self, vim, List.wrap(cons(core, plugins)))

    def init(self):
        return Env(  # type: ignore
            config_path=self._config_path,
            bases=self._bases,
            type_bases=self._type_bases,
            projects=Projects()
        )

    @property
    def projects(self):
        return self.env.projects

__all__ = ['Proteome']
