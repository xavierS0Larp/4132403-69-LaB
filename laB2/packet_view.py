import uuid

ETHERNET_HEADER = 14  # dst MAC 6 + src MAC 6 + EtherType 2
IPV4_HEADER = 20  # ขนาดมาตรฐาน (ไม่มี options)
TCP_HEADER = 20  # ขนาดมาตรฐาน (ไม่มี options)


def get_mac():
    """ดึง MAC address ของเครื่องมาแสดงเป็นรูปแบบ xx:xx:xx:xx:xx:xx"""
    node = uuid.getnode()
    return ":".join(f"{(node >> shift) & 0xFF:02x}" for shift in range(40, -8, -8))


def hex_dump(data, width=16):
    """แสดงข้อมูลดิบแบบ hex + ASCII เหมือนที่เห็นใน Wireshark"""
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {offset:04x}  {hex_part:<{width * 3}} |{ascii_part}|")
    return "\n".join(lines)


def show_packet(sock, payload, direction):
    """พิมพ์โครงสร้างแพ็กเก็ตของ payload ที่กำลังจะส่งออกไป

    sock      : socket ที่เชื่อมต่ออยู่ (ใช้ดึง IP/port ต้นทาง-ปลายทาง)
    payload   : ข้อมูล (bytes) ที่จะส่ง
    direction : ข้อความกำกับ เช่น "CLIENT -> SERVER"
    """
    src_ip, src_port = sock.getsockname()
    dst_ip, dst_port = sock.getpeername()

    payload_size = len(payload)
    tcp_segment = TCP_HEADER + payload_size
    ip_packet = IPV4_HEADER + tcp_segment
    eth_frame = ETHERNET_HEADER + ip_packet

    mac = get_mac()

    print()
    print("=" * 68)
    print(f" PACKET TO SEND : {direction}   (total frame = {eth_frame} bytes)")
    print("=" * 68)

    # ชั้นที่ 2 - Data Link (Ethernet II)
    print(f"[L2] Ethernet II Frame .......... {eth_frame} bytes")
    print(f"     Destination MAC ............ {mac}")
    print(f"     Source MAC ................. {mac}")
    print("     EtherType .................. 0x0800 (IPv4)")

    # ชั้นที่ 3 - Network (IP)
    print(f"[L3] IPv4 Header ................ {IPV4_HEADER} bytes")
    print("     Version .................... 4")
    print(f"     Header Length .............. {IPV4_HEADER} bytes")
    print(f"     Total Length ............... {ip_packet} bytes")
    print("     TTL ........................ 64")
    print("     Protocol ................... 6 (TCP)")
    print(f"     Source IP .................. {src_ip}")
    print(f"     Destination IP ............. {dst_ip}")

    # ชั้นที่ 4 - Transport (TCP)
    print(f"[L4] TCP Header ................. {TCP_HEADER} bytes")
    print(f"     Source Port ................ {src_port}")
    print(f"     Destination Port ........... {dst_port}")
    print("     Flags ...................... PSH, ACK")
    print("     Window Size ................ 65535")

    # ชั้นที่ 7 - Application (ข้อมูลของเราเอง)
    print(f"[L7] Application Payload ........ {payload_size} bytes")
    print(hex_dump(payload))
    print("=" * 68)
																																																																																																			