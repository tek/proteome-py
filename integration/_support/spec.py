import proteome.test

from tryp.test.spec import IntegrationSpec


class Spec(proteome.test.Spec, IntegrationSpec):

    def setup(self):
        super().setup()

__all__ = ['Spec']
