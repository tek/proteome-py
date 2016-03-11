import tryp.logging
from trypnv.logging import trypnv_logger

from tryp.lazy import lazy


log = proteome_root_logger = trypnv_logger('proteome')


def proteome_logger(name: str):
    return proteome_root_logger.getChild(name)


class Logging(tryp.logging.Logging):

    @lazy
    def _log(self) -> tryp.logging.Logger:  # type: ignore
        return proteome_logger(self.__class__.__name__)

__all__ = ('proteome_logger', 'Logging')
