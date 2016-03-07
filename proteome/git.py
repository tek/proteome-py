import io
import os
from pathlib import Path
from itertools import takewhile
from typing import Callable
from datetime import datetime

from fn import _, F  # type: ignore

from proteome.project import Project

import pyrsistent  # type: ignore

from dulwich import repo, config, porcelain  # type: ignore
from dulwich.repo import BASE_DIRECTORIES, OBJECTDIR  # type: ignore
from dulwich.object_store import DiskObjectStore  # type: ignore
from dulwich.objects import Commit  # type: ignore

from tryp import may, List, Maybe, Map, Empty, Just, __, Left, Right
from tryp.logging import Logging
from tryp.transformer import Transformer
from tryp.lazy import lazy
from tryp.task import Try

from trypnv.record import field, bool_field, dfield, maybe_field, Record
from trypnv import ProcessExecutor, Job


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


class RepoState(Record):
    current = maybe_field(str)


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
        return self.patch / __.splitlines() | ['no diff']

    @property
    def patch(self):
        f = io.BytesIO()
        try:
            porcelain.diff_tree(self.repo.repo, self.parent, self.target, f)
        except Exception as e:
            return Left(e)
        else:
            p = f.getvalue().decode()\
                .replace('\n\ No newline at end of file', '')
            return Right(p) if p else Left('empty diff')

    @property
    def revert(self):
        return Diff(self.repo, self.parent, self.target)


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

    def browse_format(self, show_diff: bool):
        prefix = '*' if self.current else ' '
        info = '{}  {}    {}'.format(prefix, self.hex[:8], self.since)
        diff = self.diff.map(_.show) if show_diff else Empty()
        return List(info) + (diff | List())


class DulwichRepo(repo.Repo):

    def __init__(self, store, worktree=None) -> None:
        super().__init__(str(store))
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
        cf.write_to_file(f)
        self._put_named_file('config', f.getvalue())
        self._put_named_file(os.path.join('info', 'exclude'), b'')

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


class Repo(Logging):

    def __init__(self, repo, state: RepoState) -> None:
        self.repo = repo
        self.state = state

    def copy(self, new_state: RepoState):
        return self.__class__(self.repo, new_state)  # type: ignore

    def __str__(self):
        return '{}({}, {})'.format(
            self.__class__.__name__, self.repo.path, self.state)

    @lazy
    def current(self):
        return self.state.current.or_else(self._head_id)

    def ref(self, name):
        return Maybe.from_call(lambda: self.repo.refs[name.encode()],
                               exc=KeyError)

    @property
    def master(self):
        return self.ref(_master_ref)

    @property
    def _master_ref_b(self):
        return _master_ref.encode()

    @property
    def index(self):
        return self.repo.open_index()

    @property
    def status(self):
        return porcelain.status(self.repo)

    def add_commit_all(self, msg):
        self.add_all()
        if self.index_dirty:
            return self.commit_master(msg)
        else:
            return Left('no changes to add')

    def add_all(self):
        return porcelain.add(self.repo)

    @property
    def index_dirty(self):
        return Map(self.status.staged).values.exists(bool)

    @property
    def committer(self):
        return 'proteome <proteome@nvim.local>'

    def commit_master(self, msg):
        return Try(
            self.repo.do_commit,
            message=msg.encode(),
            committer=self.committer.encode(),
            ref=self._master_ref_b,
        ) // (lambda a: self.to_master())

    def to_master(self):
        return self._head_commit.map(self._switch)

    @lazy
    def history(self):
        return List.wrap(self._master_id.map(self.history_at) | []) / _.commit

    def history_at(self, sha):
        return self.repo.get_walker(include=[sha])

    @property
    def history_ids(self):
        return self.history.map(_.id)

    @property
    def _master_id(self):
        return self.ref(_master_ref)

    @property
    def _head_id(self):
        return Try(self.repo.head)

    @property
    def _head_commit(self):
        return self._head_id // F(Try, self.repo.get_object)

    def _switch(self, commit):
        self._checkout_commit(commit)
        return self.state.set(current=Just(commit.id.decode()))

    def _checkout_commit(self, commit):
        self.repo.reset_index(commit.tree)

    def commit_info(self, index, commit):
        return CommitInfo.create(index, commit, self)

    @property
    def log_formatted(self):
        return self.history_info / _.log_format

    @lazy
    def history_info(self):
        return self.history\
            .with_index\
            .smap(self.commit_info)

    @property
    def current_b(self):
        return self.current / __.encode()

    @lazy
    def current_commit(self):
        return self.current_b / self.repo.get_object

    @property
    def current_commit_info(self):
        com = self.current_commit
        index = com // self.history.index_of
        return index.map2(com, self.commit_info)

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

    @may
    def repo(self, state: RepoState=RepoState()) -> Maybe[Repo]:
        if self.initialize():
            return Repo(self._repo, state)

    @property
    def _repo(self):
        return DulwichRepo.at(self.work_tree, self.git_dir)

    def t(self, state: RepoState):
        return self.repo(state).map(RepoT)


class HistoryState(Record):
    repos = dfield(Map())
    browse = dfield(Map())


class History(Logging):

    def __init__(self, base: Path, state: HistoryState=HistoryState()) -> None:
        self.base = base
        self.state = state

    @property
    def repos(self):
        return self.state.repos

    def adapter(self, project: Project):
        git_dir = self.base / project.fqn
        work_tree = project.root
        return RepoAdapter(work_tree, Just(git_dir))

    def state_for(self, project: Project):
        return self.repos.get(project) | (lambda: RepoState())

    def at(self, project: Project, f: Callable[[RepoT], RepoT]):
        return self.adapter(project)\
            .t(self.state_for(project))\
            .map(f)\
            .map(lambda r: self.repos + (project, r.state))\
            .map(lambda r: self.state.set(repos=r))

    def repo(self, project: Project):
        return self.adapter(project).repo(self.state_for(project))


class HistoryT(Transformer[History]):

    def pure(self, h: Maybe[HistoryState]) -> History:  # type: ignore
        new_state = h | self.state
        return History(self.val.base, new_state)

    @property
    def state(self):
        return self.val.state


class Git(ProcessExecutor):

    def pre_args(self, project: Project):
        return []

    def command(self, client, git_args, name, *cmd_args):
        args = list(map(str, git_args + [name] + list(cmd_args)))
        self.log.debug('running git {}'.format(' '.join(args)))
        job = Job(
            client=client,
            exe='git',
            args=args,
            loop=self.loop,
        )
        return self.run(job)

    def project_command(self, project: Project, name: str, *cmd_args):
        return self.command(project.job_client, self.pre_args(project), name,
                            *cmd_args)

    def revert(self, project: Project, commit: CommitInfo):
        return self.project_command(project, 'revert', '-n', commit.hex)

    def revert_abort(self, project: Project):
        return self.project_command(project, 'revert', '--abort')

    def clone(self, client, url, location):
        self.log.info('Cloning {}...'.format(url))
        return self.command(client, [], 'clone', url, location)


class HistoryGit(Git):

    def __init__(self, base: Path, vim) -> None:
        self.base = base
        super(HistoryGit, self).__init__(vim)

    def pre_args(self, project: Project):
        d = str(project.root)
        h = str(self._history_dir(project))
        return [
            '--git-dir',
            h,
            '--work-tree',
            d,
        ]

    def _history_dir(self, project: Project):
        return self.base / project.fqn

__all__ = ('History', 'RepoAdapter', 'RepoT', 'Repo', 'RepoState', 'HistoryT')
