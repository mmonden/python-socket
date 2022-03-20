from ast import Str
import sys, socket

class ClientSocket:
	BUFFERSIZE = 1
	end_of_header = "\r\n\r\n"
	stop = "\r\n"

	command = ""
	uri = ""
	port = 0

	soc = 0
	ip = ""

	request = ""
	response = ""

	charset = "ISO-8859-1"
	filetype = ""

	def input_commands(self, command, uri, port):
		self.command = command
		self.uri = uri
		self.port = int(port)

	def create_socket(self):
		try:
			self.ip = socket.gethostbyname(self.uri)
			self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	#	AF_INET = ipv4; SOCK_STREAM = TCP
			# self.soc.setblocking(0)		#	Voor select() later, select.select([socket], [], [], 5); imort select
			self.soc.settimeout(5)		#	Eerst dit testen 
		except socket.error as e:
			print(e)

	def connect_socket(self):
		try:
			self.soc.connect((self.ip, self.port))
		except socket.error as e:
			print(e)

	def close_connection(self):
		self.soc.shutdown(socket.SHUT_RDWR)
		self.soc.close()

	def req(self, command):
		length = 30

		if command == "HEAD":
			self.head(command)
		elif command == "GET":
			self.get(command)
		elif command == "POST":
			self.post(command, input(), length)
		elif command == "PUT":
			self.put(command, input() , length)

	def check_charset(self, header):
		substr = "charset="
		pos = header.find(substr)

		if pos != -1:
			pos += len(substr)

			d = header[pos]
			pos += 1
			while header[pos] != "\r":
				if header[pos] == "\"":
					break
				d += header[pos]
				pos += 1

			self.charset = d

	def check_file_type(self, header):
		substr = "Content-Type: "
		pos = header.find(substr)

		file_type_1 = ""
		file_type_2 = ""
		while header[pos + len(substr)] != ";":
			if header[pos + len(substr)] == "\r":
				break 
			
			if len(file_type_1) != 0:
				if file_type_1[-1] != "/":
					file_type_1 += header[pos + len(substr)]
				else:
					file_type_2 += header[pos + len(substr)]
			else:
				file_type_1 += header[pos + len(substr)]

			pos += 1

		return file_type_1[:-1], file_type_2

	def check_page_length(self, header):
		substr_cl = "Content-Length: "
		substr_te = "Transfer-Encoding: chunked"

		content_length = header.find(substr_cl)
		transfer_format = header.find(substr_te)
		
		if transfer_format != -1:
			return -1
		elif content_length != -1:
			s = ""
			while header[content_length + len(substr_cl)] != "\r":
				s += header[content_length + len(substr_cl)]
				content_length += 1

			return int(s)

	def retrieve_embedded_images(self):
		pass

	def get_header(self):
		buffer = self.soc.recv(self.BUFFERSIZE).decode(encoding=self.charset)
		
		while self.end_of_header not in buffer:
			buffer += self.soc.recv(self.BUFFERSIZE).decode(encoding=self.charset)

		return buffer

	def get_chunked(self):
		def in_buffer(buffer):
			if len(buffer) > len(self.stop):
				if buffer[-len(self.stop):] == self.stop:
					return False

			return True

		def get_chunksize():
			buffer = ""
			while in_buffer(buffer):
				buffer += self.soc.recv(self.BUFFERSIZE).decode(encoding=self.charset)

			if buffer[:len(self.stop)] == self.stop:
				buffer = buffer[len(self.stop):]

			return int(buffer[:-len(self.stop)], base=16)

		size = get_chunksize()
		while size != 0:
			buffer = ""

			while len(buffer) < size:
				size_counter = size - len(buffer)
				buffer += self.soc.recv(size_counter).decode(encoding=self.charset)

			self.response += buffer
			size = get_chunksize()

	def get_whole(self, chunk):
		while len(self.response) < chunk:
			self.response += self.soc.recv(chunk).decode(encoding=self.charset)

	def get(self, command):
		self.request = command + " / HTTP/1.1\r\nHost: " + self.uri + "\r\n\r\n"
		self.soc.send(self.request.encode())
		
		#	This call receives the header
		header = self.get_header()
		self.check_charset(header)
		chunk = self.check_page_length(header)		#	If chunked: chunk = -1
		filetype_1, self.filetype = self.check_file_type(header)

		if chunk == -1:
			self.get_chunked()
		else:
			self.get_whole(chunk)

		self.retrieve_embedded_images()

	def head(self, command):
		self.request = command + " / HTTP/1.1\r\nHost: " + self.uri + "\r\n\r\n"
		self.soc.send(self.request.encode())

		self.response = self.get_header()

	def post(self, command, path, length):
		self.request = command + " " + path + " HTTP/1.1\r\nHost: " + self.uri + "\r\n" + "Content-Length: " + str(length) + "\r\n\r\n"
		self.soc.send(self.request.encode())

	def put(self, command, path, length):
		self.request = command + " " + path + " / HTTP/1.1\r\nHost: " + self.uri + "\r\n" + "Content-Length: " + str(length) + "\r\n\r\n"
		self.soc.send(self.request.encode())

	def write_output(self, name):
		if self.filetype == "plain":
			self.filetype = "txt"
			
		print(name + "." + self.filetype)
		fout = open(name + "." + self.filetype, "w")

		fout.write(self.response)
		fout.close()

	def __init__(self, command, uri, port):
		self.input_commands(command, uri, port)
		self.create_socket()
		self.connect_socket()

		self.req(self.command)
		self.write_output(uri)

		self.close_connection()


# client = ClientSocket(sys.argv[1], sys.argv[2], sys.argv[3])