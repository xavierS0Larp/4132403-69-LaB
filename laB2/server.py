import socket
from datetime import datetime

from packet_view import show_packet

HOST = "127.0.0.1"
PORT = 5000


def log(tag, text):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {tag:<8} {text}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        log("SERVER", f"Listening on {HOST}:{PORT} ...")

        conn, addr = server.accept()
        with conn:
            client = f"{addr[0]}:{addr[1]}"
            log("CONNECT", f"Client connected from {client}")

            while True:
                data = conn.recv(1024)
                if not data:
                    log("CONNECT", f"Client {client} disconnected")
                    break

                message = data.decode("utf-8").strip()
                # แสดงข้อความที่รับมาจาก client พร้อมขนาดข้อมูลจริงเป็นไบต์
                log("RECV", f"from {client} ({len(data)} bytes): {message!r}")

                reply = "Bye" if message.lower() == "exit" else f"Received: {message}"
                payload = reply.encode("utf-8")

                # แสดงโครงสร้างของแพ็กเก็ตก่อนส่งกลับไปหา client
                show_packet(conn, payload, "SERVER -> CLIENT")

                conn.sendall(payload)
                log("SEND", f"to   {client}: {reply!r}")

                if message.lower() == "exit":
                    break

        log("SERVER", "Connection closed")


if __name__ == "__main__":
    main()
