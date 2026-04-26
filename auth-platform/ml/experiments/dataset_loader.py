"""Load governed dataset records from Postgres and images from S3."""


import boto3
import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
S3_ENDPOINT = "http://localhost:4566"


def get_s3():
    return boto3.client(
        "s3", endpoint_url=S3_ENDPOINT,
        aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1",
    )


def load_dataset_records(
    dataset_version: str,
    split: str = "all",
    limit: int | None = None,
) -> list[dict]:
    """Load reference image records for a dataset version."""
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    conditions = ["rdv.dataset_version = %s"]
    params: list = [dataset_version]

    if split != "all":
        conditions.append("rdm.split = %s")
        params.append(split)

    where = " AND ".join(conditions)
    limit_clause = f"LIMIT {limit}" if limit else ""

    cur.execute(f"""
        SELECT ri.id as reference_image_id, ri.reference_item_id, ri.region_code,
               ri.object_uri, rdm.split, rit.authenticity_status,
               rdv.dataset_version
        FROM reference_dataset_members rdm
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE {where}
        ORDER BY ri.region_code, ri.id
        {limit_clause}
    """, params)

    cols = [desc[0] for desc in cur.description]
    records = [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return records


def load_image_bytes(object_uri: str) -> bytes:
    """Download image bytes from S3 object URI."""
    parts = object_uri.replace("s3://", "").split("/", 1)
    s3 = get_s3()
    response = s3.get_object(Bucket=parts[0], Key=parts[1])
    return response["Body"].read()
