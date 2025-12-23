from halogen.interface.model import ModelInterface

class HalogenCore:

	def __init__(self):
		self.model = ModelInterface("python3 -m model")
		self.model.start()
		self.loop()

	def loop(self):
		while True:

			user_input = input("User: ")
			self.model.send_input(user_input)

			while True:
				res = self.model.get_response()

				if res:
					print(f"Bot: {res}")
