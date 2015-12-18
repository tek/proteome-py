from trypnv import Machine, PluginStateMachine
from trypnv.nvim import HasNvim

from proteome.nvim import NvimFacade
from proteome.logging import Logging

from tryp import List


class ProteomeComponent(Machine, HasNvim, Logging):

    def __init__(self, name: str, vim: NvimFacade) -> None:
        Machine.__init__(self, name)
        HasNvim.__init__(self, vim)


class ProteomeState(PluginStateMachine, HasNvim, Logging):

    def __init__(self, vim: NvimFacade, plugins: List[str]) -> None:
        self.vim = vim
        PluginStateMachine.__init__(self, 'proteome', plugins)
        HasNvim.__init__(self, vim)


__all__ = ['ProteomeComponent', 'ProteomeState']
