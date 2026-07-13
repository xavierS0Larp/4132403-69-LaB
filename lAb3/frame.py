import math
import struct

IP_HEADER_SIZE = 20
TCP_HEADER_SIZE = 20
ETH_HEADER_SIZE = 14

# MSS ของ loopback บนเครื่องทั่วไป (MTU 65535 - IP 20 - TCP 20)
MSS = 65495

# TCP flags
FIN, SYN, RST, PSH, ACK, URG = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20
FLAG_NAMES = [(URG, "URG"), (ACK, "ACK"), (PSH, "PSH"), (RST, "RST"), (SYN, "SYN"), (FIN, "FIN")]


def flags_to_text(flags):
    names = [name for bit, name in FLAG_NAMES if flags & bit]
    return "+".join(names) if names else "-"


def checksum(data):
    """คำนวณ Internet checksum (RFC 1071)"""
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def build_ipv4_header(src_ip, dst_ip, payload_len, ident=0x1C46, ttl=64):
    """ประกอบ IPv4 header 20 ไบต์ (protocol = 6 คือ TCP)"""
    version_ihl = (4 << 4) | 5          # version 4, header length 5 words = 20 bytes
    total_length = IP_HEADER_SIZE + TCP_HEADER_SIZE + payload_len
    flags_fragment = 0x4000             # Don't Fragment

    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,                              # DSCP / ECN
        total_length,
        ident,
        flags_fragment,
        ttl,
        6,                              # protocol = TCP
        0,                              # checksum (ใส่ 0 ก่อนคำนวณ)
        bytes(int(x) for x in src_ip.split(".")),
        bytes(int(x) for x in dst_ip.split(".")),
    )
    csum = checksum(header)
    return header[:10] + struct.pack("!H", csum) + header[12:], total_length, csum


def build_tcp_header(src_port, dst_port, seq, ack_num, flags=PSH | ACK, window=65535):
    """ประกอบ TCP header 20 ไบต์"""
    offset_reserved = (5 << 4)          # data offset 5 words = 20 bytes
    return struct.pack(
        "!HHIIBBHHH",
        src_port,
        dst_port,
        seq,
        ack_num,
        offset_reserved,
        flags,
        window,
        0,                              # checksum (ปกติ NIC/OS คำนวณให้)
        0,                              # urgent pointer
    )


def hexdump(data, limit=16):
    shown = data[:limit]
    text = " ".join(f"{b:02X}" for b in shown)
    if len(data) > limit:
        text += f" ... (+{len(data) - limit} bytes)"
    return text


def show_frame(direction, src_ip, src_port, dst_ip, dst_port, app_header, payload, seq=0, ack_num=0):
    """แสดงโครงสร้างข้อมูล 1 ข้อความ ตั้งแต่ชั้น Application ลงไปถึง Link Layer

    direction: "SEND" (ก่อนส่ง) หรือ "RECV" (ตอนรับ)
    app_header: header ระดับแอป 4 ไบต์ที่บอกขนาด payload (None ถ้าเป็นข้อความดิบ เช่น ACK)
    """
    app_len = len(app_header or b"") + len(payload)
    segments = max(1, math.ceil(app_len / MSS))
    first_seg_payload = min(app_len, MSS)

    ip_header, ip_total_len, ip_csum = build_ipv4_header(src_ip, dst_ip, first_seg_payload)
    tcp_header = build_tcp_header(src_port, dst_port, seq, ack_num)

    if direction == "SEND":
        title = "OUTGOING FRAME (before send)"
        endpoints = f"{src_ip}:{src_port} -> {dst_ip}:{dst_port}"
    else:
        title = "INCOMING FRAME (on receive)"
        endpoints = f"{dst_ip}:{dst_port} <- {src_ip}:{src_port}   (src = sender)"

    print()
    print("+" + "-" * 66 + "+")
    print(f"| {title:<64} |")
    print(f"| {endpoints:<64} |")
    print("+" + "-" * 66 + "+")

    # ---------- Layer 7 ----------
    if app_header:
        declared = struct.unpack("!I", app_header)[0]
        print("[Application Layer] Length-prefixed message")
        print(f"    App header (4B) : {hexdump(app_header)}   -> payload = {declared:,} bytes")
    else:
        print("[Application Layer] Raw message (no app header)")
    print(f"    Payload ({len(payload):,}B) : {hexdump(payload)}")
    print(f"    Total app bytes : {app_len:,}")

    # ---------- Layer 4 ----------
    print("[Transport Layer]   TCP")
    print(f"    Raw header (20B): {hexdump(tcp_header, 20)}")
    print(f"    Src port        : {src_port}")
    print(f"    Dst port        : {dst_port}")
    print(f"    Seq / Ack       : {seq} / {ack_num}")
    print(f"    Flags           : 0x{PSH | ACK:02X} ({flags_to_text(PSH | ACK)})")
    print(f"    Window / MSS    : 65535 / {MSS}")
    print(f"    Segments needed : {segments}  (payload {app_len:,}B / MSS {MSS}B)")

    # ---------- Layer 3 ----------
    print("[Network Layer]     IPv4")
    print(f"    Raw header (20B): {hexdump(ip_header, 20)}")
    print(f"    Version / IHL   : 4 / 5 (header 20 bytes)")
    print(f"    Total length    : {ip_total_len} bytes (IP 20 + TCP 20 + data {first_seg_payload})")
    print(f"    Flags           : DF (Don't Fragment)")
    print(f"    TTL / Protocol  : 64 / 6 (TCP)")
    print(f"    Checksum        : 0x{ip_csum:04X}")
    print(f"    Src IP -> Dst IP: {src_ip} -> {dst_ip}")

    # ---------- Layer 2 ----------
    if src_ip.startswith("127."):
        print("[Link Layer]        Loopback (no real Ethernet frame, never leaves the NIC)")
    else:
        print("[Link Layer]        Ethernet II (14B header + 4B FCS)")
    on_wire = segments * (ETH_HEADER_SIZE + IP_HEADER_SIZE + TCP_HEADER_SIZE) + app_len
    print(f"    Overhead/segment: Eth 14 + IP 20 + TCP 20 = 54 bytes")
    print(f"    Est. on wire    : {on_wire:,} bytes ({segments} segment(s))")
    print("+" + "-" * 66 + "+")
