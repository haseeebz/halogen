from halogen.adapters.connection import HalogenConnection
from google import genai
from google.genai import types, errors
from pydantic import BaseModel

class ModelResponse(BaseModel):
	content: str

class Gemini:

	def __init__(self):
		print("Starting connection...")
		self.conn = HalogenConnection("127.0.0.1", 8080, False)
		self.conn.connect()
		print("Connection established...")
		self.conn.start_connection()
		with open("secrets.txt") as file:
			self.api_key = file.read()

		self.client = genai.Client(api_key = self.api_key)

		self.supported_models = [
			"gemini-2.5-pro",
			"gemini-2.5-flash",
			"gemini-2.5-flash-lite"
		]

		self.default_model = "gemini-2.5-flash"
		self.current_model = self.default_model
		self.thinking_budget = 0

		self.content_config = types.GenerateContentConfig(
			thinking_config = types.ThinkingConfig(thinking_budget=self.thinking_budget),
			response_schema = ModelResponse,
			response_mime_type = "application/json"
		)

		self.loop()


	def loop(self):
		while self.conn.is_alive():
			msg = self.conn.recv()
			
			if msg:
				print("Received user input!")
				self.generate(msg)


	def generate(self, msg: str):
		
		try:
			response = self.send_request(msg)
		except errors.ClientError as e:
			msg = f"Client Error (Code:{e.code}) {e.message}!"
			self.conn.send(str(e))
			return

		res: ModelResponse = response.parsed
		
		print("Processed user input!")
		self.conn.send(res.content)
	
		
	def send_request(self, content: str):

		response = self.client.models.generate_content(
			model = self.current_model,
			contents = content,
			config = self.content_config
		)

		return response
	

Gemini()