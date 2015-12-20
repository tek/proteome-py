from pathlib import Path

import neovim  # type: ignore

import trypnv

from proteome.logging import Logging


class NvimFacade(Logging, trypnv.nvim.NvimFacade):

    def __init__(self, nvim: neovim.Nvim) -> None:
        trypnv.nvim.NvimFacade.__init__(self, nvim, 'proteome')

    def cd(self, d):
        self.vim.chdir(str(d))

    def switch_root(self, path):
        p = str(path)
        self.cd(p)
        self.pautocmd('SwitchedRoot')
        self.set_pvar('root', p)
        self.set_pvar('root_name', str(path.name))


__all__ = ['NvimFacade']
