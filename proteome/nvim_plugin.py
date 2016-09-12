from pathlib import Path

import neovim

from amino import List, Map, __, F, _

from ribosome import command, NvimStatePlugin, msg_command, json_msg_command

from proteome.plugins.core import (
    AddByParams, Show, Create, SetProject, Next, Prev, StageI,
    Save, RemoveByIdent, BufEnter, StageII, StageIII, StageIV, CloneRepo
)
from proteome.plugins.history.messages import (HistoryPrev, HistoryNext,
                                               HistoryStatus, HistoryLog,
                                               HistoryBrowse,
                                               HistoryBrowseInput,
                                               HistorySwitch, HistoryPick,
                                               HistoryRevert,
                                               HistoryFileBrowse)
from proteome.main import Proteome
from proteome.nvim import NvimFacade
from proteome.logging import Logging
from proteome.plugins.unite import (UniteSelectAdd, UniteSelectAddAll,
                                    UniteProjects)
from proteome.plugins.unite import Id as Unite


def unite_candidates(name):
    handler = getattr(Unite, '{}_candidates'.format(name))
    def uc_wrap(f):
        @neovim.function(handler, sync=True)
        def f_wrap(*a, **kw):
            return f(*a, **kw) / (lambda a: {'word': a})
        return f_wrap
    return uc_wrap


def _unite_word(args):
    first = List.wrap(args).lift(0)
    candidates = (
        first.to_list.join
        if first.exists(lambda a: isinstance(a, list))
        else first
    )
    return candidates / Map // __.get('word')


def unite_action(name):
    handler = getattr(Unite, name)
    def uc_wrap(f):
        @neovim.function(handler)
        def f_wrap(self, args):
            _unite_word(args) / F(f, self) % self.pro.send
        return f_wrap
    return uc_wrap


class ProteomeNvimPlugin(NvimStatePlugin, Logging):

    def __init__(self, vim: neovim.Nvim) -> None:
        super().__init__(NvimFacade(vim))
        self.pro = None
        self._post_initialized = False

    @property
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
        config_path = self.vim.vars.ppath('config_path')\
            .get_or_else(Path('/dev/null'))
        bases = self.vim.vars.ppathl('base_dirs')\
            .get_or_else(List())\
            .map(Path)
        type_bases = self.vim.vars.pd('type_base_dirs')\
            .get_or_else(Map())\
            .keymap(lambda a: Path(a).expanduser())\
            .valmap(List.wrap)
        plugins = self.vim.vars.pl('plugins') | List()
        self.pro = Proteome(self.vim.proxy, Path(config_path), plugins, bases,
                            type_bases)
        self.pro.start()
        self.pro.wait_for_running()
        self.pro.send(StageI())

    @neovim.autocmd('VimEnter')
    def vim_enter(self):
        if not self._post_initialized:
            self.proteome_post_startup()

    @command()
    def proteome_post_startup(self):
        self._post_initialized = True
        if self.pro is not None:
            self.pro.send(StageII().at(1))
            self.pro.send(StageIII().at(1))
            self.pro.send(StageIV().at(1))
        else:
            self.log.error('proteome startup failed')

    @command()
    def pro_plug(self, plug_name, cmd_name, *args):
        self.pro.plug_command(plug_name, cmd_name, args)

    @msg_command(Create)
    def pro_create(self):
        pass

    addable = dict(complete='customlist,ProCompleteAddableProjects')
    projects = dict(complete='customlist,ProCompleteProjects')

    @json_msg_command(AddByParams, **addable)
    def pro_add(self):
        pass

    @neovim.function('ProCompleteProjects', sync=True)
    def pro_complete_projects(self, args):
        lead, line, pos = args
        return self.pro.data.projects.idents.filter(__.startswith(lead))

    @neovim.function('ProCompleteAddableProjects', sync=True)
    def pro_complete_addable_projects(self, args):
        lead, line, pos = args
        return self.pro.data.addable.filter(__.startswith(lead))

    @msg_command(RemoveByIdent, **projects)
    def pro_remove(self):
        pass

    @msg_command(Show)
    def pro_show(self):
        pass

    @msg_command(SetProject, **projects)
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

    @neovim.autocmd('BufEnter')
    def buf_enter(self):
        if self._post_initialized:
            self.pro.send(BufEnter(self.vim.buffer.proxy))

    @json_msg_command(CloneRepo)
    def pro_clone(self):
        pass

    @msg_command(HistoryPrev)
    def pro_history_prev(self):
        pass

    @msg_command(HistoryNext)
    def pro_history_next(self):
        pass

    @msg_command(HistoryStatus)
    def pro_history_status(self):
        pass

    @msg_command(HistoryLog)
    def pro_history_log(self):
        pass

    @msg_command(HistoryBrowse)
    def pro_history_browse(self):
        pass

    @msg_command(HistoryFileBrowse)
    def pro_history_file_browse(self):
        pass

    @msg_command(HistoryBrowseInput)
    def pro_history_browse_input(self):
        pass

    @msg_command(HistorySwitch)
    def pro_history_switch(self):
        pass

    @msg_command(HistoryPick)
    def pro_history_pick(self):
        pass

    @msg_command(HistoryRevert)
    def pro_history_revert(self):
        pass

    @msg_command(UniteSelectAdd)
    def pro_select_add(self):
        pass

    @msg_command(UniteSelectAddAll)
    def pro_select_add_all(self):
        pass

    @msg_command(UniteProjects)
    def projects(self):
        pass

    @unite_candidates('addable')
    def pro_unite_addable(self, args):
        return self.pro.data.main_addable

    @unite_candidates('all_addable')
    def pro_unite_all_addable(self, args):
        return self.pro.data.addable

    @unite_candidates('projects')
    def pro_unite_projects(self, args):
        return self.pro.data.all_projects / _.name

    @unite_action('add_project')
    def pro_unite_add_project(self, ident):
        return AddByParams(ident, options=Map())

    @unite_action('activate_project')
    def pro_unite_activate_project(self, ident):
        return SetProject(ident)

    @unite_action('delete_project')
    def pro_unite_delete_project(self, ident):
        return RemoveByIdent(ident)

__all__ = ('ProteomeNvimPlugin',)
