from amino import __
from amino.test.spec_spec import later

from kallikrein.matchers.start_with import start_with
from kallikrein.matchers.maybe import be_just

from integration._support.base import DefaultSpec


class CloneSpec(DefaultSpec):
    '''clone a repository
    valid $valid
    invalid $invalid
    '''

    def valid(self):
        name = 'proteome.nvim'
        self.vim.cmd('ProClone tek/{}'.format(name))
        readme = self.base / self.tpe1 / name / 'README.md'
        later(lambda: readme.exists().should.be.ok)
        return self.pvar_becomes_map('active', name, __['name'])

    def invalid(self):
        name = 'invalid@#'
        self.vim.cmd('ProClone tek/{}'.format(name))
        return self._log_line(-1, be_just(start_with('failed to clone')))

__all__ = ('CloneSpec',)
