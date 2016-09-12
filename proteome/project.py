from pathlib import Path
from typing import Tuple
import json

from amino import Maybe, Empty, Just, List, Map, may, Boolean, flat_may, __, F
from amino.lazy import lazy

from fn import _

from ribosome.nvim import NvimFacade, HasNvim
from ribosome.record import field, list_field, Record
from ribosome.process import JobClient

from proteome.logging import Logging


def mkpath(path: str):
    return Path(path).expanduser()  # type: ignore


def format_path(path: Path):
    h = str(Path.home())  # type: ignore
    return str(path).replace(h, '~')


# TODO subprojects, e.g. sbt projects
class Project(Record):
    name = field(str)
    root = field(Path)
    tpe = field(Maybe, initial=Empty())
    types = list_field()
    langs = list_field()
    history = field(bool, initial=False)

    @staticmethod
    def of(name, root, tpe=Empty(), **kw):
        return Project(name=name, root=root, tpe=tpe, **kw)

    @property
    def ident(self):
        return self.tpe.map(_ + '/').get_or_else('') + self.name

    @property
    def info(self) -> str:
        return '{}: {}'.format(self.ident, format_path(self.root))

    def __str__(self):
        return self.info

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.ident))

    def __eq__(self, other):
        return (
            isinstance(other, Project) and
            self.name == other.name and
            self.root == other.root and
            self.tpe == other.tpe
        )

    def __hash__(self):
        return hash((self.name, self.root, self.tpe))

    @property
    def ctags_langs(self):
        return (self.langs + self.tpe.to_list).distinct

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

    @property
    def json(self):
        return dict(
            name=self.name,
            root=str(self.root),
            tpe=self.tpe | None,
            types=self.types,
            langs=self.langs,
        )

    @property
    def all_types(self):
        return self.tpe.to_list + self.types

    @property
    def has_type(self):
        return self.tpe.is_just

    @lazy
    def job_client(self):
        return JobClient(cwd=self.root, name=self.ident)

    def match_ident(self, ident):
        return ident in (self.ident, self.name)


class Projects(object):

    def __init__(self, projects: List[Project]=List()) -> None:
        self.projects = projects

    def __add__(self, pro: Project) -> 'Projects':
        return Projects(self.projects + [pro])

    def __sub__(self, pro: Project) -> 'Projects':
        return Projects(self.projects.without(pro))

    def __pow__(self, pros: List[Project]) -> 'Projects':
        return Projects(self.projects + pros)

    def show(self, names: List[str]=List()):
        if names.is_empty:
            pros = self.projects
        else:
            pros = names.flat_map(self.project)
        return pros.map(_.info)

    def project(self, ident: str) -> Maybe[Project]:
        @flat_may
        def try_split():
            if '/' in ident:
                tpe, name = ident.split('/', 1)
                return self.projects.find(
                    lambda a: a.name == name and a.tpe == Just(tpe))
        return self.projects.find(_.name == ident)\
            .or_else(try_split)

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

    def __contains__(self, item):
        return (
            (isinstance(item, Project) and item in self.projects) or
            (isinstance(item, str) and self.project(item).is_just)
        )

    @property
    def json(self):
        return self.projects.map(_.json)

    def index_of(self, project):
        return self.projects.index_of(project)

    def index_of_ident(self, ident):
        return self.projects.index_where(_.ident == ident)\
            .or_else(self.projects.index_where(_.name == ident))

    @property
    def idents(self):
        return self.projects.map(_.ident)


def sub_path(base: Path, path: Path):
    check = lambda: path.relative_to(str(base))
    return Maybe.from_call(check, exc=ValueError)\
        .map(_.parts)\
        .map(List.wrap)


def sub_paths(dirs: List[Path], path: Path):
    return dirs\
        .flat_map(lambda a: sub_path(a, path))


class Resolver(object):

    def __init__(self, bases: List[Path], types: Map[Path, List[str]]) -> None:
        self.bases = bases
        self.types = types

    def type_name(self, tpe: str, name: str) -> Maybe[Path]:
        return self.bases\
            .map(_ / tpe / name)\
            .find(lambda a: a.is_dir())\
            .or_else(lambda: self.specific(tpe, name))

    def specific(self, tpe: str, name: str) -> Maybe[Path]:
        return self.types\
            .valfilter(_.call('contains', tpe))\
            .k\
            .map(_ / name)\
            .find(lambda a: a.is_dir())

    def dir(self, path: Path) -> Maybe[Tuple[str, str]]:
        return self.dir_in_bases(path)\
            .or_else(lambda: self.dir_in_types(path))

    def dir_in_bases(self, path: Path) -> Maybe[Tuple[str, str]]:
        return sub_paths(self.bases, path)\
            .filter(lambda a: len(a) >= 2)\
            .map(lambda a: (a[0], a[-1]))\
            .head

    def dir_in_types(self, path: Path) -> Maybe[Tuple[str, str]]:
        trans = lambda a, b: b.head.zip(sub_path(a, path).flat_map(_.last))
        return self.types\
            .flat_map(trans)\
            .head


def content(path: Path):
    return List.wrap(path.iterdir()) if path.is_dir() else List()


def subdirs(path: Path, n: int):
    sub = content(path).filter(__.is_dir())
    return sub if n <= 1 else sub // F(subdirs, n=n - 1)


def extract_ident(path: Path):
    return (
        Just(path.parts)
        .filter(lambda a: len(a) >= 2)
        .map(lambda a: '/'.join(a[-2:]))
    )


