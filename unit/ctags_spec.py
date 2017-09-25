from pathlib import Path

from kallikrein import kf, Expectation, k
from kallikrein.matchers.empty import be_empty

from amino import List, Just
from amino.test import temp_path

from proteome.project import Project
from proteome.ctags import CtagsExecutor

from unit._support.async import test_loop
from unit._support.loader import LoaderSpec


class CtagsSpec(LoaderSpec):
    '''execute ctags
    successful generation of a tag file $success
    failure result for nonexisting project directory $fail
    '''

    def success(self) -> Expectation:
        with test_loop() as loop:
            ctags = CtagsExecutor(None)
            p = Project.of(self.pypro1_name, self.pypro1_root, tpe=Just(self.pypro1_type), langs=List(self.pypro1_type))
            p.remove_tag_file()
            result = loop.run_until_complete(ctags.gen(p))
            return k(result.success).true & kf(p.tag_file.exists).true & k(ctags.current.k).must(be_empty)

    def fail(self) -> Expectation:
        with test_loop() as loop:
            ctags = CtagsExecutor(None)
            p = Project.of('invalid', Path(temp_path('invalid')), tpe=Just('c'), langs=List('c'))
            result = loop.run_until_complete(ctags.gen(p))
            return k(result.success).false

__all__ = ('CtagsSpec',)
