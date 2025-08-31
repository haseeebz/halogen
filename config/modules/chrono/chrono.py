from collections.abc import Callable
from threading import Thread
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

from halogen.base import HalogenEvents, HalogenModule, HalogenConfig
from halogen.modules.tasks.base import HalogenTool, HalogenTaskError

class Chrono(HalogenModule):

	def __init__(self, emit_event: Callable[[HalogenEvents.Event], None], config: HalogenConfig) -> None:
		super().__init__(emit_event, config)
		self.has_tools = True
		self.executor = ThreadPoolExecutor()
	
	@classmethod
	def name(cls):
		return "chrono"

	@classmethod
	def info(cls):
		return "Module for time and reminders related functionality."
	

	def handled_events(self) -> list[type[HalogenEvents.Event]]:
		return []
	

	def start(self) -> None:
		pass


	def end(self) -> tuple[bool, str]:
		self.executor.shutdown(False)
		return (True, "Shutdown the ThreadPool and killed all timers.")


	@HalogenTool(
		"set_duration_reminder", 
		"Set a reminder (in integar seconds). Add detailed context to the message also.",
		["message:string", "seconds:integar"]
	)
	def set_duration_reminderw(self, chain: HalogenEvents.Chain, msg: str, sec: str):

		if not sec.isdigit():
			raise HalogenTaskError(f"{sec} is not a valid integar.")

		sec = int(sec)

		def timer():
			time.sleep(sec)
			
			ev = HalogenEvents.NotifyEvent(
				self.name(),
				HalogenEvents.make_timestamp(),
				chain,
				f"Timer Finished. Tell the user. Reminder: {msg}"
			)

			self.emit_event(ev)

		self.executor.submit(timer)

		return f"Set reminder to notify after {sec}s."


	@HalogenTool(
		"set_time_reminder", 
		"Set a time based reminder for today. Add context to the message also.",
		["message:string", "hour:integar(0-23)", "minute:integar(0-59)"]
	)
	def set_time_reminder(self, chain: HalogenEvents.Chain, msg: str, h: str, m: str):
		
		if not (h.isdigit() and m.isdigit()):
			raise HalogenTaskError(f"{sec} is not a valid integar.")

		h = int(h)
		m = int(m)

		current = datetime.now()

		if h <= current.hour and m <= current.minute:
			raise HalogenTaskError(f"Time {h}:{m} has already passed. Current : {h}:{m}.")


		def timer():
			
			while True:
				current = datetime().now()
				if h <= current.hour and m <= current.minute: break

			ev = HalogenEvents.NotifyEvent(
				self.name(),
				HalogenEvents.make_timestamp(),
				chain,
				f"Reminder for {h}:{m} Finished. Tell the user. Reminder: {msg}"
			)

			self.emit_event(ev)

		self.executor.submit(timer)

		return f"Set reminder to notify on {h}:{m}."