class ProjectLoader(Logging):

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
                    self.log.error('parse error in {}: {}'.format(path, e))
                    return List()
        if (self.config_path.is_dir()):
            return List.wrap(self.config_path.glob('*.json')) \
                .flat_map(parse)
        elif self.config_path.is_file():
            return parse(self.config_path)
        else:
            return List()

    def resolve(self, tpe: str, name: str):
        return self.resolver.type_name(tpe, name)\
            .map(lambda a: Project.of(name, a, Just(tpe)))

    def resolve_ident(self, ident: str, params: Map=Map(),
                      main: Maybe[str]=Empty()):
        if '/' in ident:
            return self.resolve(*ident.split('/', 1))
        else:
            return main.flat_map(lambda a: self.resolve(a, ident))

    def json_by_name(self, name: str):
        return self.config\
            .find(lambda a: a.get('name').contains(name))

    def json_by_type_name(self, tpe, name):
        def matcher(record: Map) -> Boolean:
            return (record.get('name').contains(name) and
                    record.get('type').contains(tpe))
        return self.config\
            .find(matcher)

    def json_by_ident(self, ident: str):
        @flat_may
        def try_split():
            if '/' in ident:
                return self.json_by_type_name(*ident.split('/', 1))
        return self.json_by_name(ident)\
            .or_else(try_split)

    def json_by_root(self, root: Path):
        return self.config\
            .find(lambda a: a.get('root').map(mkpath).contains(root))

    def by_ident(self, name: str):
        return self.json_by_ident(name)\
            .flat_map(self.from_json)

    def from_json(self, json: Map) -> Maybe[Project]:
        ''' Try to instantiate a Project from the given json object.
        Convert the **type** key to **tpe** and its value to
        Maybe.
        Make sure **root** is a directory, fall back to resolution
        by **tpe/name**.
        Reinsert the root dir into the json dict, filter out all keys
        that aren't contained in Project's fields.
        Try to instantiate.
        '''
        root = json.get('root')\
            .map(mkpath)\
            .or_else(
                json.get_all('type', 'name')
                .flat_smap(self.resolver.type_name))
        valid_fields = root\
            .map(lambda a: json ** Map(root=a, tpe=json.get('type')))\
            .map(lambda a: a.at(*Project._pclass_fields))
        return Maybe.from_call(lambda: valid_fields.ssmap(Project)) | Empty()

    # TODO log error if not a dir
    # use Either
    @may
    def create(self, name: str, root: Path, **kw):
        if root.expanduser().is_dir():  # type: ignore
            return Project.of(name, root, **kw)

    def from_params(self, ident: str, root: Path, params: Map):
        parts = List(*reversed(ident.split('/', 1)))
        name = parts[0]
        tpe = parts.lift(1).or_else(params.get('type'))
        kw = params.at('types', 'langs', 'history')
        return self.create(name, root, tpe=tpe, **kw)

    @property
    def _all_long_ident(self):
        def typed_ident(base, types):
            names = subdirs(base, n=1) / _.name
            return (types // (lambda t: names / F('{}/{}'.format, t)))
        bases = self.resolver.bases // F(subdirs, n=2) // extract_ident
        typed = self.resolver.types.to_list.flat_smap(typed_ident)
        return bases + typed

    def _short_ident(self, idents):
        return idents / __.split('/') / _[-1]

    def _main_ids(self, idents, main: Maybe[str]):
        return main / (
            lambda a: idents.filter(__.startswith(a + '/'))) | List()

    def all_ident(self, main: Maybe[str]):
        all = self._all_long_ident
        m_ids = self._main_ids(all, main)
        return all + self._short_ident(m_ids)

    def main_ident(self, main: Maybe[str]):
        m_ids = self._main_ids(self._all_long_ident, main)
        return self._short_ident(m_ids)


class ProjectAnalyzer(HasNvim, Logging):

    def __init__(self, vim: NvimFacade, loader: ProjectLoader) -> None:
        super(ProjectAnalyzer, self).__init__(vim)
        self.loader = loader

    def _default_detect_data(self, wd: Path):
        type_name = self.loader.resolver.dir(wd)
        return type_name\
            .flat_smap(self.loader.json_by_type_name)\
            .map(_ + ('root', str(wd)))\
            .or_else(
                type_name
                .smap(lambda t, n: Map(type=t, root=str(wd), name=n))
            )

    def _detect_data(self, wd: Path):
        return self.loader.json_by_root(wd)\
            .or_else(
                self.vim.vars.p('project_detector')
                .flat_map(lambda a: self.vim.call(a, str(wd))))\
            .or_else(self._default_detect_data(wd))

    @property
    def main_dir(self) -> Maybe[Path]:
        return Maybe.from_call(Path.cwd, exc=IOError)

    @property
    def main_dir_or_home(self) -> Path:
        return self.main_dir | Path.home()  # type: ignore

    @property
    def _detect_main_data(self) -> Maybe[Map]:
        return self.main_dir // self._detect_data

    @property
    def _main_data(self) -> Maybe[Map]:
        return self.pflags.get('detect_main_project', True)\
            .maybe(self._detect_main_data) | Empty()

    @property
    def _auto_main(self):
        return self._main_data\
            .flat_map(self.loader.from_json)

    @property
    def _fallback_main(self):
        tpe = self.vim.vars.p('main_project_type')
        return Project.of('main', self.main_dir_or_home, tpe)

    @property
    def main(self):
        return self.vim.vars.p('main_project')\
            .flat_map(self.loader.by_ident)\
            .or_else(self._auto_main)\
            .get_or_else(self._fallback_main)

__all__ = ('Projects', 'Project', 'ProjectLoader', 'Resolver')
