from encodings import utf_8
import threading
import socket
import time
import os
from builtins import print
path = os.path.dirname(os.path.abspath(__file__))

IP = socket.gethostbyname(socket.gethostname())
PORT = 8085
ADDR = (IP, PORT)
SIZE = 1
FORMAT = "utf-8"
DISCONNECT_MSG = "DISCONNECT!"
STATUS_CODE = {200: "200 OK", 404: "404 Not Found",
               400: "400 Bad Request", 500: "500 Server Error", 304: "304 Not Modified"}
TIME = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime())

"""
    start up server and activate threading
"""
def main():
    print(f"[STARTING] {IP, PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[LISTENING] ON {IP} : {PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

        print(f"[ACTIVE_CONNECTIONS] {threading.active_count()-1}")

"""
    first the header of the html message is retreived, and split into parts. afterwards a check to see if an additional body should still be retreived
    based on the method. if so, the body will be added and the rest of the program works with 'parts' as an input
    parts = [method, uri, http-version, headers(dictionnary), body]
"""
def handle_client(conn, addr):
    print(f"[NEW_CONNECTION] {addr} connected.")
    connected = True

    while connected:
        header = get_PART(conn, SIZE)
        parts = split_HEADER(header, conn)

        # Http requirement
        if check_HOST(parts, conn):
            if parts[0] == "PUT" or parts[0] == "POST":
                length_next_chunk = int(parts[3]['Content-Length'])
                body = get_PART(conn, length_next_chunk)
                parts.append(body)

            redirect_msg(parts, conn)

    conn.close()

    print(f"[ACTIVE_CONNECTIONS] {threading.active_count()-2}")

"""
    redirects request according to the method
"""
def redirect_msg(parts, conn):
    method = parts[0]

    if method == 'GET':
        handle_GET(parts, conn)
    elif method == 'HEAD':
        handle_HEAD(parts, conn)
    elif method == 'PUT':
        handle_PUT(parts, conn)
    elif method == 'POST':
        handle_POST(parts, conn)
    else:
        stat_line = STATUS_CODE[400]
        response_body = "<html><body><h1>No valid request</h1></body></html>"
        c_length = len(response_body.encode(FORMAT))
        headers = f"DATE: {TIME}\r\nContent-Type: text/plain\r\nContent-Length: {c_length}"

        respond(conn, stat_line, headers, response_body)

        return

    return

"""
    first: retrieve the path to this directory, second: give the file the correct name and extention, third: write file with body and respond
"""
def handle_PUT(parts, conn):
    path = os.path.dirname(os.path.abspath(__file__))
    file_name = parts[1][1:]
    file_name = file_name.split('.', 2)[0]+".txt"

    with open(os.path.join(path, file_name), 'w') as newfile:
        newfile.write(parts[4])

    status_line = "HTTP/1.1 " + STATUS_CODE[200]
    response_body = "<html><body><h1>The file was created.</h1></body></html>"
    c_length = len(response_body.encode(FORMAT))
    headers = f"DATE: {TIME}\r\nContent-Type: text/plain\r\nContent-Length: {c_length}"

    respond(conn, status_line, headers, response_body)

    return

"""
    This function works a lot like the handle_PUT function, but first a little check wether or not the file already exists.
    if not, handle put will be called, else, the body wil be appended in the correct file. Finally, respond.
"""    
def handle_POST(parts, conn):
    file_name = parts[1][1:]
    file_name = file_name.split('.', 2)[0]+".txt"
    path = os.path.dirname(os.path.abspath(__file__))
    dir_list = os.listdir(path)

    if file_name not in dir_list:
        handle_PUT(parts, conn)
    else:
        with open(os.path.join(path, file_name), 'a') as newfile:
            newfile.write(parts[4])

        status_line = "HTTP/1.1 " + STATUS_CODE[200]
        response_body = "<html><body><h1>the content was succesfully appended.</h1></body></html>"
        c_length = len(response_body.encode(FORMAT))
        headers = f"DATE: {TIME}\r\nContent-Type: text/plain\r\nContent-Length: {c_length}"

        respond(conn, status_line, headers, response_body)

    return

"""
    first, retrieve the path to this directory, if / is requested, the function will restart with /index.html as a parameter
    check if file exists in this directory
    check If-Modified-Since header
    configure correct content types --> only support for images, and text (html/txt)
    if everything is ok, the request is granted.
    a shortcut is made by the handleHEAD function, leaving the response body behind
"""
def handle_GET(parts, conn, head=False):
    path = os.path.dirname(os.path.abspath(__file__))
    dir_list = os.listdir(path)

    if parts[1][1:] == "":
        parts[1] = "/index.html"

        return handle_GET(parts, conn, head)

    if parts[1][1:] not in dir_list:
        status_line = "HTTP/1.1 " + STATUS_CODE[404]
        response_body = "<html><body><h1>File not found.</h1></body></html>"
        c_length = len(response_body.encode(FORMAT))
        headers = f"DATE: {TIME}\r\nContent-Type: text/html\r\nContent-Length: {c_length}"

        respond(conn, status_line, headers, response_body)

        return

    headers: dict = parts[3]

    if "If-Modified-Since" in headers.keys():
        path = os.path.join(path, parts[1][1:])
        timem = headers["If-Modified-Since"]
        file_time = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime(os.path.getmtime(path)))

        if file_time < timem:
            status_line = "HTTP/1.1 " + STATUS_CODE[304]
            response_body = "<html><body><h1>File has not been modified.</h1></body></html>"
            c_length = len(response_body.encode(FORMAT))
            headers = f"DATE: {TIME}\r\nContent-Type: text/html\r\nContent-Length: {c_length}"

            respond(conn, status_line, headers, response_body)

            return

    type = parts[1].split('.', 2)[1]

    try:
        if type != "html" or type != "txt":
            content_type = f"image/{parts[1].split('.', 2)[1]}"
        elif type == 'html':
            content_type = "text/html"
        elif type == 'txt':
            content_type = "text/plain"
    except:
        stat_line = STATUS_CODE[500]
        response_body = "<html><body><h1>500 INTERNAL SERVER ERROR</h1></body></html>"
        c_length = len(response_body.encode(FORMAT))
        headers = f"DATE: {TIME}\r\nContent-Type: text/plain\r\nContent-Length: {c_length}"

        respond(conn, stat_line, headers)

        conn.close()

    path = os.path.join(path, parts[1][1:])
    length = os.path.getsize(path)

    with open(path, "rb") as data:
        all_bytes = data.read(length)

    status_line = "HTTP/1.1 " + STATUS_CODE[200]
    response_body = all_bytes
    c_length = length
    headers = f"DATE: {TIME}\r\nContent-Type: {content_type}\r\nContent-Length: {c_length}"

    if head:
        respond(conn, status_line, headers)
    else:
        respond(conn, status_line, headers, response_body)

    return

