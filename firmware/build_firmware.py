import os
import struct
import hashlib
from datetime import datetime

def build_firmware(version="1.0.0"):
    """
    Builds a fake firmware binary.
    In real life this would be a compiled ECU binary.
    Structure:
      - 4 bytes: magic number (0xDEADBEEF)
      - 4 bytes: version major.minor.patch encoded
      - 8 bytes: build timestamp
      - 2048 bytes: simulated firmware payload (random bytes)
      - 32 bytes: SHA256 hash of the above
    """
    print(f"Building firmware version {version}...")

    # Magic number
    magic = struct.pack(">I", 0xDEADBEEF)

    # Version
    major, minor, patch = [int(x) for x in version.split(".")]
    ver_bytes = struct.pack(">BBH", major, minor, patch)

    # Timestamp
    ts = int(datetime.utcnow().timestamp())
    ts_bytes = struct.pack(">Q", ts)

    # Simulated payload — random bytes representing ECU code
    payload = os.urandom(2048)

    # SHA256 of everything so far
    content = magic + ver_bytes + ts_bytes + payload
    checksum = hashlib.sha256(content).digest()

    binary = content + checksum

    output_path = f"firmware/ecu_firmware_v{version}.bin"
    with open(output_path, "wb") as f:
        f.write(binary)

    print(f"Firmware built: {output_path} ({len(binary)} bytes)")
    print(f"SHA256: {checksum.hex()}")
    return output_path

if __name__ == "__main__":
    build_firmware("1.0.0")