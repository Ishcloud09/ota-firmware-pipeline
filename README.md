# Secure OTA Firmware Pipeline

A cloud-to-device over-the-air (OTA) firmware update pipeline for an embedded Linux device, built around AWS IoT Core and cryptographically signed firmware — the delivery-direction counterpart to [ecu-fault-diagnostics](https://github.com/Ishcloud09/ecu-fault-diagnostics), which handles device-to-cloud telemetry.

## What this proves

A firmware update pushed from a CI/CD pipeline is automatically discovered, downloaded, cryptographically verified, and either applied or rejected by a device — with no manual intervention, and with automatic rollback if a signed-but-broken update passes verification but fails a post-install health check.

## Architecture

```
git tag push
      │
      ▼
GitHub Actions ──build──> sign (RSA-PSS/SHA256) ──upload──> S3
      │
      └──create Job──> AWS IoT Core (IoT Jobs)
                              │
                              ▼
                    QEMU ARM device (Debian Linux)
                    running ota_agent.py as a systemd service:
                      1. Polls IoT Jobs over mutual-TLS MQTT
                      2. Downloads firmware + signature via presigned S3 URL
                      3. Verifies the RSA signature
                      4. Applies the update, or rejects it
                      5. Runs a post-apply health check
                      6. Rolls back to the last known-good version on failure
                      7. Reports status (SUCCEEDED / FAILED) back to AWS
```

**Security principle:** the pipeline that builds and signs firmware is never the same system that decides whether to trust it. GitHub Actions only ever *signs* (using a private key held in GitHub Secrets); only the device *verifies* (using the public key), and only the device decides whether to apply an update. A compromised CI/CD system could push a bad artifact, but it could never make the device accept one.

## Why Debian instead of Yocto

The device layer runs a stock Debian ARM image under QEMU rather than a custom Yocto-built distribution. This was a deliberate scoping decision: the architecture, systemd integration, and OTA agent behavior are identical regardless of the base OS, and a Yocto build adds significant build time without changing what this project demonstrates. The design is Yocto-compatible — swapping the base image is an infrastructure change, not an architecture change.

## Regulatory context

The device-side verify/apply/rollback flow implements the core technical intent of **UN R156** (software update management), which requires that a vehicle ECU never be left in a failed state after a rejected or unsuccessful update.

## Components

| Path | Purpose |
|---|---|
| `firmware/build_firmware.py` | Produces a firmware binary (magic number, version, timestamp, SHA256, simulated payload) |
| `scripts/generate_keys.py` | Generates the RSA-2048 keypair used for signing/verification |
| `scripts/sign_firmware.py` | Signs a firmware binary (RSA-PSS, SHA256) |
| `scripts/verify_firmware.py` | Verifies a firmware binary against its signature |
| `scripts/corrupt_firmware.py` | Test utility — simulates tampering, for verifying rejection behavior |
| `scripts/create_job.py` | Generates presigned S3 URLs and registers an AWS IoT Job |
| `qemu-device/ota_agent.py` | Runs on the device — polls IoT Jobs, verifies, applies, rolls back |
| `qemu-device/ota-agent.service` | systemd unit running the agent persistently on the device |
| `.github/workflows/firmware_deploy.yml` | CI/CD — build, sign, upload, and deploy on every version tag push |

## Running it

**Trigger a deployment:**
```bash
git tag v1.x.x
git push --tags
```
This alone builds, signs, uploads, and creates the IoT Job — no manual AWS console or CLI steps.

**Device side** (once, to stand up the QEMU ARM VM and run the agent):
```bash
qemu-system-aarch64 -machine virt -cpu cortex-a57 -m 1G \
  -device virtio-blk-device,drive=hd -drive file=image.qcow2,if=none,id=hd \
  -device virtio-net-device,netdev=net -netdev user,id=net,hostfwd=tcp:127.0.0.1:2222-:22 \
  -kernel kernel -initrd initrd -nographic -append "root=LABEL=rootfs console=ttyAMA0"

python3 qemu-device/ota_agent.py
```

## Status

**Complete and demonstrated:**
- RSA-2048 firmware signing and verification, including rejection of tampered firmware
- Cloud-to-device delivery over AWS IoT Jobs with mutual-TLS device authentication
- Automatic rollback on post-apply health-check failure
- Full CI/CD: a git tag push builds, signs, uploads, and deploys with no manual steps

**Planned:**
- Terraform IaC for the AWS resources (S3, IoT Thing, IoT policy, CloudWatch alarm) — currently provisioned manually via the AWS Console
- CloudWatch alarm + SNS alert on IoT Job failure rate
- `SYSTEMS_REQUIREMENTS.md` mapping implemented behavior to specific UN R156 clauses
