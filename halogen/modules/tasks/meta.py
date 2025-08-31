from dataclasses import dataclass, field
from typing import Callable
from halogen.base import Chain

@dataclass
class ToolData:
	name: str
	info: str
	args: list[str]
	func: Callable[[list[str], Chain], str]

@dataclass 
class ToolNamespace:
	module: str
	tools: dict[str, ToolData] = field(default_factory = dict)
	