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
        :param order_items_data: [{"product_id": 1, "quantity": 2}, ...]
        :return: (order_object, errors)
        """
        order = Order.objects.create()
        errors = []
        savepoint = transaction.savepoint()  # 初始保存点

        for item_data in order_items_data:
            product_id = item_data['product_id']
            quantity = item_data['quantity']

            try:
                # 获取商品并加锁
                product = Product.objects.select_for_update().get(id=product_id)

                # 创建订单项（自动触发库存验证）
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )

                # 扣减库存
                product.stock -= quantity
                product.save()  # 自动更新缓存

            except (Product.DoesNotExist, ValidationError) as e:
                errors.append(f"商品 {product_id}: {str(e)}")
                transaction.savepoint_rollback(savepoint)  # 回滚当前商品操作
            finally:
                # 为下一个商品创建新保存点
                savepoint = transaction.savepoint()

        if not order.items.exists():
            order.delete()  # 无成功项时删除订单
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