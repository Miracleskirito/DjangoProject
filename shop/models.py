from django.db import models
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django_redis import get_redis_connection
import logging

# Create your models here.

logger = logging.getLogger(__name__)


class Product(models.Model):
    DoesNotExist = None
    name = models.CharField(max_length=100)  # 商品名称
    description = models.TextField()  # 商品描述（含关键词）
    stock = models.PositiveIntegerField(default=0)  # 库存
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 价格

    # 缓存键格式
    @property
    def cache_key(self):
        return f"product_{self.id}"

    def save(self, *args, **kwargs):
        # 保存时自动更新缓存
        super().save(*args, **kwargs)
        self.update_cache()

    def update_cache(self):
        """更新Redis缓存"""
        conn = get_redis_connection("default")
        try:
            conn.hmset(self.cache_key, {
                'name': self.name,
                'description': self.description,
                'stock': self.stock,
                'price': str(self.price)
            })
            conn.expire(self.cache_key, 60 * 60)  # 缓存1小时
        except Exception as e:
            logger.error(f"缓存更新失败: {e}")
            # 缓存失败不影响主流程，降级到数据库查询


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间
    status = models.CharField(max_length=20, default='pending')  # 订单状态


class OrderItem(models.Model):
    objects = None
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 下单时价格快照

    def clean(self):
        # 验证库存
        if self.quantity > self.product.stock:
            raise ValidationError(f"商品 {self.product.name} 库存不足")