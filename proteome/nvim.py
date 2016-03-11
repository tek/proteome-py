from pathlib import Path

import neovim

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
        self.set_pvar('root_dir', p)


__all__ = ['NvimFacade']
