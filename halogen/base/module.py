from abc import ABC
from types import MethodType
from typing import Tuple, Literal, Union
from collections.abc import Callable

from .events import HalogenEvents
from .config import HalogenConfig
from .chain import Chain


class HalogenModule(ABC):
	"""
	Base class for making a halogen module. Only a subclass of this base class is allowed to be 
	integrated with halogen's module manager.
	
	Each HalogenModule should be defined like this:

	1) __init__ should be fixed to the __init__ of this base class that is no parameters should be 
	changed. The class is actually initialized by the module manager.

	2) Classmethod 'name' which returns a string that tells the name of the module. Note that this should 
	be the same as the directory in which the module class resides. For example, filesystem directory has
	HalogenModule named 'filesystem'

	3) Classmethod 'info' which gives info about the module in a single line.

	4) A .handle() method that is used by core to pass events that it can receive.

	5) A .handled_events() which returns a list of events that the module can handle. Only events listed
	here will be sent by the core to this module.

	Other than these some functions that are already defined include:

	1) .emit_event() for sending events to the core. Do not use the raw .eventbus_emit().
	2) .log() which is a shorthand to making a log event and emitting it.
	
	"""

	def __init__(self, emit_event: Callable[[HalogenEvents.Event], None], config: HalogenConfig) -> None:
		super().__init__()
		self.eventbus_emit = emit_event
		self.config = config 
		self.has_commands = False
		self.has_tools = False


	@classmethod
	def name(cls) -> str:
		"""
		The name of the module. This is important for config file. By default, its the literal
		name of the class. 
		"""
		return cls.__name__
	

	@classmethod
	def info(cls) -> str:
		"""
		The info and details related to the module. 
		"""
		return f"No information provided for {cls.name()}"


	def start(self) -> None:
		"""
		Function that is called once the core starts running. 
		It is recomended to put all of the setup here.
		Override this and do not call super().start()
		"""
		raise NotImplementedError(f"start method of class {self.__class__} not implemented.")


	def end(self) -> Tuple[bool, str]:
		"""
		Function called by HalogenCore to end the module. 
		The module must do all its clean up before returning True. 
		In case something goes wrong, return False + string. It will be logged. 
		Override this and do not call super().end()
		"""
		raise NotImplementedError(f"end method of class {self.__class__} not implemented.")


	def handled_events(self) -> list[type[HalogenEvents.Event]]:
		"""
		List of HalogenEvents that the module can handle. 
		These will be dispatched to the module via HalogenModule.handle(). 
		Override this and do not call super().handled_events()
		"""
		raise NotImplementedError(f"handled_events method of class {self.__class__} not implemented.")


	def handle(self, event: HalogenEvents.Event) -> None:
		"""
		The function called by HalogenCore to pass an event. 
		Override this and do not call super().handle()
		"""
		raise NotImplementedError(f"handle method of class {self.__class__} not implemented.")


	def emit_event(self, event: HalogenEvents.Event) -> None:
		"""
		Internal function to call when the module wants to emit some event to the eventbus.
		"""
		if not isinstance(event, HalogenEvents.Event):
			log_event = HalogenEvents.LogEvent(
				self.name(),
				HalogenEvents.make_timestamp(),
				"warning",
				f"HalogenModule '{self.name()}' tried to emit an invalid event. " \
				"Expected argument was a Halogen Event or its subclass. " \
				f"Got {type(event)}"
			)
			self.eventbus_emit(log_event)
			return
		
		self.eventbus_emit(event)


	def log(
		self, 
		chain: Chain,
		level: Literal["debug", "info", "warning", "critical"],
		msg: str
	):
		"""
		Shorthand for creating a log event and emitting it to the bus.
		"""
		event = HalogenEvents.LogEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			chain,
			level,
			msg
		)
		self.emit_event(event)
