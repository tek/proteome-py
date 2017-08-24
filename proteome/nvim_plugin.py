import neovim

from proteome.nvim_plugin_impl import ProteomeNvimPluginImpl


@neovim.plugin
class ProteomeNvimPlugin(ProteomeNvimPluginImpl):
    pass

__all__ = ('ProteomeNvimPlugin',)
