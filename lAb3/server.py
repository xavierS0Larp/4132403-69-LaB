import socket
import struct
import time
from collections import OrderedDict

from frame import show_frame

HOST = "127.0.0.1"
PORT = 5001

# ทุกข้อความมี header 4 ไบต์บอกขนาด payload ที่ตามมา
HEADER_SIZE = 4


def recv_exactly(conn, size):
    """อ่านข้อมูลให้ครบ size ไบต์ (TCP อาจส่งมาไม่ครบในรอบเดียว)"""
    chunks = []
    received = 0
    while received < size:
        chunk = conn.recv(min(4096, size - received))
        if not chunk:
            return None
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


def format_size(size):
    """แปลงจำนวนไบต์เป็นข้อความอ่านง่าย เช่น 100 B, 10 KB"""
    if size >= 1024 and size % 1024 == 0:
        return f"{size // 1024} KB"
    return f"{size} B"


def print_summary(stats, total_bytes, started_at):
    """สรุปผลรวมของข้อมูลที่ server ได้รับทั้งหมด"""
    if not stats:
        print("\nNo data received")
        return

    session_seconds = time.perf_counter() - started_at

    print("\n" + "=" * 62)
    print("Summary (average per message size)")
    print("=" * 62)
    print(f"{'Size':>8} | {'Rounds':>6} | {'Avg time (ms)':>13} | {'Avg Mbps':>10}")
    print("-" * 62)

    for size, samples in stats.items():
        rounds = len(samples)
        avg_seconds = sum(samples) / rounds
        mbps = (size * 8) / avg_seconds / 1_000_000 if avg_seconds > 0 else 0.0
        print(
            f"{format_size(size):>8} | {rounds:>6} | "
            f"{avg_seconds * 1000:13.3f} | {mbps:10.2f}"
        )

    print("-" * 62)
    total_messages = sum(len(samples) for samples in stats.values())
    print(f"Total messages : {total_messages}")
    print(f"Total received : {total_bytes:,} bytes ({total_bytes / 1024:.1f} KB)")
    print(f"Session time   : {session_seconds:.3f} s")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        print(f"Server listening on {HOST}:{PORT}")

        conn, addr = server.accept()
        with conn:
            print(f"Connected by {addr}\n")

            # เก็บเวลารับของแต่ละขนาด เพื่อนำไปสรุปตอนจบ
            stats = OrderedDict()
            total_bytes = 0
            count = 0
            seq = 1  # จำลอง TCP sequence number ของฝั่ง server
            started_at = time.perf_counter()

            client_ip, client_port = conn.getpeername()
            my_ip, my_port = conn.getsockname()

            rows = []
            while True:
                header = recv_exactly(conn, HEADER_SIZE)
                if not header:
                    break

                size = struct.unpack("!I", header)[0]

                start = time.perf_counter()
                payload = recv_exactly(conn, size)
                if payload is None:
                    break
                elapsed = time.perf_counter() - start

                count += 1
                total_bytes += len(payload)
                stats.setdefault(len(payload), []).append(elapsed)

                # แสดงโครงสร้างข้อมูลที่รับมา (รอบแรกของแต่ละขนาดเท่านั้น)
                first_of_size = len(stats[len(payload)]) == 1
                if first_of_size:
                    show_frame(
                        "RECV", client_ip, client_port, my_ip, my_port,
                        header, payload, ack_num=seq,
                    )

                mbps = (len(payload) * 8) / elapsed / 1_000_000 if elapsed > 0 else 0.0
                rows.append((count, len(payload), elapsed, mbps))

                # ตอบ ACK กลับไปเพื่อให้ client วัดเวลาไป-กลับได้
                if first_of_size:
                    show_frame(
                        "SEND", my_ip, my_port, client_ip, client_port,
                        None, b"ACK", seq=seq,
                    )
                conn.sendall(b"ACK")
                seq += 3

            print("\n" + "=" * 42)
            print("Received messages")
            print("=" * 42)
            print(f"{'#':>3} | {'Size':>8} | {'Time (ms)':>10} | {'Mbps':>8}")
            print("-" * 42)
            for no, nbytes, elapsed, mbps in rows:
                print(
                    f"{no:>3} | {format_size(nbytes):>8} | "
                    f"{elapsed * 1000:10.3f} | {mbps:8.2f}"
                )

            print_summary(stats, total_bytes, started_at)

        print("\nConnection closed")


if __name__ == "__main__":
    main()
