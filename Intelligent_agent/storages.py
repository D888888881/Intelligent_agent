"""腾讯云 COS（S3 兼容 API）媒体文件存储。"""

from storages.backends.s3boto3 import S3Boto3Storage


class TencentCOSMediaStorage(S3Boto3Storage):
    """uploads / 生图 / 局部修复等 ImageField 默认写入 COS。"""

    default_acl = None
    file_overwrite = False

    def get_object_parameters(self, name):
        params = super().get_object_parameters(name)
        params.setdefault(
            "CacheControl",
            "private, max-age=604800, stale-while-revalidate=86400",
        )
        return params