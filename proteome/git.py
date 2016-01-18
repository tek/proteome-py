from pathlib import Path
from itertools import takewhile
from typing import Callable
from datetime import datetime

try:
    import pygit2
    from pygit2 import Commit, GitError
except ImportError:
    pygit_working = False
else:
    pygit_working = True

from fn import _, F  # type: ignore

from proteome.project import Project

from pyrsistent import PRecord

from tryp import may, List, Maybe, Map, Empty, Just, __
from tryp.logging import Logging
from tryp.transformer import Transformer
from tryp.lazy import lazy

from trypnv.data import field, bool_field


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


class RepoState(PRecord):
    current = field(Maybe, initial=Empty())


class CommitInfo(PRecord):
    num = field(int)
    hex = field(str)
    timestamp = field(int)
    current = bool_field()

    @property
    def since(self):
        return format_since(self.timestamp)


class Repo(Logging):

    def __init__(self, repo: pygit2.Repository, state: RepoState):
        self.repo = repo
        self.state = state

    def __str__(self):
        return '{}({}, {})'.format(
            self.__class__.__name__, self.repo.path, self.state)

    @lazy
    def current(self):
        return self.state.current.or_else(self._head_id)

    @lazy
    def current_commit(self):
        return self.history.find(F(_.id) >> self.current.contains)

    def ref(self, name):
        return Maybe.from_call(lambda: self.repo.lookup_reference(name),
                               exc=KeyError)

    @property
    def _master_ref(self):
        return 'refs/heads/master'

    @property
    def master(self):
        return self.ref(self._master_ref)

    @property
    def _master_id(self):
        return self.master.map(_.target)

    @property
    def _master_commit(self):
        return self.master.map(lambda a: a.get_object())

    @property
    def _head(self):
        return Maybe.from_call(lambda: self.repo.head, exc=GitError)

    @property
    def _head_commit(self):
        return self._head.map(lambda a: a.get_object())

    @property
    def _head_id(self):
        return self._head.map(_.target)

    @lazy
    def history(self):
        return List(*(self._master_id.map(self.history_at) | []))

    @property
    def history_ids(self):
        return self.history.map(_.id)

    def history_at(self, id):
        return self.repo.walk(id, pygit2.GIT_SORT_TIME)

    def future_at(self, id):
        def search(mid):
            return reversed(list(takewhile(_.id != id, self.history_at(mid))))
        return self._master_id.map(search) | iter([])

    @may
    def parent(self, id, n=0) -> Maybe[Commit]:
        return self._skip(self.history_at(id), n)

    @may
    def child(self, id, n=0) -> Maybe[Commit]:
        return self._skip(self.future_at(id), n - 1)

    def _skip(self, hist, n):
        try:
            for i in range(n + 1):
                next(hist)
            return next(hist)
        except StopIteration:
            pass

    def prev(self):
        value = self.current\
            .flat_map(self.parent)\
            .map(self._switch)
        return value

    def next(self):
        return self.current\
            .flat_map(self.child)\
            .map(self._switch)

    def to_master(self):
        return self._head_commit.map(self._switch)

    def _switch(self, commit: Commit):
        self._checkout_commit(commit)
        return self.state.set(current=Just(commit.id))

    def _checkout_commit(self, commit: Commit):
        strat = pygit2.GIT_CHECKOUT_FORCE
        try:
            self.repo.checkout_tree(commit.tree, strategy=strat)
            self.repo.set_head(commit.oid)
            if commit.id == self._master_id:
                self.repo.checkout(self._master_ref)
        except GitError as e:
            self.log.error('failed to check out commit: {}'.format(e))

    def _checkout_master(self):
        return self._master_commit.map(self._switch)

    def add_commit_all(self, msg):
        self.repo.index.add_all()
        tree = self.repo.index.write_tree()
        return self._create_master_commit(tree, msg)

    def _create_master_commit(self, tree, msg):
        u = 'proteome'
        m = 'proteome@nvim.local'
        author = pygit2.Signature(u, m)
        committer = pygit2.Signature(u, m)
        parents = self._master_commit\
            .or_else(self._head_commit)\
            .map(lambda a: [a.hex]) | []
        self.repo.create_commit(self._master_ref, author, committer,
                                msg, tree, parents)
        return self._checkout_master()

    @property
    def status(self):
        return self.repo.status()

    def commit_info(self, index):
        def create(commit):
            return CommitInfo(num=index, hex=commit.hex,
                              timestamp=commit.commit_time,
                              current=self.current.contains(commit.id))
        return self.history.lift(index).map(create)

    @property
    def current_commit_info(self):
        return self.current_commit\
            .flat_map(self.history.index_of)\
            .flat_map(self.commit_info)

    @property
    def log_formatted(self):
        def format(commit):
            prefix = '*' if commit.current else ' '
            return '{} {} {}'.format(prefix, commit.hex[:8], commit.since)
        return List.wrap(range(len(self.history)))\
            .flat_map(self.commit_info)\
            .map(format)


class RepoT(Transformer[Repo]):

    @property
    def repo(self):
        return self.val

    def pure(self, s: Maybe[RepoState]):
        new_state = s | self.repo.state
        return Repo(self.repo.repo, new_state)

    @property
    def state(self):
        return self.repo.state


class RepoAdapter(object):

    def __init__(self, work_tree: Path, git_dir: Maybe[Path]=Empty()):
        self.work_tree = work_tree
        self.git_dir = git_dir | (work_tree / '.git')

    def initialize(self):
        if not self.ready:
            self._initialize()
        return self.ready

    @property
    def ready(self):
        try:
            self._repo
            return True
        except KeyError:
            pass

    def _initialize(self):
        pygit2.init_repository(str(self.git_dir), bare=True)

    @may
    def repo(self, state: RepoState=RepoState()) -> Maybe[Repo]:
        if self.initialize():
            return Repo(self._repo, state)

    def t(self, state: RepoState):
        return self.repo(state).map(RepoT)

    @property
    def _repo(self):
        inst = pygit2.Repository(str(self.git_dir))
        inst.workdir = str(self.work_tree)
        return inst

HistoryState = Map[Project, RepoState]


class History(object):

    def __init__(self, base: Path, state: HistoryState=Map()):
        self.base = base
        self.state = state

    def adapter(self, project: Project):
        git_dir = self.base / project.fqn
        work_tree = project.root
        return RepoAdapter(work_tree, Just(git_dir))

    def state_for(self, project: Project):
        return self.state.get(project) | (lambda: RepoState())

    def at(self, project: Project, f: Callable[[RepoT], RepoT]):
        return self.adapter(project)\
            .t(self.state_for(project))\
            .map(f)\
            .map(lambda r: self.state + (project, r.state))

    def add_commit_all(self, project: Project, message: str):
        return self.with_repo(project, __.add_commit_all(message))


class HistoryT(Transformer[History]):

    def pure(self, h: Maybe[HistoryState]) -> 'HistoryT':
        new_state = h | self.state
        return History(self.val.base, new_state)

    @property
    def state(self):
        return self.val.state

__all__ = ('History', 'RepoAdapter', 'RepoT', 'Repo', 'RepoState', 'HistoryT')
