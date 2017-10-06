from amino import List, Map, __, _, Path, Nil, Either, Lists, L, Try, Right, do

from ribosome.settings import PluginSettings, path_setting, path_list_setting, setting_ctor, path_list, str_setting


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

tags_command_help = '''If your project uses an alternative program to generate its tags, set this variable to its
executable path or name. Arguments go into `g:proteome_tags_args`.
'''

tags_args_help = '''Set this to a space-separated list of arguments for the custom tags command.
You can supply a python format string containing the variables `langs`, `tag_file` and `root`.
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
        super().__init__('proteome')
        self.config_path = path_setting('config_path', 'config directory', config_path_help, True, Path('/dev/null'))
        self.base_dirs = path_list_setting('base_dirs', 'project base dirs', base_dirs_help, True, Nil)
        self.type_base_dirs = type_base_dirs_setting('type_base_dirs', 'project type base dir map', type_base_dirs_help,
                                                     True, Nil)
        self.tags_command = str_setting('tags_command', 'custom command for ctags generation', tags_command_help, True,
                                        '')
        self.tags_args = str_setting('tags_args', 'args for custom ctags command', tags_args_help, True, '')

__all__ = ('ProteomeSettings',)
