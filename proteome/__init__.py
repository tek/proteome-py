import neovim

from amino import List, Map, __, _

from toolz import merge

from ribosome import command, msg_command, json_msg_command, AutoPlugin
from ribosome.unite import mk_unite_candidates, mk_unite_action
from ribosome.unite.plugin import unite_plugin
from ribosome.settings import Config, RequestHandler

from proteome.components.core import (AddByParams, Show, Create, SetProject, Next, Prev, Save, RemoveByIdent, BufEnter,
                                      CloneRepo)
from proteome.components.history.messages import (HistoryPrev, HistoryNext, HistoryStatus, HistoryLog, HistoryBrowse,
                                                  HistoryBrowseInput, HistorySwitch, HistoryPick, HistoryRevert,
                                                  HistoryFileBrowse)
from proteome.components.history.main import HistoryComponent
from proteome.components.unite import UniteSelectAdd, UniteSelectAddAll, UniteProjects, UniteNames, Plugin as Unite
from proteome.components.config import Config as ConfigC
from proteome.env import Env
from proteome.components.ctags.main import Ctags
from proteome.components.core.main import Core
from proteome.settings import ProteomeSettings
from proteome.components.core.message import Load

unite_candidates = mk_unite_candidates(UniteNames)
unite_action = mk_unite_action(UniteNames)


addable = dict(complete='customlist,ProCompleteAddableProjects')
projects = dict(complete='customlist,ProCompleteProjects')


def mk_config(**override) -> Config:
    defaults = dict(
        name='proteome',
        prefix='pro',
        state_type=Env,
        components=Map(ctags=Ctags, core=Core, config=ConfigC, history=HistoryComponent, unite=Unite),
        settings=ProteomeSettings(),
        request_handlers=List(
            RequestHandler.json_msg_cmd(AddByParams)('Add', bang=True, **addable),
            RequestHandler.json_msg_cmd(Load)('Load'),
        ),
        core_components=List('core'),
        default_components=List('config', 'history', 'unite', 'ctags'),
    )
    actual = merge(defaults, override)
    return Config(**actual)


config = mk_config()


@unite_plugin('pro')
class ProteomeNvimPlugin(AutoPlugin):

    @command()
    def pro_plug(self, plug_name, cmd_name, *args):
        self.root.plug_command(plug_name, cmd_name, args)

    @msg_command(Create)
    def pro_create(self):
        pass

    @neovim.function('ProCompleteProjects', sync=True)
    def pro_complete_projects(self, args):
        lead, line, pos = args
        return self.root.data.projects.idents.filter(__.startswith(lead))

    @neovim.function('ProCompleteAddableProjects', sync=True)
    def pro_complete_addable_projects(self, args):
        lead, line, pos = args
        return self.root.data.addable.filter(__.startswith(lead))

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
        self.root.send(BufEnter(self.vim.buffer.proxy))

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
        return self.root.data.main_addable

    @unite_candidates('all_addable')
    def pro_unite_all_addable(self, args):
        return self.root.data.addable

    @unite_candidates('projects')
    def pro_unite_projects(self, args):
        return self.root.data.all_projects / _.name

    @unite_action('add_project')
    def pro_unite_add_project(self, ident):
        return AddByParams(ident, options=Map())

    @unite_action('activate_project')
    def pro_unite_activate_project(self, ident):
        return SetProject(ident)

    @unite_action('delete_project')
    def pro_unite_delete_project(self, ident):
        return RemoveByIdent(ident)

__all__ = ('ProteomeNvimPlugin', 'config')
