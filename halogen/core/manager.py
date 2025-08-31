from types import MethodType, ModuleType
from typing import Callable, MutableSequence, Type, Literal
from pathlib import Path
import importlib, sys
import inspect

from halogen.base import (
	HalogenModule, 
	HalogenConfig,
	HalogenEvents
)

from halogen.modules import MODULES
from halogen.modules import HalogenLogModule



class HalogenModuleManager():

	def __init__(self, config: HalogenConfig, emit_event: Callable):

		self.config = config
		self.emit_event = emit_event
		self.modules_dir = self.config.directory / "modules"


		self.modules: MutableSequence[HalogenModule] = []
		self.dispatch_map: dict[type[HalogenEvents.Event], MutableSequence[HalogenModule]] = {}


	def load_modules(self) -> None:
		"Loading all modules and passing them to registration."
		self.modules.clear()
		
		for core_module in MODULES:
			self.initialize_module(core_module)

		py_modules: list[ModuleType] = self.import_modules()

		for py_module in py_modules:
			module = self.get_module(py_module)

			if module is None: continue

			self.initialize_module(module)
			

	def initialize_module(self, module_class: type[HalogenModule]) -> None:
		"Get the module class and intialize it."

		valid = isinstance(module_class, type) and issubclass(module_class, HalogenModule)

		if not valid:
			self.log(
				HalogenEvents.chain(),
				"warning",
				f"An argument of type {module_class.__name__} as passed to manager. "\
				"Not a Halogen Module!"
			)
			return

		module = module_class(
			self.emit_event,
			self.config.get_sub_config(module_class.name())
			)
		
		self.modules.append(module)

		handled_events = module.handled_events()

		for event in handled_events:
			self.dispatch_map.setdefault(event, []).append(module)

		if module.has_commands:
			self.handle_module_commands(module)

		if module.has_tools:
			self.handle_module_tools(module)

		self.log(
			HalogenEvents.chain(),
			"info",
			f"Initialized module '{module.name()}'. " \
			f"Info : {module.info()}"
		)

		self.log(
			HalogenEvents.chain(),
			"debug",
			f"Module '{module.name()}' handles events: {[e.__name__ for e in handled_events]}"
		)

	
	def get_module(self, py_module: ModuleType) -> type[HalogenModule] | None:
		"Get the HalogenModule from a python module."

		#looking for python module that defines a get_module

		if hasattr(py_module, "get_module"):
			module: type[HalogenModule] = py_module.get_module()
			return module
		else:
			self.log(
				HalogenEvents.chain(),
				"warning",
				f"Could not load module '{py_module.__name__}'. " \
				"The module does not define a standard 'get_module' method which should return a " \
				"Halogen module."
			)
			return None

    
	def import_modules(self) -> list[ModuleType]:
		"""
		Get all python modules within modules/
		"""
	
		mods = []

		for sub_dir in self.modules_dir.iterdir():

			if not sub_dir.is_dir():
				self.log(
					HalogenEvents.chain(),
					"debug",
					f"Ignoring {sub.absolute()}. Not a directory"
				)
				continue
			
			sub_dir_init = sub_dir / "__init__.py"

			if not sub_dir_init.exists():
				self.log(
					HalogenEvents.chain(),
					"debug",
					f"Ignoring {sub_dir.absolute()}. Not a python module."
				)
				continue

			mod_name = sub_dir.name

			spec = importlib.util.spec_from_file_location(mod_name, sub_dir_init)

			if not spec: continue
			if not spec.loader: continue

			mod = importlib.util.module_from_spec(spec)
			sys.modules[mod_name] = mod
			
			spec.loader.exec_module(mod)
			mods.append(mod)

		
		return mods
	
	
	def start_modules(self, dev = False):
		"Calls .start() on all registered modules."

		for module in self.modules:

			try:
				module.start()
				continue
			except Exception as e:
				err = e

			self.log(
				HalogenEvents.chain(),
				"critical",
				f"Could not start module with name {module.name()} (type:{type(module)}). " \
				f"Encountered Error = {err.__class__.__name__}:{str(err)}. " \
				"Shutting down halogen!"
			)

			event = HalogenEvents.ShutdownEvent(
				"module",
				HalogenEvents.make_timestamp(),
				HalogenEvents.chain(),
				True,
				"critical"
			)
			
			self.emit_event(event)

			if dev:
				self.end_modules()
				raise err


	def end_modules(self) -> HalogenLogModule | None:
		"Calls .end() on all modules."

		logger = None

		for module in self.modules:

			if isinstance(module, HalogenLogModule): 
				logger = module
				continue

			try:
				success, msg = module.end()
			except Exception as e:
				success = False
				err = f"{type(e).__name__}({str(e)})"
				msg = f"Could not properly end module '{module.name()}'. Error: {err}" 

			
			self.log(
				HalogenEvents.chain(),
				"info" if success else "warning",
				f"Ended {module.name()}: {msg}"
			) 
			
		return logger


	def handle_module_commands(self, module: HalogenModule):

		for name, mem in inspect.getmembers(module, inspect.ismethod):
			if not hasattr(mem, "_is_command"):
				continue
		
			ev = HalogenEvents.CommandRegisterEvent(
				module.name(),
				HalogenEvents.make_timestamp(),
				HalogenEvents.chain(),
				module.name(),
				mem._name, #type: ignore
				mem._info, #type: ignore // These SHOULD exist if _is_command exists
				mem
			)
			self.emit_event(ev)


	def handle_module_tools(self, module: HalogenModule):

		for name, mem in inspect.getmembers(module, inspect.ismethod):
			if not hasattr(mem, "_is_tool"):
				continue

			ev = HalogenEvents.ToolRegisterEvent(
				module.name(),
				HalogenEvents.make_timestamp(),
				HalogenEvents.chain(),
				module.name(),
				mem._name, #type: ignore
				mem._args,#type: ignore
				mem._info, #type: ignore // These SHOULD exist if _is_task exists
				mem
			)
			self.emit_event(ev)


	
	def defined_events(self):
		return self.dispatch_map.keys()
	

	def get_module_list(self, event: Type[HalogenEvents.Event]):
		return self.dispatch_map[event]
	

	def log(
		self, 
		chain: HalogenEvents.Chain, 
		level: Literal["debug", "info", "warning", "critical"], 
		msg: str
		):

		event = HalogenEvents.LogEvent(
			"module",
			HalogenEvents.make_timestamp(),
			chain,
			level,
			msg
		)
		self.emit_event(event)