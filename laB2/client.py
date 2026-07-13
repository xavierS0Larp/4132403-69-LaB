import socket

from packet_view import show_packet

HOST = "127.0.0.1"
PORT = 5000


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        print(f"Connected to server {HOST}:{PORT}")
        print('Type a message ("exit" to quit)')

        while True:
            message = input("\nYou: ").strip()
            if not message:
                continue

            payload = message.encode("utf-8")

            # แสดงโครงสร้างของแพ็กเก็ตก่อนส่งออกไปจริง
            show_packet(client, payload, "CLIENT -> SERVER")

            client.sendall(payload)

            data = client.recv(1024)
            if not data:
                print("Server closed the connection")
                break

            print(f"Server: {data.decode('utf-8')}")

            if message.lower() == "exit":
                break


if __name__ == "__main__":