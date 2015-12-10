from pathlib import Path

import neovim  # type: ignore

from tryp import List, Map

from trypnv import command, NvimStatePlugin, msg_command

from proteome.plugins.core import (AddByName, Show, Create, SwitchRoot, Next,
                                   Prev, Init, Save)
from proteome.main import Proteome
from proteome.nvim import NvimFacade
from proteome.logging import Logging


class ProteomeNvimPlugin(NvimStatePlugin, Logging):

    def __init__(self, vim: neovim.Nvim) -> None:
        super(ProteomeNvimPlugin, self).__init__(NvimFacade(vim))
        self.pro = None  # type: Proteome

    def state(self):
        return self.pro

    @neovim.command('ProteomeReload', nargs=0)
    def proteome_reload(self):
        self.proteome_quit()
        self.proteome_start()

    @command()
    def proteome_quit(self):
        if self.pro is not None:
            self.vim.clean()
            self.pro = None

    @command()
    def proteome_start(self):
        config_path = self.vim.ps('config_path')\
            .get_or_else('/dev/null')
        bases = self.vim.pl('base_dirs')\
            .get_or_else(List())\
            .map(Path)
        type_bases = self.vim.pd('type_base_dirs')\
            .get_or_else(Map())\
            .keymap(Path)\
            .valmap(List.wrap)
        plugins = self.vim.pl('plugins') | List()
        self.pro = Proteome(self.vim, Path(config_path), plugins, bases,
                            type_bases)
        self.pro.send(Init())
        self.vim.vim.call('ptplugin#runtime_after')

    @command()
    def pro_plug(self, plug_name, cmd_name, *args):
        self.pro.plug_command(plug_name, cmd_name, args)

    @msg_command(Create)
    def pro_create(self):
        pass

    @msg_command(AddByName)
    def pro_add(self):
        pass

    @msg_command(Show, sync=True)
    def pro_show(self):
        pass

    @msg_command(SwitchRoot)
    def pro_to(self):
        pass

    @msg_command(Next)
    def pro_next(self):
        pass

    @msg_command(Prev)
    def pro_prev(self):
        pass

    @msg_command(Save)
    def pro_save(self):
        pass


__all__ = ['ProteomeNvimPlugin']
