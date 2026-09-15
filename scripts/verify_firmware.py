from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import sys

def verify_firmware(firmware_path, sig_path=None, public_key_path="keys/public_key.pem"):
    if sig_path is None:
        sig_path = firmware_path + ".sig"

    print(f"Verifying {firmware_path}...")

    with open(public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    with open(firmware_path, "rb") as f:
        firmware_data = f.read()

    with open(sig_path, "rb") as f:
        signature = f.read()

    try:
        public_key.verify(
            signature,
            firmware_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        print("SIGNATURE VALID — firmware is authentic and untampered")
        return True
    except InvalidSignature:
        print("SIGNATURE INVALID — firmware rejected")
        return False

if __name__ == "__main__":
    import sys
    firmware_path = sys.argv[1] if len(sys.argv) > 1 else "firmware/ecu_firmware_v1.0.0.bin"
    sig_path = sys.argv[2] if len(sys.argv) > 2 else None
    verify_firmware(firmware_path, sig_path)