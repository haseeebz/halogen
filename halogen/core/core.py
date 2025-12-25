from ..adapters.connection import HalogenConnection
from halogen.adapters.reason import ReasoningAdapter

class HalogenCore:

	def __init__(self):
		self.reasoning_adapter = ReasoningAdapter("python3 model/adapter.py")
		self.reasoning_adapter.start()
		self.loop()

	def loop(self):
		self.waiting = False

		while self.reasoning_adapter.conn.is_alive():

			user_input = input()
			self.reasoning_adapter.ask(user_input)

			msg = self.reasoning_adapter.get_response()

			print(msg)

		print("Connection ended...")