def handle_HEAD(parts, conn):
    handle_GET(parts, conn, True)

"""
    checks if the host header field is given in request
"""
def check_HOST(parts, conn):
    heads: dict = parts[3]

    if 'Host' not in heads.keys():
        stat_line = STATUS_CODE[400]
        response_body = "<html><body><h1>No host field given</h1></body></html>"
        c_length = len(response_body.encode(FORMAT))
        headers = f"DATE: {TIME}\r\nContent-Type: text/plain\r\nContent-Length: {c_length}"

        respond(conn, stat_line, headers, response_body)

        return False

    return True

"""
    send response to client
"""
def respond(conn, status_line, headers, msg_body=b""):
    try:
        msg = (status_line + "\r\n" + headers + "\r\n\r\n").encode(FORMAT)
        msg = msg + msg_body + "\r\n".encode(FORMAT)
    except:
        pass

    conn.send(msg)

    return

"""
    accept client input
"""
def get_PART(conn, size):
    buffer = ""
    while "\r\n\r\n" not in buffer:
        buffer += conn.recv(size).decode(FORMAT)
    return buffer

"""
    splits the request without the body in parts
"""
def split_HEADER(msg, conn):
    if msg == DISCONNECT_MSG:
        conn.close()

        return

    try:
        request = ''.join((line + '\n') for line in msg.splitlines())
        request_head = request.splitlines()  # List of request and headers
        request_line = request_head[0]

        method, uri, http = request_line.split(' ', 3)
        headers = {}

        for head in request_head[1:len(request_head)-1]:
            elem = head.split(": ", 1)
            headers[elem[0]] = elem[1]
    except:
        stat_line = STATUS_CODE[500]
        response_body = "<html><body><h1>500 INTERNAL SERVER ERROR</h1></body></html>"
        c_length = len(response_body.encode(FORMAT))
        headers = f"DATE: {TIME}\r\nContent-Type: text/plain\r\nContent-Length: {c_length}"

        respond(conn, stat_line, headers)

        conn.close()

    return [method, uri, http, headers]

main()
