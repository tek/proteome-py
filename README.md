This plugin assists in working on multiple projects in a single neovim
instance, allowing to change the current working directory according to a
defined set of projects, and providing additional functionality like project
specific configuration, ctags handling and a git history.

# Setup
Install the plugin with [chromatin]:

```vim
let g:chromatin_rplugins += [{ 'spec': 'proteome~=11.4.0', 'name': 'proteome', 'interpreter': 'python3.6' }]
```

# General functionality
The core concept is the management of the current project, its dependencies on
the local file system and their project types.
The most basic property being manipulated is the working dir, which can be switched
to one of the projects in the set.
The main project is always present, additional ones can be added either during
startup or dynamically at runtime.

### Startup
The regular initialization flow is:

* Proteome starts during the `after/plugin/` vim phase.

* The [main project](#main-project) is determined.

* Based on the result of that, [project specific vim config](#config) is loaded.
  This is where dependency projects should be added.

* The project specific config is applied and the initial state is created.

* The *after* part of the project config is loaded.

### Commands

Projects can be configured in several ways, explained below, and added with the
`ProAdd` command.

The argument to `ProAdd` must be an identifier in the shape of either
`type/name` or `name`, where `type` is an optional identifier used for several
functions, generally the project's main language.
Optionally, a json object can be passed to configure the project's parameters.

The `ProNext` and `ProPrev` commands allow cycling through
the set of projects, changing `cwd` to the currently active project's root.

The `ProSave` command is intended to be executed with `:wall`, depending on the
user's workflow, as the plugins perform several tasks that rely on that.
If you have a 'save all' mapping, you should combine it with this.

`ProShow` prints a short overview of added projects.

`ProTo` activates a project, either by index or by name.

`ProClone` fetches a git repository into a base dir, using the main type, and
adds it as if `ProAdd` was executed.

`ProSelectAdd` runs a fuzzy selection tool (currently [Unite]) for addable
projects of the main type.

`ProSelectAddAll` runs Unite with projects from all types.

`Projects` runs Unite with all currently added projects. Two actions are
available – `activate` and `remove`, defaulting on the former.

#### Examples
```
ProAdd python/proteome
```

Tries to look up the project `proteome` of type `python`, first in the [json
config](#json-config), then the [type indexed base dirs](#type-indexed) and
finally the [explicitly typed dirs](#explicitly-typed).

```
ProAdd rails/mysite { "root": "/projects/mysite", "types": ["jade", "ruby"] }
```

Adds the project `mysite` of type `rails`, if the root dir exists, with
additional project types `jade` and `ruby` (see [Config plugin](#config)).

```
ProAdd neovim
```
Tries to look up `neovim` as project name in the json config, then uses the
main project type to search in type dirs like in the first example.

```
ProClone neovim/neovim
```
Clones the github repo for neovim into the first directory in
`g:proteome_base_dirs` using the main project's type as subdir.
If cloning was successful, add the new project and activate it.

# Configuration
General config options that should be set:

### Plugins
By default, only basic features for managing the working dir are available.
By defining this variable, additional (including custom) plugins can be
activated.

```viml
let g:proteome_plugins = [
      \ 'proteome.plugins.ctags',
      \ 'proteome.plugins.history',
      \ 'proteome.plugins.config',
      \ 'proteome.plugins.unite',
      \ ]
```

### Project base dirs
There are two kinds of base directory where proteome looks up a project identifier:

#### Type indexed
In type indexed directories, matching projects are located at the path
`basedir/type/name`.

```viml
let g:proteome_base_dirs = ['~/projects', '/data/projects']
```

Lookup for `type/name` then checks `~/projects/type/name` and
`/data/projects/type/name`.

#### Explicitly typed
Type base dirs are used to look up only the types defined in the dict's values
and match subdirs of the corresponding keys with the name of the given project.
```viml
let g:proteome_type_base_dirs = {
      \ '~/.config/nvim/bundle': ['vim', 'nvim'],
      \ }
```

Lookup for `vim/name` then checks `~/.config/nvim/bundle/name`.

### json config
Additionally, projects can be configured explicitly in json files. The variable
needs to point to a directory; all contained json files will be read.
```viml
let g:proteome_config_path = '~/.config/projects'
```
The config file format is a list of json objects like so:
```json
[
  {
    "name": "proteome",
    "type": "python",
    "root": "/projects/python/proteome"
  }
]
```

### Main Project
During startup, the principal project that's being worked on is determined
automatically, unless the variable `proteome_main_project` is set (and
optionally `proteome_main_project_type`).

Automatic discovery compares the current directory to the base dir variables
described in [Project Base Dirs](#project-base-dirs) above and extracts name
and type from the path.

This information is then used by the [Config Plugin](#config) described below.

If only a name is specified to `ProAdd`, the main project's type is used as
fallback.

# Plugins

The elements of the `proteome_plugins` variable should denote a python module
that contains a `Plugin` class inheriting the
`proteome.state.ProteomeComponent` class.
There are four built-in plugins in proteome:

## Config

Loads extra vim config from all runtimepaths based on the current project's
parameters, to run project type specific global configuration.
The location of the loaded files is every runtimepath directory's subdirectories
`project` and `project_after` (e.g. `~/.config/nvim/project_after`).
This is overridable via `g:proteome_config_project{,_after}_dir`.

For a project
named `mysite` with the main type `rails` and additional type `ruby`, the order
is:

* `project/rails.vim`
* `project/ruby.vim`
* `project/rails/mysite.vim`
* `project/all/*.vim`

and in the *after* phase, the same paths under `project_after`.

## Ctags

Generates ctags files in all projects when calling the `ProSave` command and
adds the `.tags` file in each project root to the `tags` option.
The languages used when scanning are the main project type and the optional
`langs` list parameter.

## History

```vim
let g:proteome_history_base = '~/tmp/nvim_history'
```

Creates bare git repositories for each project at
`{g:proteome_history_base}/type__name`, where a snapshot of the current project
state is commited every time `ProSave` is executed.
This provides a separate persistent undo history with git comfort without using
the project's regular git repository.

**Note**: This feature is pretty experimental, so don't be surprised if some
actions fail, especially the *pick* feature.

Only projects with the config attribute `"history": true` are considered. If
all projects should get a history, `let g:proteome_all_projects_history = 1`.
In the latter case, projects that don't have a type (like the fallback project
used for any dir) are excluded unless explicitly allowed.

Several commands for examining the history and checking out previous states are
provided:

`ProHistoryPrev` and `ProHistoryNext` check out the current project's parent
and child commits. Currently, only the whole project can be checked out, but
this will be provided for single files later.

`ProHistoryBrowse` loads a scratch buffer in a new tab and fills it with the
history, displaying the diff of the currently selected commit.
`j` and `k` are mapped to cycling up and down. Pressing `<cr>` checks out the
currently displayed commit.
`p` and `r` both try to revert the selected commit only, using `patch` and `git
revert` respectively. This can easily fail though, if the patch can't be
applied to the current working tree.
`q` closes the tab.

`ProHistoryFileBrowse` is a variant of the above that operates on a single
file, either the current buffer's or the specified argument, if any.
Only diffs for that file are shown, and when selecting a commit, only a
checkout of the file from that commit is done, followed by a new commit.

## Unite

The [three commands](#commands) described before can be called with arguments
that are passed to the unite command, like `-start-insert`.

## License

Copyright (c) Torsten Schmits.
Distributed under the terms of the [MIT License].

[MIT License]: http://opensource.org/licenses/MIT 'mit license'
[Unite]: https://github.com/Shougo/unite.vim 'unite repo'
[chromatin]: https://github.com/tek/chromatin 'chromatin repo'
