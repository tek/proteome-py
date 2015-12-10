from pathlib import Path

import neovim  # type: ignore

import trypnv

from proteome.logging import Logging


class NvimFacade(Logging, trypnv.nvim.NvimFacade):

    def __init__(self, nvim: neovim.Nvim) -> None:
        trypnv.nvim.NvimFacade.__init__(self, nvim, 'proteome')

    def switch_root(self, path: Path):
        p = str(path)
        self.vim.chdir(p)
        self.pautocmd('SwitchedRoot')
        self.log.info('switched root to {}'.format(p))
        self.set_pvar('root', p)
        self.set_pvar('root_name', str(path.name))


__all__ = ['NvimFacade']
