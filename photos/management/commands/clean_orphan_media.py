"""
Management command: clean_orphan_media
用途：扫描 media 目录下被 Photo、PendingPhoto、SiteProfile 所管理的子目录，
      删除不再被任何数据库记录引用的孤立文件。

使用方法：
  # 仅预览，不实际删除（默认 dry-run）
  python manage.py clean_orphan_media

  # 实际删除
  python manage.py clean_orphan_media --delete
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings

from photos.models import Photo, PendingPhoto, SiteProfile


# 只扫描这些子目录（相对于 MEDIA_ROOT）
MANAGED_DIRS = ["photos", "pending", "site"]


class Command(BaseCommand):
    help = "扫描并清理 media 目录中未被数据库引用的孤立文件"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            default=False,
            help="实际执行删除（默认为 dry-run，只列出孤立文件不删除）",
        )

    def handle(self, *args, **options):
        do_delete = options["delete"]
        media_root = settings.MEDIA_ROOT

        # ── 1. 收集数据库中所有被引用的文件路径（相对路径） ──────────────────
        referenced = set()

        # Photo: image, image_sm, image_lg
        for field in ("image", "image_sm", "image_lg"):
            for val in Photo.objects.exclude(**{f"{field}": ""}).exclude(
                **{f"{field}": None}
            ).values_list(field, flat=True):
                if val:
                    referenced.add(os.path.normpath(val))

        # PendingPhoto: image, image_sm
        for field in ("image", "image_sm"):
            for val in PendingPhoto.objects.exclude(**{f"{field}": ""}).exclude(
                **{f"{field}": None}
            ).values_list(field, flat=True):
                if val:
                    referenced.add(os.path.normpath(val))

        # SiteProfile: avatar, banner
        for field in ("avatar", "banner"):
            for val in SiteProfile.objects.exclude(**{f"{field}": ""}).exclude(
                **{f"{field}": None}
            ).values_list(field, flat=True):
                if val:
                    referenced.add(os.path.normpath(val))

        self.stdout.write(
            self.style.SUCCESS(f"✅ 数据库共引用了 {len(referenced)} 个文件")
        )

        # ── 2. 遍历 media 目录下的受管子目录，找出孤立文件 ──────────────────
        orphans = []
        total_files = 0

        for managed_dir in MANAGED_DIRS:
            scan_path = os.path.join(media_root, managed_dir)
            if not os.path.isdir(scan_path):
                continue

            for dirpath, dirnames, filenames in os.walk(scan_path):
                for filename in filenames:
                    abs_path = os.path.join(dirpath, filename)
                    # 计算相对于 MEDIA_ROOT 的路径（Django ImageField 存的就是这个）
                    rel_path = os.path.normpath(
                        os.path.relpath(abs_path, media_root)
                    )
                    total_files += 1
                    if rel_path not in referenced:
                        orphans.append((abs_path, rel_path))

        self.stdout.write(f"📂 扫描了 {total_files} 个文件，发现 {len(orphans)} 个孤立文件")

        if not orphans:
            self.stdout.write(self.style.SUCCESS("🎉 没有孤立文件，media 目录很干净！"))
            return

        # ── 3. 输出孤立文件列表 ──────────────────────────────────────────────
        self.stdout.write("\n── 孤立文件列表 ──")
        total_size = 0
        for abs_path, rel_path in orphans:
            size = os.path.getsize(abs_path)
            total_size += size
            action = "🗑  [会删除]" if do_delete else "👁  [dry-run]"
            self.stdout.write(f"  {action}  {rel_path}  ({size // 1024} KB)")

        self.stdout.write(
            f"\n合计孤立文件大小：{total_size // 1024} KB  ({total_size / 1024 / 1024:.2f} MB)"
        )

        # ── 4. 执行删除 ──────────────────────────────────────────────────────
        if do_delete:
            deleted = 0
            errors = 0
            for abs_path, rel_path in orphans:
                try:
                    os.remove(abs_path)
                    deleted += 1
                except OSError as e:
                    self.stderr.write(f"  ❌ 删除失败：{rel_path}  原因：{e}")
                    errors += 1

            # 清理空目录（从深到浅）
            for managed_dir in MANAGED_DIRS:
                scan_path = os.path.join(media_root, managed_dir)
                for dirpath, dirnames, filenames in os.walk(scan_path, topdown=False):
                    if dirpath == scan_path:
                        continue  # 不删受管子目录本身
                    if not os.listdir(dirpath):
                        try:
                            os.rmdir(dirpath)
                            self.stdout.write(f"  📁 清理空目录：{dirpath}")
                        except OSError:
                            pass

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ 已删除 {deleted} 个孤立文件" +
                    (f"，{errors} 个失败" if errors else "")
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  这是 dry-run 预览，未执行任何删除。"
                    "如需实际删除，请加上 --delete 参数。"
                )
            )
