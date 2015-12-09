from pathlib import Path
import json
import os

from tryp import Maybe, Empty, Just, List, Map, may

from fn import _  # type: ignore

from trypnv import Log
from trypnv.nvim import NvimFacade, HasNvim


class Project(object):

    def __init__(
            self,
            name: str,
            root: Path,
            tpe: Maybe[str]=Empty(),
            types: List[str]=List(),
            langs: List[str]=List(),
            history: bool=True,
    ) -> None:
        self.name = name
        self.root = root
        self.tpe = tpe
        self.types = types
        self.langs = langs
        self.history = history

    @property
    def info(self) -> str:
        return '{}: {}'.format(self.name, self.root)

    def __str__(self):
        return self.info

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __eq__(self, other):
        return (
            isinstance(other, Project) and
            self.name == other.name and
            self.root == other.root and
            self.tpe == other.tpe
        )

    @property
    def ctags_langs(self):
        return (self.langs + self.tpe.toList).distinct

    @property
    def want_ctags(self):
        return not self.ctags_langs.is_empty

    @property
    def tag_file(self):
        return self.root / '.tags'

    def remove_tag_file(self):
        if self.tag_file.exists():
            self.tag_file.unlink()

    @property
    def fqn(self):
        t = self.tpe.get_or_else('notype')
        return '{}__{}'.format(t, self.name)


class Projects(object):

    def __init__(self, projects: List[Project]=List()) -> None:
        self.projects = projects

    def __add__(self, pro: Project) -> 'Projects':
        return Projects(self.projects + [pro])

    def __pow__(self, pros: List[Project]) -> 'Projects':
        return Projects(self.projects + pros)

    def show(self, names: List[str]=List()):
        if names.is_empty:
            pros = self.projects
        else:
            pros = names.flat_map(self.project)
        return pros.map(_.info)

    def project(self, name: str) -> Maybe[Project]:
        return self.projects.find(_.name == name)

    def ctags(self, names: List[str]):
        matching = names.flat_map(self.project)
        return matching

    def __str__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            ','.join(map(repr, self.projects))
        )

    def __getitem__(self, index):
        return self.projects.lift(index)

    def __len__(self):
        return len(self.projects)


def sub_path(base: Path, path: Path):
    check = lambda: path.relative_to(base)
    return Maybe.from_call(check)\
        .map(_.parts)\
        .map(List.wrap)


def sub_paths(dirs: List[Path], path: Path):
    return dirs\
        .flat_map(lambda a: sub_path(a, path))


class Resolver(object):

    def __init__(self, bases: List[Path], types: Map[Path, List[str]]) -> None:
        self.bases = bases
        self.types = types

    def type_name(self, tpe: str, name: str):
        return self.bases\
            .map(_ / tpe / name)\
            .find(lambda a: a.is_dir())\
            .or_else(lambda: self.specific(tpe, name))

    def specific(self, tpe: str, name: str):
        self.types\
            .valfilter(_.call('contains', tpe))\
            .keys\
            .map(_ / name)\
            .find(lambda a: a.is_dir())

    def dir(self, path: Path):
        return self.dir_in_bases(path)\
            .or_else(lambda: self.dir_in_types(path))

    def dir_in_bases(self, path: Path):
        return sub_paths(self.bases, path)\
            .filter(lambda a: len(a) >= 2)\
            .map(lambda a: (a[0], a[-1]))\
            .head

    def dir_in_types(self, path: Path):
        trans = lambda a, b: b.head.zip(sub_path(a, path).flat_map(_.last))
        return self.types\
            .flat_map(trans)\
            .head


class ProjectLoader(object):

    def __init__(self, config_path: Path, resolver: Resolver) -> None:
        self.resolver = resolver
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> List[Map]:
        def parse(path: Path):
            with path.open() as f:
                try:
                    return List.wrap(map(Map, json.loads(f.read())))
                except Exception as e:
                    Log.error('parse error in {}: {}'.format(path, e))
                    return List()
        if (self.config_path.is_dir()):
            return List.wrap(self.config_path.glob('*.json')) \
                .flat_map(parse)
        else:
            return parse(self.config_path)

    def resolve(self, tpe: str, name: str):
        return self.resolver.type_name(tpe, name) \
            .map(lambda a: Project(name, a))

    def json_by_name(self, name: str):
        return self.config \
            .find(lambda a: a.get('name').contains(name))

    def by_name(self, name: str):
        return self.json_by_name(name)\
            .flat_map(self.from_json)

    def from_json(self, json: Map) -> Maybe[Project]:
        def from_type(tpe: str, name: str):
            root = json.get('root') \
                .map(os.path.expanduser)\
                .get_or_else(self.resolver.type_name(tpe, name))
            return Project(name, Path(root), Just(tpe))
        return json.get('type') \
            .zip(json.get('name')) \
            .smap(from_type)

    @may
    def create(self, name: str, root: Path, **kw):
        if root.is_dir():
            return Project(name, root, **kw)


class ProjectAnalyzer(HasNvim):

    def __init__(self, vim: NvimFacade, loader: ProjectLoader) -> None:
        super(ProjectAnalyzer, self).__init__(vim)
        self.loader = loader

    def _default_detect_data(self, wd: Path):
        return self.loader.resolver.dir(wd)\
            .map(lambda a: Map({'name': a[1], 'root': str(wd), 'type': a[0]}))

    def _detect_data(self, wd: Path):
        return self.vim.pvar('project_detector')\
            .flat_map(lambda a: self.vim.call(a, str(wd)))\
            .or_else(self._default_detect_data(wd))

    @property
    def current_dir(self):
        return Path.cwd()

    @property
    def _detect_current_data(self) -> Maybe[Map]:
        return self._detect_data(self.current_dir)

    @property
    def _current_data(self) -> Maybe[Map]:
        return self.pflags.detect_current_project\
            .maybe(self._detect_current_data)\
            .get_or_else(Empty())

    @property
    def _auto_current(self):
        return self._current_data\
            .flat_map(self.loader.from_json)

    @property
    def _fallback_current(self):
        tpe = self.vim.pvar('current_project_type')
        return Project('current', self.current_dir, tpe)

    @property
    def current(self):
        return self.vim.pvar('current_project')\
            .flat_map(self.loader.by_name)\
            .or_else(self._auto_current)\
            .get_or_else(self._fallback_current)


__all__ = ['Projects', 'Project', 'ProjectLoader', 'Resolver']
