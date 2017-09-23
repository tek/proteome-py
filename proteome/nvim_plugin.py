import neovim

from amino import List, Map, __, _, Path, Nil, Either, Lists, L, Try, Right, do

from ribosome import command, msg_command, json_msg_command, AutoPlugin
from ribosome.unite import mk_unite_candidates, mk_unite_action
from ribosome.unite.plugin import unite_plugin
from ribosome.settings import (PluginSettings, Config, RequestHandler, path_setting, path_list_setting, setting_ctor,
                               path_list)

from proteome.plugins.core import (AddByParams, Show, Create, SetProject, Next, Prev, Save, RemoveByIdent, BufEnter,
                                   CloneRepo)
from proteome.plugins.history.messages import (HistoryPrev, HistoryNext, HistoryStatus, HistoryLog, HistoryBrowse,
                                               HistoryBrowseInput, HistorySwitch, HistoryPick, HistoryRevert,
                                               HistoryFileBrowse)
from proteome.plugins.unite import UniteSelectAdd, UniteSelectAddAll, UniteProjects, UniteNames
from proteome.env import Env
from proteome.plugins.ctags.main import Ctags

unite_candidates = mk_unite_candidates(UniteNames)
unite_action = mk_unite_action(UniteNames)

config_path_help = '''Each json file in this directory is read to populate the list of project configurations.
Here you can either define independent projects that can be added with `ProAdd!`:
```
{
"name": ".sbt",
"type": "scala",
"langs": ["scala"],
"root": "~/.sbt/0.13"
}
```
Or you can amend projects that are located in one of the project base dirs, for example to set additional languages.
'''

base_dirs_help = '''A list of directories that are searched for projects of the `<type>/<name>` structure. Types are
categories grouping projects by language or other, arbitrary, criteria. When adding a project with `ProAdd! type/name`,
it is matched against these paths.
'''

type_base_dirs_help = '''A dictionary of directories mapped to lists of strings defining project types.
A directory is searched when adding projects of a type matching one of the corresponding types.
'''


@do
def cons_type_base_dirs(data: dict) -> Either[str, Map[Path, List[str]]]:
    keys, values = Lists.wrap(data.items()).unzip
    paths = yield path_list(keys)
    types = yield values.traverse(__.traverse(L(Try)(Path, _), Either), Either)
    yield Right(Map(paths.zip(types)))


type_base_dirs_setting = setting_ctor(dict, cons_type_base_dirs)


class ProteomeSettings(PluginSettings):

    def __init__(self) -> None:
        super().__init__()
        self.config_path = path_setting('config_path', 'config directory', config_path_help, True, Path('/dev/null'))
        self.base_dirs = path_list_setting('base_dirs', 'project base dirs', base_dirs_help, True, Nil)
        self.type_base_dirs = type_base_dirs_setting('type_base_dirs', 'project type base dir map', type_base_dirs_help,
                                                     True, Nil)


addable = dict(complete='customlist,ProCompleteAddableProjects')
projects = dict(complete='customlist,ProCompleteProjects')


config = Config(
    name='proteome',
    prefix='pro',
    state_type=Env,
    components=Map(ctags=Ctags),
    settings=ProteomeSettings(),
    request_handlers=List(
        RequestHandler.json_msg_cmd(AddByParams)('Add', bang=True, **addable)
    ),
    core_components=List('proteome.plugins.core'),
    default_components=List('proteome.plugins.config', 'proteome.plugins.history', 'proteome.plugins.unite', 'ctags'),
)


@unite_plugin('pro')
class ProteomeNvimPlugin(AutoPlugin):

    @command()
    def pro_plug(self, plug_name, cmd_name, *args):
        self.pro.plug_command(plug_name, cmd_name, args)

    @msg_command(Create)
    def pro_create(self):
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
