from pathlib import Path
import os

import neovim  # type: ignore

from tryp import List, Map

from trypnv import command, NvimStatePlugin, msg_command, json_msg_command

from proteome.plugins.core import (AddByParams, Show, Create, SwitchRoot, Next,
                                   Prev, StageI, Save, RemoveByIdent,
                                   BufEnter, StageII, StageIII)
from proteome.main import Proteome
from proteome.nvim import NvimFacade
from proteome.logging import Logging


class ProteomeNvimPlugin(NvimStatePlugin, Logging):

    def __init__(self, vim: neovim.Nvim, start: bool=True) -> None:
        super(ProteomeNvimPlugin, self).__init__(NvimFacade(vim))
        self.pro = None  # type: Proteome
        self._initialized = False
        self._post_initialized = False
        if start:
            self._start_if_not_discovering_plugins()

    def _start_if_not_discovering_plugins(self):
        ''' dirty workaround for weird behaviour
        apparently, if the nvim api is acessed during the plugin
        discovery started by :UpdateRemotePlugins, the whole process
        silently fails and no remote commands are discovered at all.
        therefore, the state machine can only be started if this is a
        regular startup, as :UpdateRemotePlugins can only be executed
        from a running vim.
        because of the mentioned issue, this cannot be signaled by a vim
        variable, so an env var is used. it has to be set via the
        autocmd VimEnter.
        '''
        if '_PROTEOME_VIM_STARTED' not in os.environ:
            self.proteome_start()

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

    @command()
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


    @neovim.autocmd('VimEnter')
    def vim_enter(self):
        if not self._post_initialized:
            self._post_initialized = True
            self._post_startup()

    def _post_startup(self):
        self.pro.send_wait(StageII())
        self.vim.delay(self._finish_startup, 1.0)

    def _finish_startup(self):
        self.pro.send_wait(StageIII())

    @neovim.autocmd('BufEnter')
    def buf_enter(self):
        if self._post_initialized:
            self.pro.send(BufEnter(self.vim.current_buffer.proxy))


__all__ = ['ProteomeNvimPlugin']
