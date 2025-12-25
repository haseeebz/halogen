import subprocess
from .connection import HalogenConnection

class ReasoningAdapter:
	"The adapter that will do reasoning."


	def __init__(self, path: str):
		self.path = path
		self.conn = HalogenConnection("127.0.0.1", 8080, True)
		print(f"Reasoning adapter listening at {self.conn.host}:{self.conn.port}")
 

	def start(self):
		print(f"Starting reasoning adapter. Path : {self.path}")
		output = subprocess.Popen(self.path, shell=True)
		self.conn.await_connection()
		self.conn.start_connection()
		

	def ask(self, msg: str):
		self.conn.send(msg)

	
	def get_response(self) -> str | None:
		return self.conn.recv()