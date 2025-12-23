from .connection import Connection
import subprocess

class ModelInterface:

	def __init__(self, command: str):
		self.command = command
		self.conn = Connection("127.0.0.1", 8080, True)

	def start(self):
		print("Starting model interface...")
		#subprocess.Popen(self.command, shell= True)
		self.conn.await_connection()
		self.conn.start()
		print("Connection established with model interface...")

	def send_input(self, msg: str):
		print("Sending input to model interface...")
		self.conn.send(msg)

	def get_response(self) -> str | None:
		return self.conn.get()
	


	
	