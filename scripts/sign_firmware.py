from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import sys
import os

def sign_firmware(firmware_path, private_key_path="keys/private_key.pem"):
    print(f"Signing {firmware_path}...")

    # Load private key
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    # Read firmware
    with open(firmware_path, "rb") as f:
        firmware_data = f.read()

    # Sign using RSA-PSS with SHA256
    signature = private_key.sign(
        firmware_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    # Save signature alongside firmware
    sig_path = firmware_path + ".sig"
    with open(sig_path, "wb") as f:
        f.write(signature)

    print(f"Signature saved: {sig_path} ({len(signature)} bytes)")
    return sig_path

if __name__ == "__main__":
    firmware_path = sys.argv[1] if len(sys.argv) > 1 else "firmware/ecu_firmware_v1.0.0.bin"
    sign_firmware(firmware_path)