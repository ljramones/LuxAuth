"""S3 helpers for object storage via boto3 (LocalStack-compatible)."""

from __future__ import annotations

from typing import Any

import boto3


_s3_client: Any | None = None


def get_s3_client() -> Any:
    """Return a cached boto3 S3 client configured for the current settings."""
    global _s3_client  # noqa: PLW0603
    if _s3_client is None:
        from auth_common.config import Settings

        settings = Settings()
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )
    return _s3_client


def upload_file(
    bucket: str,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload bytes to S3 and return the object URI (s3://bucket/key)."""
    client = get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"s3://{bucket}/{key}"


def download_file(bucket: str, key: str) -> bytes:
    """Download an object from S3 and return its contents as bytes."""
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()  # type: ignore[no-any-return]


def generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 3600,
) -> str:
    """Generate a presigned URL for downloading an S3 object."""
    client = get_s3_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )
    return url
