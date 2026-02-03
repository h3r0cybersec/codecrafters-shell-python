import sys
from typing import AnyStr, List, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass
from utils import Status

@dataclass
class BuiltinMixing(ABC):
    """ Definisce un comando builtin """

    @classmethod
    @abstractmethod
    def execute(cls, *args) -> Status:
        """ definisce la logica di esecuzione per il comando specifico """
        ...
