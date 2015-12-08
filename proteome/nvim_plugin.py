from pathlib import Path

import neovim  # type: ignore

from tryp import List

from trypnv import command, NvimStatePlugin, msg_command

from proteome.plugins.core import (AddByName, Show, Create, SwitchRoot, Next,
                                   Prev)
from proteome.main import Proteome
from proteome.nvim import NvimFacade


class ProteomeNvimPlugin(NvimStatePlugin):

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
            .get_or_else(List())
        plugins = self.vim.pl('plugins') | List()
        self.pro = Proteome(self.vim, Path(config_path), plugins, bases)
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


__all__ = ['NvimStatePlugin']
