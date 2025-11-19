# app/utils.py
import os
import csv
import boto3
import tempfile
from typing import IO, List, Tuple

def validate_csv_header(file_path: str, required_cols: List[str]) -> Tuple[bool, List[str]]:
    """
    Check that CSV file has required columns in header.
    Returns (is_valid, missing_columns)
    """
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return False, required_cols
    header_lower = [h.strip().lower() for h in header]
    missing = [c for c in required_cols if c.lower() not in header_lower]
    return (len(missing) == 0), missing

# S3 helpers (optional: used when using S3 rather than local disk)
def s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

def upload_fileobj_to_s3(fileobj: IO, bucket: str, key: str):
    s3 = s3_client()
    s3.upload_fileobj(fileobj, bucket, key)

def download_s3_to_local(bucket: str, key: str, local_path: str):
    s3 = s3_client()
    s3.download_file(bucket, key, local_path)

def safe_remove(path: str):
    try:
        os.remove(path)
    except Exception:
        pass
