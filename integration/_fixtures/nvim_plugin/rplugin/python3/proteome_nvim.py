import neovim

from proteome.nvim_plugin import ProteomeNvimPlugin

import tryp

tryp.development = True


@neovim.plugin
class Plugin(ProteomeNvimPlugin):
    pass
