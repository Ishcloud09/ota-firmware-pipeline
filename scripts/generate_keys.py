from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import os

def generate_rsa_keypair():
    os.makedirs("keys", exist_ok=True)

    print("Generating RSA-2048 key pair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Save private key (NEVER commit this)
    with open("keys/private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save public key (safe to commit)
    public_key = private_key.public_key()
    with open("keys/public_key.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print("Keys generated:")
    print("  keys/private_key.pem  (KEEP SECRET — never commit)")
    print("  keys/public_key.pem   (safe to commit — device uses this)")

if __name__ == "__main__":
    generate_rsa_keypair()