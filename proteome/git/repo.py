import io
from pathlib import Path
from itertools import takewhile
from datetime import datetime
from asyncio import coroutine

from fn import _, F

import pyrsistent

from dulwich import repo, config, porcelain
from dulwich.repo import BASE_DIRECTORIES, OBJECTDIR
from dulwich.object_store import DiskObjectStore
from dulwich.objects import Commit
from dulwich.patch import write_object_diff
from dulwich.index import build_file_from_blob

from amino import may, List, Maybe, Map, Empty, Just, __, Left, Either
from amino.logging import Logging
from amino.transformer import Transformer
from amino.lazy import lazy
from amino.task import Try, Task
from amino.lazy_list import LazyList

from ribosome.record import field, bool_field, maybe_field, Record
from ribosome.process import JobClient

from proteome.project import Project


_master_ref = 'refs/heads/master'


def format_since(stamp):
    elapsed = datetime.now() - datetime.fromtimestamp(stamp)
    if elapsed.days:
        t = '{} days'.format(elapsed.days)
    else:
        sec = elapsed.seconds
        s = '{}s'.format(sec % 60)
        if sec >= 60:
            m = '{}m'.format(sec % 3600 // 60)
            if sec >= 3600:
                h = '{}h'.format(sec // 3600)
                t = '{} {}'.format(h, m)
            else:
                t = '{} {}'.format(m, s)
        else:
            t = s
    return '{} ago'.format(t)


def file_diff(f, store, old_tree, new_tree, path):
    changes = store.tree_changes(old_tree, new_tree)
    for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) in changes:
        if newpath.decode() == path:
            write_object_diff(f, store, (oldpath, oldmode, oldsha),
                                        (newpath, newmode, newsha))


class RepoState(Record):
    current = maybe_field(str)


class ProjectRepoState(RepoState):
    project = field(Project)


class Diff(Logging):

    def __init__(self, repo, target, parent):
        self.repo = repo
        self.target = target
        self.parent = parent

    @lazy
    def show(self):
        return self.patch_lines

    @property
    def patch_lines(self):
        return self._patch_lines(self.patch)

    @lazy
    def patch(self):
        return self._patch(
            lambda f:
            porcelain.diff_tree(self.repo.repo, self.parent, self.target, f)
        )

    def show_file(self, path: str):
        return self._patch_lines(self.file_patch(path))

    def file_patch(self, path: str):
        return self._patch(
            lambda f:
            file_diff(f, self.repo.repo.object_store, self.parent, self.target,
                      path)
        )

    def _patch(self, diff):
        f = io.BytesIO()
        try:
            diff(f)
        except Exception as e:
            return Left(e)
        else:
            p = f.getvalue()
            if p:
                nl = '\n\ No newline at end of file'
                return Try(p.decode) / __.replace(nl, '')
            else:
                return Left('empty diff')

    def _patch_lines(self, patch):
        return patch / __.splitlines() | ['no diff']

    @property
    def revert(self):
        return Diff(self.repo, self.parent, self.target)

    @property
    def empty(self):
        return self.patch.is_left


class CommitInfo(Record):
    num = field(int)
    hex = field(str)
    timestamp = field(int)
    current = bool_field()
    repo = pyrsistent.field(
        mandatory=True,
        invariant=lambda a: (isinstance(a, Repo), 'repo is not a Repo')
    )
    diff = maybe_field(Diff)

    @staticmethod
    def create(index, commit: Commit, repo):
        id = commit.id.decode()
        d = repo.parent(commit) / _.tree / F(Diff, repo, commit.tree)
        return CommitInfo(num=index, hex=id, timestamp=commit.commit_time,
                          current=repo.current.contains(id),
                          repo=repo, diff=d)

    @property
    def since(self):
        return format_since(self.timestamp)

    @property
    def num_since(self):
        return '#{} {}'.format(self.num, self.since)

    @property
    def log_format(self):
        prefix = '*' if self.current else ' '
        return '{} {} {}'.format(prefix, self.hex[:8], self.since)

    def browse_format(self, show_diff: bool, path: Maybe[Path]=Empty()):
        prefix = '*' if self.current else ' '
        info = '{}  {}    {}'.format(prefix, self.hex[:8], self.since)
        diff = self.show_diff(path) if show_diff else Empty()
        return List(info) + (diff | List())

    def show_diff(self, path: Maybe[Path]=Empty()):
        return self.diff / (lambda d: path.cata(d.show_file, lambda: d.show))

    @property
    def empty(self):
        return self.diff.exists(_.empty)


class DulwichRepo(repo.Repo, Logging):

    def __init__(self, store, worktree=None) -> None:
        super().__init__(str(store))
        self.store = store
        self.bare = False
        if worktree is not None:
            self._init_history_files(worktree)
        (
            Try(self.get_config().get, b'core', b'worktree') /
            __.decode() %
            self._set_worktree
        )

    def _set_worktree(self, path):
        self.path = path

    @property
    def excludesfile_rel(self):
        return str(Path('info') / 'exclude')

    @property
    def excludesfile(self):
        return Path(self.store) / self.excludesfile_rel

    def _init_history_files(self, worktree):
        desc = 'proteome history repo for {}'.format(worktree).encode()
        self._put_named_file('description', desc)
        f = io.BytesIO()
        cf = config.ConfigFile()
        cf.set(b'core', b'repositoryformatversion', b'0')
        cf.set(b'core', b'filemode', b'true')
        cf.set(b'core', b'bare', False)
        cf.set(b'core', b'logallrefupdates', True)
        cf.set(b'core', b'worktree', str(worktree).encode())
        cf.set(b'user', b'name', b'proteome')
        cf.set(b'user', b'email', b'proteome@nvim.local')
        cf.write_to_file(f)
        self._put_named_file('config', f.getvalue())
        self._put_named_file(self.excludesfile_rel, b'')

    def set_excludes(self, f):
        if f.is_file():
            self._put_named_file(self.excludesfile_rel, f.read_bytes())

    @staticmethod
    def create(worktree: Path, store: Path):
        List.wrap(BASE_DIRECTORIES)\
            .smap(store.joinpath) %\
            __.mkdir(parents=True, exist_ok=True)
        DiskObjectStore.init(str(store / OBJECTDIR))
        repo = DulwichRepo(store, worktree)
        repo.refs.set_symbolic_ref(b'HEAD', _master_ref.encode())
        return repo

    @staticmethod
    def at(worktree: Path, store: Path):
        return (
            DulwichRepo(store)
            if (store / OBJECTDIR).exists()
            else DulwichRepo.create(worktree, store)
        )

    def path_blob(self, commit_sha, path):
        tree_id = self[commit_sha.encode()].tree
        tree = self.get_object(tree_id)
        mode, sha = tree.lookup_path(self.get_object, str(path).encode())
        return self[sha], mode


class Repo(Logging):

    def __init__(self, repo, state: RepoState) -> None:
        self.repo = repo
        self.state = state

    def init(self, excludes: Maybe[Path]):
        excludes / self.repo.set_excludes
        return Just(self.state)

    def copy(self, new_state: RepoState):
        return self.__class__(self.repo, new_state)  # type: ignore

    def __str__(self):
        return '{}({}, {})'.format(
            self.__class__.__name__, self.repo.path, self.state)

    def ref(self, name):
        return Maybe.from_call(lambda: self.repo.refs[name.encode()],
                               exc=KeyError)

    @property
    def current(self):
        return self.state.current.or_else(self._head_id)

    @property
    def current_b(self):
        return self.current / __.encode()

    @property
    def _master_id_b(self):
        return self.ref(_master_ref)

    @property
    def _master_id(self):
        return self._master_id_b / __.decode()

    @property
    def _head_id_b(self) -> Either[str, bytes]:
        return Try(self.repo.head)

    @property
    def _head_id(self) -> Either[str, str]:
        return self._head_id_b / __.decode()

    @property
    def _master_ref_b(self):
        return _master_ref.encode()

    @property
    def index(self):
        return self.repo.open_index()

    @property
    def status(self):
        return porcelain.status(self.repo)

    @property
    def job_client(self):
        return JobClient(cwd=self.base, name=self.base.name)

    @coroutine
    def add_commit_all(self, project, executor, msg):
        if (yield from executor.add_all(project)).success and self.index_dirty:
            return self.commit_master(msg)
        else:
            return Just(self.state)

    @property
    def base(self):
        return Path(self.repo.path)

    @property
    def index_dirty(self):
        f = lambda: Map(self.status.staged).v.exists(bool)
        return Try(f) | True

    # FIXME checking out master seems to change files to wrong states sometimes
    def commit_master(self, msg):
        committed = Try(
            self.repo.do_commit,
            message=msg.encode(),
            ref=self._master_ref_b,
        )
        return committed // (lambda a: self.reset_master())

    def to_master(self):
        return self.master_commit.map(self._switch)

    def reset_master(self):
        def set_ref(ref):
            self.repo[b'HEAD'] = ref.encode()
            return self.state.set(current=Just(ref))
        return self._master_id / set_ref

    @property
    def master_commit(self):
        return self._master_id_b // F(Try, self.repo.get_object)

    @lazy
    def history(self):
        return self.history_raw / _.commit

    @property
    def history_raw(self):
        return LazyList(self._master_id.map(self.history_at) | [])

    def history_at(self, sha):
        return self.repo.get_walker(include=[sha.encode()])

    def file_history(self, path: Path):
        relpath = str(self.relpath(path) | '///')
        def filt(entry):
            paths = (
                List.wrap(entry.changes()) //
                (F(_.new.path) >> Maybe) /
                __.decode()
            )
            return paths.contains(relpath)
        return self.history_raw.filter(filt) / _.commit

    def relpath(self, path: Path):
        return (Try(path.relative_to, self.base).to_maybe
                if path.is_absolute()
                else Just(path))

    def abspath(self, path):
        return Path(path) if Path(path).is_absolute() else self.base / path

    @property
    def history_ids(self):
        return self.history.map(_.id)

    @property
    def head_commit(self) -> Either[str, Commit]:
        return self._head_id_b // F(Try, self.repo.get_object)

    def _switch(self, commit: Commit):
        self._checkout_commit(commit)
        return self.state.set(current=Just(commit.id.decode()))

    def _checkout_commit(self, commit):
        self.repo.reset_index(commit.tree)

    def commit_info(self, index, commit):
        return CommitInfo.create(index, commit, self)

    @property
    def log_formatted(self):
        return self.history_info / _.log_format

    def file_log_formatted(self, path):
        return self.file_history_info(path) / _.log_format

    def _history_info(self, commits):
        return commits\
            .with_index\
            .smap(self.commit_info)\
            .filter_not(_.empty)

    @lazy
    def history_info(self):
        return self._history_info(self.history)

    def file_history_info(self, path: Path):
        return self._history_info(self.file_history(path))

    @lazy
    def current_commit(self):
        return self.current_b / self.repo.get_object

    @property
    def current_commit_info(self):
        com = self.current_commit.to_maybe
        index = com // self.history.index_of
        return index.ap2(com, self.commit_info)

    def future_at(self, id):
        def search(hist):
            all = List.wrap(takewhile(_.commit.id != id, hist))
            return all.reversed
        return self._master_id / self.history_at / search | iter([])

    def parents(self, commit):
        return List.wrap(commit.parents) / self.repo.get_object

    def parent(self, commit):
        return self.parents(commit).head

    def child(self, id, n=0):
        return self.future_at(id).lift(n - 1) / _.commit

    def prev(self):
        return self.current_commit // self.parent / self._switch

    def next(self):
        return self.current_commit // self.child / self._switch

    def select(self, num):
        return self.history.lift(num) / self._switch

    def checkout_file(self, commit_sha, path):
        path_s = str(self.abspath(path))
        return (Task.call(self.repo.path_blob, commit_sha, path)
                .map2(F(build_file_from_blob, target_path=path_s)))


class RepoT(Transformer[Repo]):

    @property
    def repo(self):
        return self.val

    def pure(self, s: Maybe[RepoState]):
        new_state = s | self.repo.state
        return self.repo.copy(new_state)

    @property
    def state(self):
        return self.repo.state


class RepoAdapter(Logging):

    def __init__(self, work_tree: Path, git_dir: Maybe[Path]=Empty()) -> None:
        self.work_tree = work_tree
        self.git_dir = git_dir | (work_tree / '.git')

    def initialize(self):
        if not self.ready:
            self._initialize()
        return self.ready

    # TODO remove dangling lock file
    # and set the excludesfile
    def _initialize(self):
        return self._repo

    @property
    def ready(self):
        try:
            self._repo
            return True
        except KeyError:
            pass

    @property
    def _repo(self):
        return DulwichRepo.at(self.work_tree, self.git_dir)

    def t(self, state: RepoState):
        return self.repo(state) / RepoT

    @property
    def _new_state(self):
        return RepoState()


class ProjectRepoAdapter(RepoAdapter):

    def __init__(self, project: Project, git_dir: Maybe[Path]=Empty()) -> None:
        self.project = project
        super().__init__(self.project.root, git_dir)

    @may
    def repo(self, state: Maybe[RepoState]=Empty()) -> Maybe[Repo]:
        if self.initialize():
            return Repo(self._repo, state | self._new_state)

    @property
    def _new_state(self):
        return ProjectRepoState(project=self.project)

__all__ = ('RepoAdapter', 'RepoT', 'Repo', 'RepoState')
