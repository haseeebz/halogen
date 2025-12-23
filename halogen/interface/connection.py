import socket
import threading
import queue
from typing import Optional

class Connection:
	
	def __init__(self, host: str, port: int, server: bool = False):
		
		self.host = host
		self.port = port
		self.server = server
		
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.send_queue = queue.Queue()
		self.recv_queue = queue.Queue()
		
		self.running = True

		if server:
			self.sock.bind((host, port), )
			self.sock.listen(1)           
		else:
			self.sock.connect((host, port))
			self.conn = self.sock

		self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
		self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
	
	
	def await_connection(self):
		if not self.server:
			raise Exception("Is not a server.")
		
		self.conn, _ = self.sock.accept()
		print("Connection Established.")



	def start(self):
		print("Started i/o threads...")
		self.recv_thread.start()
		self.send_thread.start()


	def _recv_loop(self):
		
		buffer = b""
		while self.running:
			try:
				data = self.conn.recv(4096)
				if not data:
					self.running = False
					break
				buffer += data
				while b"\n" in buffer:
					msg, buffer = buffer.split(b"\n", 1)
					self.recv_queue.put(msg.decode())
			except Exception as e:
				print("Recv error:", e)
				self.running = False
				break


	def _send_loop(self):
		while self.running:
			try:
				msg = self.send_queue.get()
				self.conn.sendall(msg.encode() + b"\n")
			except Exception as e:
				print("Send error:", e)
				self.running = False
				break


	def send(self, msg: str):
		self.send_queue.put(msg)


	def get(self) -> Optional[str]:
		try:
			return self.recv_queue.get_nowait()
		except queue.Empty:
			return None


	def close(self):
		self.running = False
		self.sock.close()
