from typing import Callable
from pathlib import Path

from ribosome.record import Record, dfield

from amino import Map, Maybe, Just
from amino.transformer import Transformer

from proteome.logging import Logging
from proteome.project import Project
from proteome.git import RepoT, ProjectRepoAdapter, RepoState


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
        return ProjectRepoAdapter(project, Just(git_dir))

    def state_for(self, project: Project):
        return self.repos.get(project)

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

__all__ = ('HistoryState', 'History', 'HistoryT')
