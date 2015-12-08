import sure  # NOQA
from flexmock import flexmock  # NOQA
from pathlib import Path

from tryp import List, Just

from proteome.project import Project
from proteome.git import HistoryGit

from unit.project_spec import _LoaderSpec
from unit._support.async import test_loop

from tek.test import temp_dir


class Git_(_LoaderSpec):

    def commit_all(self):
        history_base = temp_dir('git', 'history')
        git = HistoryGit(history_base)
        p = self.mk_project('pro1', 'py')
        (p.root / 'test_file').touch()
        history_repo = history_base / p.fqn
        with test_loop() as loop:
            run = lambda f: loop.run_until_complete(f).success.should.be.ok
            run(git.init(p))
            run(git.add_commit_all(p, 'test'))
        (history_repo / 'HEAD').exists().should.be.ok
        git.current.keys.should.be.empty

__all__ = ['Git_']
