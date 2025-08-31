from collections.abc import Callable
from typing import Tuple
from halogen.base import HalogenModule, HalogenEvents, HalogenConfig, Chain, HalogenError
from pathlib import Path
import os

from .sub_managers.memory import MemoryManager
from .sub_managers.tasks import ToolManager
# TODO Make prompt manager more robust and modular cuz the current approach is literal duct tape


class HalogenPromptManager(HalogenModule):

	def __init__(
		self, 
		emit_event: Callable[[HalogenEvents.Event], None], 
		config: HalogenConfig
		) -> None:
		super().__init__(emit_event, config)
		
		self.core_sections: list[str] = []
		self.memory: MemoryManager = MemoryManager(self.config.get("memory_length", 50))
		self.tools: ToolManager = ToolManager()

		self.log_file = Path(__file__).resolve().parent / "halogen.log"

		self.prompts_dir = self.config.directory / "prompt"

		if not self.prompts_dir.exists():
			raise HalogenError(f"Prompts Config directory not found: {self.prompts_dir.absolute()}.")
	

	@classmethod
	def name(cls) -> str:
		return "prompt"
	

	def	start(self) -> None:
		self.load_core_sections()
		
		
	def end(self) -> Tuple[bool, str]:
		return (True, "")
	

	def handled_events(self) -> list[type[HalogenEvents.Event]]:
		return [
			HalogenEvents.AIResponseEvent,
			HalogenEvents.UserInputEvent,
			HalogenEvents.NotifyEvent,
			HalogenEvents.ToolRegisteredEvent,
			HalogenEvents.TaskEvent,
			HalogenEvents.TaskCompletionEvent
		]


	def handle(self, event: HalogenEvents.Event) -> None:
		match event:

			case HalogenEvents.AIResponseEvent():
				self.memory.add("you", event.message)

			case HalogenEvents.UserInputEvent():
				self.handle_user_input(event)

			case HalogenEvents.NotifyEvent():
				self.handle_notify_event(event)

			case HalogenEvents.ToolRegisteredEvent():
				self.tools.add_tool(event)

			case HalogenEvents.TaskCompletionEvent():
				self.handle_task_completion(event)
				

	def load_core_sections(self):

		system_prompt = Path(__file__).resolve().parent / "system.txt"
		with open(system_prompt) as file:
			self.core_sections.append(file.read())

		profile_prompt = self.prompts_dir / "profile.txt"
		with open(profile_prompt) as file:
			self.core_sections.append(file.read())

		user_prompt = self.prompts_dir / "user.txt"
		with open(user_prompt) as file:
			self.core_sections.append(file.read())

		self.log(
			HalogenEvents.chain(),
			"debug",
			f"Assembled core sections."
		)


	def make_prompt_parts(self) -> list[str]:
		parts = []
		parts.extend(self.core_sections)
		parts.append(self.tools.stringify())
		parts.append(self.memory.stringify())
		return parts


	def handle_user_input(self, event: HalogenEvents.UserInputEvent):	

		self.log(
			HalogenEvents.chain(event),
			"info",
			"Received user input. Making prompt."
		)

		prompt = self.make_prompt_parts()
		prompt.append("\n[USER]")
		prompt.append(event.message)

		str_prompt = "\n".join(prompt)

		prompt_event = HalogenEvents.PromptEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			HalogenEvents.chain(event),
			str_prompt
		)

		self.print_prompt(prompt_event)
		self.emit_event(prompt_event)

		self.memory.add("user", event.message)


	def handle_task_completion(self, ev: HalogenEvents.TaskCompletionEvent):

		self.log(
			HalogenEvents.chain(ev),
			"info",
			"Received task completion info. Making prompt."
		)

		prompt = self.make_prompt_parts()
		prompt.append("\n[HALOGEN]")


		task_info = []
		task_info.append(f"Completed task : {ev.name}")
		for sub in ev.sub_tasks:
			msg = f"Completed task '{sub.namespace}::{sub.func_name}' with args {sub.args}. " \
				f"Success = {sub.success}. Output = {sub.output}"
			task_info.append(msg)
		
		task_info_str = "\n".join(task_info)
			
		prompt.append(task_info_str)

		str_prompt = "\n".join(prompt)

		prompt_event = HalogenEvents.PromptEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			HalogenEvents.chain(ev),
			str_prompt
		)

		self.print_prompt(prompt_event)
		self.memory.add("halogen", task_info_str)
		self.emit_event(prompt_event)


	def handle_notify_event(self, ev: HalogenEvents.NotifyEvent):

		self.log(
			HalogenEvents.chain(ev),
			"info",
			f"Received notify event from module '{ev.sender}'. Making prompt."
		)

		prompt = self.make_prompt_parts()

		prompt.append("\n[HALOGEN]")
		msg = f"{ev.sender} module send notify:: {ev.message}"
		
		prompt.append(msg)
		
		str_prompt = "\n".join(prompt)

		prompt_event = HalogenEvents.PromptEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			HalogenEvents.chain(ev),
			str_prompt
		)

		self.print_prompt(prompt_event)
		self.memory.add("halogen", msg)
		self.emit_event(prompt_event)


	def print_prompt(self, ev: HalogenEvents.PromptEvent):
		with open(self.log_file, "a") as file:
			file.write("\n"*10)
			file.write(ev.content)

	

