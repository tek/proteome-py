import amino.logging
from ribosome.logging import ribosome_logger

from amino.lazy import lazy


log = proteome_root_logger = ribosome_logger('proteome')


def proteome_logger(name: str):
    return proteome_root_logger.getChild(name)


class Logging(amino.logging.Logging):

    @lazy
    def _log(self) -> amino.logging.Logger:  # type: ignore
        return proteome_logger(self.__class__.__name__)

__all__ = ('proteome_logger', 'Logging')
