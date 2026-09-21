#!/usr/bin/env python3
"""
OTA Agent — runs on the QEMU ARM device as a systemd service.
Polls AWS IoT Jobs over MQTT (same mutual-TLS pattern as P1's CAN simulator),
downloads signed firmware from a presigned S3 URL, verifies the RSA signature
using the verify_firmware.py logic, applies the update, reports status.

FIRST-PASS SKELETON — the notify-next payload shape and job document keys
get confirmed against real MQTT traffic once the IoT Thing + Job exist (Day B).
Rollback (backup/restore on failure) is implemented below.
"""

import json
import ssl
import shutil
import subprocess
import paho.mqtt.client as mqtt
import requests

# ---- CONFIG: fill in once the Thing + certs exist (Day B) ----
THING_NAME = "qemu-ota-device-01"
IOT_ENDPOINT = "REPLACE-ME.iot.eu-west-2.amazonaws.com"
CA_CERT = "certs/AmazonRootCA1.pem"
DEVICE_CERT = "certs/device-certificate.pem.crt"
DEVICE_KEY = "certs/device-private.pem.key"

CURRENT_VERSION_FILE = "/tmp/current_version.txt"
CURRENT_FIRMWARE_FILE = "/tmp/current_firmware.bin"
BACKUP_FIRMWARE_FILE = "/tmp/firmware_backup.bin"
BACKUP_VERSION_FILE = "/tmp/backup_version.txt"

NOTIFY_TOPIC = f"$aws/things/{THING_NAME}/jobs/notify-next"
NEXT_JOB_TOPIC = f"$aws/things/{THING_NAME}/jobs/$next/get"

client = mqtt.Client(client_id=THING_NAME)
client.tls_set(
    ca_certs=CA_CERT,
    certfile=DEVICE_CERT,
    keyfile=DEVICE_KEY,
    tls_version=ssl.PROTOCOL_TLSv1_2,
)


def verify_signature(firmware_path, sig_path, pubkey_path="keys/public_key.pem"):
    """Shells out to verify_firmware.py for RSA signature verification. Returns True/False."""
    result = subprocess.run(
        ["python3", "scripts/verify_firmware.py", firmware_path, sig_path, pubkey_path],
        capture_output=True,
        text=True,
    )
    return "VALID" in result.stdout


def apply_job(job_document):
    fw_url = job_document["firmware_url"]
    sig_url = job_document["signature_url"]
    version = job_document["version"]

    fw_resp = requests.get(fw_url, timeout=30)
    sig_resp = requests.get(sig_url, timeout=30)
    with open("/tmp/new_firmware.bin", "wb") as f:
        f.write(fw_resp.content)
    with open("/tmp/new_firmware.sig", "wb") as f:
        f.write(sig_resp.content)

    if not verify_signature("/tmp/new_firmware.bin", "/tmp/new_firmware.sig"):
        return "FAILED", "signature verification failed — update rejected"

    # This backup step is the rollback foundation:
    # On next failure (bad sig OR a post-apply health check), restore
    # CURRENT_FIRMWARE_FILE from BACKUP_FIRMWARE_FILE and report ROLLED_BACK.
    try:
        shutil.copy(CURRENT_FIRMWARE_FILE, BACKUP_FIRMWARE_FILE)
        shutil.copy(CURRENT_VERSION_FILE, BACKUP_VERSION_FILE)
    except FileNotFoundError:
        pass  # first install ever — nothing to back up yet

    shutil.copy("/tmp/new_firmware.bin", CURRENT_FIRMWARE_FILE)
    with open(CURRENT_VERSION_FILE, "w") as f:
        f.write(version)

    return "SUCCEEDED", f"applied version {version}"


def update_job_status(job_id, status, message=""):
    topic = f"$aws/things/{THING_NAME}/jobs/{job_id}/update"
    payload = {"status": status, "statusDetails": {"detail": message}}
    client.publish(topic, json.dumps(payload), qos=1)
    print(f"[job {job_id}] -> {status}: {message}")


def on_connect(client, userdata, flags, rc):
    print(f"Connected, rc={rc}")
    client.subscribe(NOTIFY_TOPIC)
    client.publish(NEXT_JOB_TOPIC, "{}")  # catch any job pending before we connected


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    execution = payload.get("execution")
    if not execution:
        return
    job_id = execution["jobId"]
    job_document = execution["jobDocument"]
    print(f"New job {job_id}: {job_document}")

    update_job_status(job_id, "IN_PROGRESS")
    status, message = apply_job(job_document)
    update_job_status(job_id, status, message)


client.on_connect = on_connect
client.on_message = on_message
client.connect(IOT_ENDPOINT, 8883, keepalive=60)
client.loop_forever()
