from halogen.interface.connection import Connection

from google import genai
from google.genai import types

from pydantic import BaseModel

class ModelResponse(BaseModel):
	msg: str


class Gemini():

	def __init__(self) -> None:

		self.conn = Connection("127.0.0.1", 8080)
		self.conn.start()

		with open("secrets.txt") as file:
			api_key = file.read()

		self.client = genai.Client(api_key = api_key)

		self.supported_models = [
			"gemini-2.5-pro",
			"gemini-2.5-flash",
			"gemini-2.5-flash-lite"
		]

		self.default_model = "gemini-2.5-pro"
		self.current_model = self.default_model
		self.thinking_budget = 0

		self.content_config = types.GenerateContentConfig(
			thinking_config = types.ThinkingConfig(thinking_budget=self.thinking_budget),
			response_schema = ModelResponse,
			response_mime_type = "application/json"
		)

		self.loop()


	@classmethod
	def name(cls) -> str:
		return "gemini"
	

	def loop(self):

		while True:
			
			user_input = self.conn.get()
			print(user_input)
			if not user_input: continue

			
			res = self.generate(user_input)

			self.conn.send(res)


	def generate(self, prompt: str) -> ModelResponse:
		
		try:
			response = self.send_request(prompt)
		except genai.errors.ClientError as e:
			msg = f"Client Error (Code:{e.code}) {e.message}!"
			print(msg)

		res: ModelResponse = response.parsed 
		return res.msg
	
		
	def send_request(self, content: str):

		response = self.client.models.generate_content(
			model = self.current_model,
			contents = content,
			config = self.content_config
		)

		return response