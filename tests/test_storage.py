"""Tests for the storage module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_upload_to_gcs(tmp_path: Path):
    mock_blob = MagicMock()
    mock_blob.public_url = "https://storage.googleapis.com/test-bucket/attachments/abc123.pdf"

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    mock_storage_module = MagicMock()
    mock_storage_module.Client.return_value = mock_client

    # google.cloud must have .storage attribute pointing to our mock
    mock_google_cloud = MagicMock()
    mock_google_cloud.storage = mock_storage_module

    mock_google = MagicMock()
    mock_google.cloud = mock_google_cloud

    test_file = tmp_path / "doc.pdf"
    test_file.write_bytes(b"fake-pdf")

    with patch.dict("os.environ", {"GCS_BUCKET": "test-bucket"}), \
         patch.dict(sys.modules, {
             "google": mock_google,
             "google.cloud": mock_google_cloud,
             "google.cloud.storage": mock_storage_module,
         }), \
         patch("storage.uuid") as mock_uuid:
        mock_uuid.uuid4.return_value = MagicMock(hex="abc123")
        from storage import upload_to_gcs
        url = upload_to_gcs(test_file)

    assert url == "https://storage.googleapis.com/test-bucket/attachments/abc123.pdf"
    mock_client.bucket.assert_called_once_with("test-bucket")
    mock_bucket.blob.assert_called_once_with("attachments/abc123.pdf")
    mock_blob.upload_from_filename.assert_called_once_with(str(test_file))
    mock_blob.make_public.assert_called_once()
