from collections.abc import Callable
import importlib.util
from pathlib import Path
import os, sys
from types import ModuleType
from typing import Tuple, Union
import inspect, importlib

from halogen.base import (
	HalogenEvents,
	HalogenConfig,
	HalogenModule,
	HalogenError,
	HalogenCommand,
	Chain
)
from halogen.base.helpers import PyModuleLoader


from .base import (
	BaseModelProvider,
	ModelResponse, 
	HalogenModelResponseError,
	HalogenProviderError
)


class HalogenModelManager(HalogenModule):

	def __init__(
		self, 
		emit_event: Callable[[HalogenEvents.Event], None], 
		config: HalogenConfig
		):
		super().__init__(emit_event, config)
		self.has_commands = True

		self.registered_providers: dict[str, BaseModelProvider] = {}
		self.current_provider: Union[BaseModelProvider, None] = None 
		
		self.model_directory = self.config.directory / "models"

		self.module_loader = PyModuleLoader()


	@classmethod
	def name(cls) -> str:
		return "model"


	@classmethod
	def info(cls) -> str:
		return "Module for loading and managing Model Providers."
	

	def start(self) -> None:

		if not self.model_directory.exists():
			ev = HalogenEvents.ShutdownEvent(
				self.name(),
				HalogenEvents.make_timestamp(),
				HalogenEvents.chain(),
				True,
				f"{self.model_directory.absolute()} does not exist. Cannot proceed"
			)
			self.emit_event(ev)
			return

		self.init_providers()

		current_provider = self.config.get("name", None)
		try:
			msg = self.change_provider(current_provider)
			success = True
		except HalogenProviderError as e:
			msg = str(e)
			success = False

		if success:
			self.log(
				HalogenEvents.chain(),
				"info",
				msg
			)
			return


		ev = HalogenEvents.ShutdownEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			HalogenEvents.chain(),
			True,
			f"{msg}"
		)
		self.emit_event(ev)


	def end(self) -> Tuple[bool, str]:
		if self.current_provider:
			self.current_provider.unload()
		return (True, "Success")


	def handled_events(self) -> list[type[HalogenEvents.Event]]:
		return [
			HalogenEvents.PromptEvent
		]


	def handle(self, event: HalogenEvents.Event) -> None:

		match event:
			case HalogenEvents.PromptEvent():
				self.generate_response(event)


	def init_providers(self):
		"""
		Initialize all providers found in models/
		"""

		providers = self.get_providers()

		for provider in providers:

			provider_obj: BaseModelProvider = provider(
				self.config.get_sub_config(provider.name())
				)
			
			self.registered_providers[provider_obj.name()] = provider_obj

			self.log(
				HalogenEvents.chain(),
				"info",
				f"Registered Model '{provider_obj.name()}'"
			)


	def get_providers(self) -> list[type[BaseModelProvider]]:
		"""
		Get all provider classes within models/
		"""
	
		providers = []

		for sub_dir in self.model_directory.iterdir():

			try:
				mod = self.module_loader.from_directory(sub_dir.name, sub_dir)
				provider = self.get_provider_from_module(mod)
				if provider: providers.append(provider)
				continue
			except PyModuleLoader.PyModuleError as e:
				msg = str(e)

			self.log(
				HalogenEvents.chain(),
				"warning",
				f"PyModuleLoader Failure : {msg}"
			)
		
		return providers
	

	def get_provider_from_module(self, mod: ModuleType) -> type[BaseModelProvider] | None:
		"""
		Get a provider class from a python module.
		"""

		if not hasattr(mod, "get_model"):
			self.log(
				HalogenEvents.chain(),
				"warning",
				f"A python module found in model/: '{mod.__name__}' has no get_model method"
			)
			return None

		model_cls = mod.get_model()
		
		if not issubclass(model_cls, BaseModelProvider):
			self.log(
				HalogenEvents.chain(),
				"critical",
				f"A python module found in model/: '{mod.__name__}' returned an invalid model provider. " \
				f"Expected BaseModelProvider, Got {type(model_cls)}"
			)
			return None
		
		name = model_cls.name()

		if name in self.registered_providers.keys():

			err = f"A python module found in model/: '{mod.__name__}' " \
			"returned an invalid model provider." \
			f"Model tried to register with name '{name}' but it already exists."

			self.log(
				HalogenEvents.chain(),
				"critical",
				err
			)

			return None
		
		return model_cls


	def generate_response(self, event: HalogenEvents.PromptEvent):

		if not self.current_provider:
			return 
		
		try:
			response = self.current_provider.generate(event)
		except HalogenModelResponseError as e:
			self.log(
			HalogenEvents.chain(event),
			"critical",
			f"Could not get response from model '{self.current_provider.name()}'. " \
			f"Encountered Error: {e.__class__.__name__} : {str(e)}."
			)
			return 

		self.parse_response(response, HalogenEvents.chain(event))


	def parse_response(self, response: ModelResponse, chain: Chain):

		extras = {}
		for ex in response.extras:
			extras[ex.key] = ex.value
		

		ai_msg = HalogenEvents.AIResponseEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			chain,
			response.message,
			extras
		)
		self.emit_event(ai_msg)

		for task in response.tasks:
			sub = [HalogenEvents._SubTask(x.namespace, x.func_name, x.args) for x in task.sub_tasks]
			ev = HalogenEvents.TaskEvent(
				self.name(),
				HalogenEvents.make_timestamp(),
				chain,
				task.name,
				sub
			)	
			self.emit_event(ev)			



	def change_provider(self, provider: str) -> str:
		
		if provider not in self.registered_providers:
			raise HalogenProviderError(f"Could not find provider '{provider}'. It was not registered.")

		if self.current_provider: self.current_provider.unload()
		self.current_provider = self.registered_providers[provider]
		self.current_provider.load()

		return f"Loaded provider '{provider}'."


	def change_model(self, model: str) -> str:
		return self.current_provider.load(model)
	

	@HalogenCommand("current", "Get info about the current model")
	def get_current_model_command(self, args: list[str], chain: Chain) -> tuple[bool, str]:
		return (True, f"Model: {self.current_provider.name()}")


	@HalogenCommand("switch", "Switch the model or provider. ARGS: [model/provider] name")
	def switch_command(self, args: list[str], chain: Chain):

		if len(args) != 2:
			raise ValueError(f"Expected 2 args. Got {len(args)}.")

		choice = args[0]
		name = args[1]

		success = True
		match choice:
			case "provider":
				msg = self.change_provider(name)
			case "model":
				msg = self.change_model(name)
			case _:
				success = False
				msg = f"Unknown switch argument : {choice}"

		return (success, msg)
		




