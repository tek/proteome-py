from ribosome import Machine, PluginStateMachine
from ribosome.nvim import HasNvim
from ribosome.machine import ModularMachine, Transitions

from proteome.nvim import NvimFacade
from proteome.logging import Logging

from amino import List


class ProteomeComponent(ModularMachine, HasNvim, Logging):

    def __init__(self, name: str, vim: NvimFacade, parent=None) -> None:
        Machine.__init__(self, name, parent)
        HasNvim.__init__(self, vim)


class ProteomeState(PluginStateMachine, HasNvim, Logging):

    def __init__(self, vim: NvimFacade, plugins: List[str]) -> None:
        HasNvim.__init__(self, vim)
        PluginStateMachine.__init__(self, 'proteome', plugins)


class ProteomeTransitions(Transitions, HasNvim):

    def __init__(self, machine, *a, **kw):
        Transitions.__init__(self, machine, *a, **kw)
        HasNvim.__init__(self, machine.vim)

__all__ = ('ProteomeComponent', 'ProteomeState', 'ProteomeTransitions')
