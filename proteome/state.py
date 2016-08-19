from ribosome import Machine, RootMachine
from ribosome.nvim import HasNvim
from ribosome.machine import ModularMachine, Transitions

from proteome.nvim import NvimFacade
from proteome.logging import Logging


class ProteomeComponent(ModularMachine, HasNvim, Logging):

    def __init__(self, name: str, vim: NvimFacade, parent=None) -> None:
        Machine.__init__(self, parent)
        HasNvim.__init__(self, vim)


class ProteomeState(RootMachine, Logging):

    @property
    def name(self):
        return 'proteome'


class ProteomeTransitions(Transitions, HasNvim):

    def __init__(self, machine, *a, **kw):
        Transitions.__init__(self, machine, *a, **kw)
        HasNvim.__init__(self, machine.vim)

__all__ = ('ProteomeComponent', 'ProteomeState', 'ProteomeTransitions')
