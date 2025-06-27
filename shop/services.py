from django.db import transaction
from django.core.exceptions import ValidationError
from django_redis import get_redis_connection
from .models import Product, Order, OrderItem
import logging

logger = logging.getLogger(__name__)


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_bulk_order(order_items_data):
        """
        批量创建订单
        """
        order = Order.objects.create()
        errors = []
        success_items = []

        for item_data in order_items_data:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity')
            print(product_id,quantity)

            # 验证数据格式
            if not product_id or not isinstance(quantity, int) or quantity <= 0:
                errors.append(f"无效商品数据: {item_data}")
                continue

            try:
                # 获取商品并加锁（使用行级锁）
                product = Product.objects.select_for_update().get(id=product_id)

                # 检查库存（避免超卖）
                if product.stock < quantity:
                    raise ValidationError(f"库存不足，当前库存: {product.stock}")

                # 创建订单项
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )

                # 扣减库存
                product.stock -= quantity
                product.save()

                success_items.append(product_id)

            except Product.DoesNotExist:
                errors.append(f"商品不存在: ID={product_id}")
            except ValidationError as e:
                errors.append(f"商品 {product_id}: {str(e)}")
            except Exception as e:
                errors.append(f"处理商品 {product_id} 时发生未知错误: {str(e)}")

        # 若没有成功的订单项，删除订单
        if not success_items:
            order.delete()
            return None, errors

        return order, errors


class SearchService:
    @staticmethod
    def search_products(query):
        """商品搜索（带缓存）"""
        cache_key = f"search_{query}"
        conn = get_redis_connection("default")

        # 尝试从缓存获取
        try:
            if conn.exists(cache_key):
                return conn.smembers(cache_key)
        except Exception as e:
            logger.error(f"缓存查询失败: {e}")

        # 缓存失效时查询数据库
        results = Product.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        ).values_list('id', flat=True)

        # 回填缓存（异步执行）
        try:
            if results:
                conn.sadd(cache_key, *results)
                conn.expire(cache_key, 60 * 5)  # 缓存5分钟
        except Exception as e:
            logger.error(f"缓存回填失败: {e}")

        return results