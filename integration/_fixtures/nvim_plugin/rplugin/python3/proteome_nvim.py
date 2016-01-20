import neovim
import os
import logging
from pathlib import Path

from proteome.nvim_plugin import ProteomeNvimPlugin

import tryp

tryp.development = True

import tryp.logging

logfile = Path(os.environ['TRYPNV_LOG_FILE'])
tryp.logging.tryp_file_logging(level=logging.DEBUG,
                               handler_level=logging.DEBUG,
                               logfile=logfile)


@neovim.plugin
class Plugin(ProteomeNvimPlugin):
    pass
