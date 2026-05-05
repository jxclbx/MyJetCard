import os
from django.core.management.base import BaseCommand
from photos.models import Photo, PendingPhoto

class Command(BaseCommand):
    help = '彻底删除 Photo 或 PendingPhoto 及其关联的图片文件'

    def add_arguments(self, parser):
        parser.add_argument('model_type', type=str, choices=['photo', 'pending'], help='数据类型：photo 或是 pending')
        parser.add_argument('entry_ids', type=int, nargs='+', help='数据库中的 ID (支持多个，空格分隔)')

    def _delete_file(self, file_field):
        """如果 ImageField 存在，则在磁盘上删除对应的物理文件"""
        if file_field and hasattr(file_field, 'name') and file_field.name:
            try:
                path = file_field.path
                if os.path.isfile(path):
                    os.remove(path)
                    self.stdout.write(self.style.SUCCESS(f"  [-] 成功删除物理文件: {path}"))
                else:
                    self.stdout.write(self.style.WARNING(f"  [!] 磁盘上未找到该文件，跳过: {path}"))
            except ValueError:
                self.stdout.write(self.style.WARNING(f"  [!] 读取路径时出错 (可能字段为空)。跳过。"))
            except OSError as e:
                self.stderr.write(self.style.ERROR(f"  [X] 删除文件失败 {file_field.path}: {e}"))

    def handle(self, *args, **options):
        model_type = options['model_type']
        entry_ids = options['entry_ids']

        for entry_id in entry_ids:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n>>> 正在处理 {model_type.upper()} ID: {entry_id}"))
            
            # 1. 处理 PHOTO
            if model_type == 'photo':
                try:
                    obj = Photo.objects.get(id=entry_id)
                    self.stdout.write(f"[*] 找到 Photo #{entry_id} (注册号: {obj.reg}, 机型: {obj.model}).")
                    
                    self.stdout.write("[*] 正在从硬盘上删除关联图片文件...")
                    self._delete_file(obj.image)
                    self._delete_file(obj.image_sm)
                    self._delete_file(obj.image_lg)
                    
                    self.stdout.write("[*] 正在删除数据库条目...")
                    obj.delete()
                    
                    self.stdout.write(self.style.SUCCESS(f"[V] 成功！Photo #{entry_id} 及其所有图片文件已被彻底废除。"))
                except Photo.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"[X] Photo (ID: {entry_id}) 不存在。"))

            # 2. 处理 PENDING PHOTO
            elif model_type == 'pending':
                try:
                    obj = PendingPhoto.objects.get(id=entry_id)
                    self.stdout.write(f"[*] 找到 PendingPhoto #{entry_id} (状态: {obj.status}, 注册号: {obj.reg}).")
                    
                    self.stdout.write("[*] 正在从硬盘上删除关联图片文件...")
                    self._delete_file(obj.image)
                    self._delete_file(obj.image_sm)
                    
                    self.stdout.write("[*] 正在删除数据库条目...")
                    obj.delete()
                    
                    self.stdout.write(self.style.SUCCESS(f"[V] 成功！PendingPhoto #{entry_id} 及其所有图片文件已被彻底删除。"))
                except PendingPhoto.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"[X] PendingPhoto (ID: {entry_id}) 不存在。"))
