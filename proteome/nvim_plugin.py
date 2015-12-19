from pathlib import Path

import neovim  # type: ignore

from tryp import List, Map

from trypnv import command, NvimStatePlugin, msg_command, json_msg_command

from proteome.plugins.core import (AddByParams, Show, Create, SetProject, Next,
                                   Prev, StageI, Save, RemoveByIdent, BufEnter,
                                   StageII, StageIII, StageIV)
from proteome.main import Proteome
from proteome.nvim import NvimFacade
from proteome.logging import Logging


class ProteomeNvimPlugin(NvimStatePlugin, Logging):

    def __init__(self, vim: neovim.Nvim) -> None:
        super(ProteomeNvimPlugin, self).__init__(NvimFacade(vim).proxy)
        self.pro = None  # type: Proteome
        self._initialized = False
        self._post_initialized = False

    def state(self):
        return self.pro

    @command()
    def proteome_reload(self):
        self.proteome_quit()
        self.proteome_start()
        self._post_startup()

    @command()
    def proteome_quit(self):
        if self.pro is not None:
            self.vim.clean()
            self.pro.stop()
            self.pro = None

    @command(sync=True)
    def proteome_start(self):
        config_path = self.vim.ppath('config_path')\
            .get_or_else(Path('/dev/null'))
        bases = self.vim.ppathl('base_dirs')\
            .get_or_else(List())\
            .map(Path)
        type_bases = self.vim.pd('type_base_dirs')\
            .get_or_else(Map())\
            .keymap(lambda a: Path(a).expanduser())\
            .valmap(List.wrap)
        plugins = self.vim.pl('plugins') | List()
        self.pro = Proteome(self.vim.proxy, Path(config_path), plugins, bases,
                            type_bases)
        self.pro.start()
        self.pro.send(StageI())

    @command()
    def pro_plug(self, plug_name, cmd_name, *args):
        self.pro.plug_command(plug_name, cmd_name, args)

    @msg_command(Create)
    def pro_create(self):
        pass

    @json_msg_command(AddByParams)
    def pro_add(self):
        pass

    @msg_command(RemoveByIdent)
    def pro_remove(self):
        pass

    @msg_command(Show, sync=True)
    def pro_show(self):
        pass

    @msg_command(SetProject)
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

    # TODO start terminal at root dir
    # @msg_command(Term)
    # def pro_term(self):
        # pass

    @neovim.autocmd('VimEnter')
    def vim_enter(self):
        if not self._post_initialized:
            self._post_initialized = True
            self._post_startup()

    def _post_startup(self):
        self.pro.send(StageII().at(1))
        self.pro.send(StageIII().at(1))
        self.pro.send(StageIV().at(1))

    @neovim.autocmd('BufEnter')
    def buf_enter(self):
        if self._post_initialized:
            self.pro.send(BufEnter(self.vim.current_buffer.proxy))


__all__ = ['ProteomeNvimPlugin']
