from dataclasses import dataclass
from utils import Status
from mixing import BuiltinMixing

@dataclass
class Echo(BuiltinMixing):
    @classmethod
    def execute(cls, *args) -> Status:
        """ implementazione comando echo """
        pass
