import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings


settings = get_settings()


class ObjectStorage:
    def __init__(self) -> None:
        self.bucket = settings.object_storage_bucket
        self.local_root = Path("storage")
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint,
            aws_access_key_id=settings.object_storage_access_key,
            aws_secret_access_key=settings.object_storage_secret_key,
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                self.local_root.mkdir(exist_ok=True)

    def put_bytes(self, key: str, body: bytes, content_type: str | None = None) -> str:
        self.ensure_bucket()
        try:
            extra = {"ContentType": content_type} if content_type else {}
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, **extra)
            return f"s3://{self.bucket}/{key}"
        except (BotoCoreError, ClientError, Exception):
            path = self.local_root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            return str(path)

    def read_bytes(self, uri: str) -> bytes:
        if uri.startswith("s3://"):
            _, _, bucket_and_key = uri.partition("s3://")
            bucket, _, key = bucket_and_key.partition("/")
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        return Path(uri).read_bytes()

    def public_url(self, uri: str) -> str:
        if uri.startswith("s3://"):
            _, _, bucket_and_key = uri.partition("s3://")
            bucket, _, key = bucket_and_key.partition("/")
            return f"{settings.object_storage_public_url}/{bucket}/{key}"
        return os.path.abspath(uri)


storage = ObjectStorage()

