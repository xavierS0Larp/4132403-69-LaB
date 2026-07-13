import socket
import struct
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from frame import show_frame

HOST = "127.0.0.1"
PORT = 5001

# ขนาดข้อความที่ต้องทดสอบตามโจทย์
SIZES = [
    ("100 B", 100),
    ("1 KB", 1 * 1024),
    ("10 KB", 10 * 1024),
    ("100 KB", 100 * 1024),
    ("1 MB", 1024 * 1024),
    ("10 MB", 10 * 1024 * 1024),
]

ROUNDS = 5  # ส่งซ้ำแต่ละขนาดแล้วเฉลี่ย ลดผลจากความแปรปรวน


def send_and_measure(client, size, seq=0, verbose=False):
    """ส่ง payload ขนาด size แล้วคืนเวลาที่ใช้ (วินาที) จนได้ ACK กลับมา"""
    payload = b"X" * size
    header = struct.pack("!I", size)

    if verbose:
        # ก่อนส่ง: แสดงว่าข้อมูลถูกห่อเป็น TCP/IP frame อย่างไร
        src_ip, src_port = client.getsockname()
        dst_ip, dst_port = client.getpeername()
        show_frame("SEND", src_ip, src_port, dst_ip, dst_port, header, payload, seq=seq)

    start = time.perf_counter()
    client.sendall(header + payload)
    ack = client.recv(3)
    elapsed = time.perf_counter() - start

    if verbose:
        # ขารับ: ACK ที่ server ตอบกลับมา
        src_ip, src_port = client.getpeername()
        dst_ip, dst_port = client.getsockname()
        show_frame("RECV", src_ip, src_port, dst_ip, dst_port, None, ack, ack_num=seq + len(header) + len(payload))

    if ack != b"ACK":
        raise RuntimeError("No ACK received from server")
    return elapsed


def plot(labels, times_ms, throughputs_mbps):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.bar(labels, times_ms, color="#4C78A8")
    ax1.set_title("Transfer Time")
    ax1.set_xlabel("Message Size")
    ax1.set_ylabel("Time (ms)")
    for i, value in enumerate(times_ms):
        ax1.text(i, value, f"{value:.2f}", ha="center", va="bottom")

    ax2.plot(labels, throughputs_mbps, marker="o", color="#F58518")
    ax2.set_title("Throughput")
    ax2.set_xlabel("Message Size")
    ax2.set_ylabel("Throughput (Mbps)")
    for i, value in enumerate(throughputs_mbps):
        ax2.text(i, value, f"{value:.1f}", ha="center", va="bottom")

    fig.tight_layout()
    fig.savefig("result.png", dpi=120)
    print("\nGraph saved to result.png")


def main():
    labels = []
    times_ms = []
    throughputs_mbps = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        print(f"Connected to server {HOST}:{PORT}")

        seq = 1  # จำลอง TCP sequence number (เริ่มหลัง SYN)

        for label, size in SIZES:
            samples = []
            for round_no in range(ROUNDS):
                # แสดงโครงสร้างแพ็กเก็ตแบบเต็มเฉพาะรอบแรกของแต่ละขนาด
                verbose = round_no == 0
                samples.append(send_and_measure(client, size, seq=seq, verbose=verbose))
                seq += 4 + size

            avg_seconds = sum(samples) / len(samples)

            # Throughput = ขนาดข้อมูล (bit) / เวลา (วินาที)
            mbps = (size * 8) / avg_seconds / 1_000_000

            labels.append(label)
            times_ms.append(avg_seconds * 1000)
            throughputs_mbps.append(mbps)

    print("\n" + "=" * 44)
    print("Client result (average of {} rounds)".format(ROUNDS))
    print("=" * 44)
    print(f"{'Size':>8} | {'Time (ms)':>10} | {'Throughput (Mbps)':>18}")
    print("-" * 44)
    for label, ms, mbps in zip(labels, times_ms, throughputs_mbps):
        print(f"{label:>8} | {ms:10.3f} | {mbps:18.2f}")

    plot(labels, times_ms, throughputs_mbps)


if __name__ == "__main__":
    main()
