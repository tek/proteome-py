from trypnv.machine import Machine, StateMachine
from trypnv.cmd import StateCommand
from trypnv.nvim import HasNvim

from proteome.nvim import NvimFacade
from proteome.logging import Logging

from fn import F, _  # type: ignore

from tryp import Empty

from tek.tools import camelcaseify  # type: ignore

class ProteomeComponent(Machine, HasNvim, Logging):

    def __init__(self, name: str, vim: NvimFacade) -> None:
        Machine.__init__(self, name)
        HasNvim.__init__(self, vim)

    def _command_by_message_name(self, name: str):
        msg_name = camelcaseify(name)
        return self._message_handlers\
            .find_key(lambda a: a.__name__ == msg_name)

    def command(self, name: str, args: list):
        return self._command_by_message_name(name)\
            .map(lambda a: StateCommand(a[0]))\
            .map(_.call('dispatch', self, args))\
            .or_else(F(self._invalid_command, name))

    def _invalid_command(self, name):
        self.log.error(
            'plugin "{}" has no command "{}"'.format(self.name, name))
        return Empty()


class ProteomeState(StateMachine, HasNvim, Logging):

    def __init__(self, vim: NvimFacade) -> None:
        self.vim = vim
        StateMachine.__init__(self, 'proteome')
        HasNvim.__init__(self, vim)


__all__ = ['ProteomeComponent', 'ProteomeState']
