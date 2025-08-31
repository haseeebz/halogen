from collections.abc import Callable
from typing import Tuple
from halogen.base import (
	HalogenEvents,
	HalogenConfig,
	HalogenModule,
	HalogenError,
	HalogenCommand,
	Chain
)

from .meta import TaskNamespace, TaskData
from .base import HalogenTaskError


class HalogenTaskManager(HalogenModule):

	def __init__(
		self, 
		emit_event: Callable[[HalogenEvents.Event], None], 
		config: HalogenConfig
		) -> None:
	
		super().__init__(emit_event, config)
		self.namespaces: dict[str, TaskNamespace] = {}
		
	
	@classmethod
	def name(cls) -> str:
		return "tasks"
	

	def start(self) -> None:
		pass


	def end(self) -> Tuple[bool, str]:
		return (True, "")
	

	def handled_events(self) -> list[type[HalogenEvents.Event]]:
		return [
			HalogenEvents.TaskEvent,
			HalogenEvents.TaskRegisterEvent
		]
	

	def handle(self, event: HalogenEvents.Event) -> None:
		match event:
			case HalogenEvents.TaskRegisterEvent():
				self.register_task(event)
			case HalogenEvents.TaskEvent():
				self.exec_task(event)                                    



	def register_task(self, ev: HalogenEvents.TaskRegisterEvent):

		namespace = self.namespaces.setdefault(
			ev.namespace,
			TaskNamespace(ev.namespace)
		)

		if ev.task_name in namespace.tasks.keys():
			self.log(
				HalogenEvents.chain(ev),
				"warning",
				f"Task with name '{ev.task_name}' for namespace '{ev.namespace}' already registered"
			)
			return
		
		task_data = TaskData(
			ev.task_name,
			ev.info,
			ev.args_info,
			ev.func
		)

		namespace.tasks[ev.task_name] = task_data

		self.log(
			HalogenEvents.chain(ev),
			"info",
			f"Registered task {ev.namespace}::{ev.task_name}"
		)

		registered_ev = HalogenEvents.TaskRegisteredEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			HalogenEvents.chain(ev),
			ev.namespace,
			ev.task_name,
			ev.args_info,
			ev.info
		)

		self.emit_event(registered_ev)

	

	def exec_task(self, ev: HalogenEvents.TaskEvent):

		self.log(
			HalogenEvents.chain(ev),
			"info",
			f"Executing task {ev.chain} {ev.namespace}::{ev.task_name} with args {ev.args}"
		)
		
		namespace = self.namespaces.setdefault(
			ev.namespace,
			TaskNamespace(ev.namespace)
		)

		if ev.task_name not in namespace.tasks.keys():
			self.log(
				HalogenEvents.chain(ev),
				"warning",
				f"Task with name '{ev.task_name}' for namespace '{ev.namespace}' not found."
			)
			return

		func = namespace.tasks[ev.task_name].func

		try:
			output = func(ev.chain, *ev.args)
			success = True
		except HalogenTaskError as e:
			output = f"Error: {str(e)}"
			success = False
		except Exception as e:
			output = f"Unexpected Error({e.__class__.__name__}): {str(e)}"
			success = False

		output_event = HalogenEvents.TaskCompletionEvent(
			self.name(),
			HalogenEvents.make_timestamp(),
			HalogenEvents.chain(ev),
			ev.task_group,
			ev.namespace,
			ev.task_name,
			ev.args,
			success,
			output
		)

		self.emit_event(output_event)

		self.log(
			HalogenEvents.chain(ev),
			"info",
			f"Executed task {ev.chain} {ev.namespace}::{ev.task_name}. Success = {success}"
		)

		self.log(
			HalogenEvents.chain(ev),
			"debug" if success else "warning",
			f"Executed task {ev.chain} {ev.namespace}::{ev.task_name} returned {output}"
		)


	
	