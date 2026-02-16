from utils import minio_utils


class _FakePaginator:
    def __init__(self, pages):
        self.pages = pages
        self.kwargs_seen = None

    def paginate(self, **kwargs):
        self.kwargs_seen = kwargs
        return self.pages


class _FakeS3Client:
    def __init__(self, pages):
        self._paginator = _FakePaginator(pages)

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self._paginator


def test_list_image_keys_uses_pagination_and_supported_extensions(monkeypatch):
    pages = [
        {
            "Contents": [
                {"Key": "top/a.png"},
                {"Key": "top/b.txt"},
            ]
        },
        {
            "Contents": [
                {"Key": "nested/one/two/c.pdf"},
                {"Key": "nested/one/two/d.tiff"},
            ]
        },
    ]
    fake_s3 = _FakeS3Client(pages)
    monkeypatch.setattr(minio_utils, "get_s3_client", lambda: fake_s3)

    keys = minio_utils.list_image_keys()

    assert keys == ["top/a.png", "nested/one/two/c.pdf", "nested/one/two/d.tiff"]
    assert fake_s3._paginator.kwargs_seen == {"Bucket": minio_utils.BUCKET_NAME}


def test_list_image_keys_respects_prefix(monkeypatch):
    pages = [{"Contents": [{"Key": "dept/team/asset.gif"}]}]
    fake_s3 = _FakeS3Client(pages)
    monkeypatch.setattr(minio_utils, "get_s3_client", lambda: fake_s3)

    keys = minio_utils.list_image_keys(prefix="dept/team/")

    assert keys == ["dept/team/asset.gif"]
    assert fake_s3._paginator.kwargs_seen == {
        "Bucket": minio_utils.BUCKET_NAME,
        "Prefix": "dept/team/",
    }
