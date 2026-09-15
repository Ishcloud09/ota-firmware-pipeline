# Test script — simulates firmware tampering
# Used to verify that RSA signature verification catches corruption

input_path = "firmware/ecu_firmware_v1.0.0.bin"
output_path = "firmware/ecu_firmware_v1.0.0_corrupted.bin"

with open(input_path, "rb") as f:
    data = f.read()

# Overwrite bytes 100-108 with "TAMPERED"
corrupted = data[:100] + b'TAMPERED' + data[108:]

with open(output_path, "wb") as f:
    f.write(corrupted)

print(f"Original firmware:  {len(data)} bytes")
print(f"Corrupted firmware: {len(corrupted)} bytes")
print(f"Bytes 100-107 changed to: {corrupted[100:108]}")
print(f"Saved to: {output_path}")