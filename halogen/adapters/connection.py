import socket, time
from queue import Queue, Empty
from threading import Thread, Lock

class HalogenConnection:

	def __init__(self, host: str, port: int, server: bool = False):

		self.host: str = host
		self.port: int = port

		self.is_server: bool = server

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.settimeout(0.05)

		if self.is_server:
			self.socket.bind((host, port), )
			self.socket.listen(1) 

		self.conn: socket.socket

		self.send_queue = Queue()
		self.recv_queue = Queue()

		self.is_running: bool = False
		self.lock = Lock()

		self._send_thread = Thread(target = self._send_loop, daemon= True)
		self._recv_thread = Thread(target = self._recv_loop, daemon= True)


	def _send_loop(self):
		while self.is_running:
			try:
				msg = self.send_queue.get(False, 0.05)
				self.conn.sendall(msg.encode() + b"\n")

			except Empty:
				time.sleep(0.05)

			except Exception as e:
				print(f"Error encountered in send:\n{e}")
				self.conn.sendall(b"")
				self.end_connection()
				

	def _recv_loop(self):
		buffer = b""
		while self.is_running:
			try:
				data = self.conn.recv(1024)
				if not data:
					self.end_connection()
				buffer += data
				while b"\n" in buffer:
					msg, buffer = buffer.split(b"\n", 1)
					self.recv_queue.put(msg)
				
			except socket.timeout:
				time.sleep(0.05)

			except Exception as e:
				print(f"Error encountered in recv:\n{e}")
				self.end_connection()


	def await_connection(self):

		if not self.is_server:
			raise Exception("Is not a server!")
		
		while True:
			try:
				self.conn, _ = self.socket.accept()
				break
			except TimeoutError:
				time.sleep(0.1)
	

	def connect(self):

		if self.is_server:
			raise Exception("Is a server!")
		
		self.socket.connect((self.host, self.port))
		self.conn = self.socket
			

	def start_connection(self):

		self.is_running = True
		self._send_thread.start()
		self._recv_thread.start()


	def end_connection(self):
		with self.lock:
			self.send_queue.put(b"")
			self.is_running = False
			self._send_thread.join()
			self._send_thread.join()
			self.conn.close()


	def send(self, msg: str):
		self.send_queue.put(msg)


	def recv(self) -> str | None:
		try:
			return self.recv_queue.get(False)
		except Empty:
			return None
		

	def is_alive(self) -> bool:
		return self.is_running