#!/usr/bin/env python3
"""
Creates an AWS IoT Job for a newly built and signed firmware version.
Called by the GitHub Actions workflow after build + sign + S3 upload.

Generates presigned S3 URLs for the firmware and its signature (24h
validity — plenty for a device to pick up and apply an update), builds
the job document in the exact shape ota_agent.py expects, and registers
the Job with AWS IoT Core so the device picks it up automatically on
its next connection.

Usage: python3 create_job.py <version>
"""
import sys
import json
import os
import boto3

BUCKET = "ota-firmware-store-ish"
THING_ARN = "arn:aws:iot:eu-west-2:831635639269:thing/qemu-ota-device-01"
REGION = "eu-west-2"


def main():
    if len(sys.argv) < 2:
        print("Usage: create_job.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    bin_key = f"firmware/v{version}/ecu_firmware_v{version}.bin"
    sig_key = f"firmware/v{version}/ecu_firmware_v{version}.bin.sig"

    s3 = boto3.client("s3", region_name=REGION)
    iot = boto3.client("iot", region_name=REGION)

    # NOTE: these presigned URLs use the CI job's own IAM access key
    # (a real, long-lived credential from GitHub Secrets) rather than
    # CloudShell's temporary session credentials — which is what kept
    # expiring mid-session during manual testing today. This is one
    # concrete advantage of automating this step.
    fw_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": bin_key}, ExpiresIn=86400
    )
    sig_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": sig_key}, ExpiresIn=86400
    )

    document = {
        "firmware_url": fw_url,
        "signature_url": sig_url,
        "version": version,
    }

    run_number = os.environ.get("GITHUB_RUN_NUMBER", "local")
    job_id = f"ota-job-ci-{version.replace('.', '-')}-{run_number}"

    iot.create_job(
        jobId=job_id,
        targets=[THING_ARN],
        document=json.dumps(document),
        targetSelection="SNAPSHOT",
    )

    print(f"Created job: {job_id}")
    print(f"Firmware: s3://{BUCKET}/{bin_key}")


if __name__ == "__main__":
    main()
