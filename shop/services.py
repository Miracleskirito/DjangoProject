from django.db import transaction
from django.core.exceptions import ValidationError
from django_redis import get_redis_connection
from .models import Product, Order, OrderItem
from django.db import models
import logging

logger = logging.getLogger(__name__)


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_bulk_order(order_items_data):
        print("[DEBUG] 开始批量创建订单")
        order = Order.objects.create()
        print(f"[DEBUG] 创建订单，ID: {order.id}")
        errors = []
        success_items = []

        for idx, item_data in enumerate(order_items_data):
            #print(f"\n[DEBUG] 处理第 {idx+1}/{len(order_items_data)} 个商品: {item_data}")
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity')
            #print(f"[DEBUG] 提取参数: product_id={product_id}, quantity={quantity}")

            # 验证数据格式
            if not product_id or not isinstance(quantity, int) or quantity <= 0:
                errors.append(f"无效商品数据: {item_data}")
                #print(f"[ERROR] 数据验证失败: {item_data}")
                continue

            try:
                #print(f"[DEBUG] 尝试获取商品 (ID={product_id}) 并加锁")
                # 获取商品并加锁（使用行级锁）
                product = Product.objects.select_for_update().get(id=product_id)
                #print(f"[DEBUG] 成功获取商品: {product.name} (库存: {product.stock})")

                # 检查库存（避免超卖）
                #print(f"[DEBUG] 检查库存: 需要 {quantity}，现有 {product.stock}")
                if product.stock < quantity:
                    raise ValidationError(f"库存不足，当前库存: {product.stock}")
                #print("[DEBUG] 库存检查通过")

                # 创建订单项
                #print(f"[DEBUG] 创建订单项: order={order.id}, product={product_id}, quantity={quantity}")
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
                #print("[DEBUG] 订单项创建成功")

                # 扣减库存
                #print(f"[DEBUG] 扣减库存: {product.stock} - {quantity} = {product.stock - quantity}")
                product.stock -= quantity
                product.save()
                #print("[DEBUG] 库存扣减成功")

                success_items.append(product_id)
                #print(f"[SUCCESS] 商品 {product_id} 处理完成")

            except Product.DoesNotExist:
                errors.append(f"商品不存在: ID={product_id}")
                #print(f"[ERROR] 商品不存在: ID={product_id}")
            except ValidationError as e:
                errors.append(f"商品 {product_id}: {str(e)}")
                #print(f"[ERROR] 验证错误: {str(e)}")
            except Exception as e:
                errors.append(f"处理商品 {product_id} 时发生未知错误: {str(e)}")
                #print(f"[ERROR] 未知错误: {str(e)}")
                import sys, traceback
                #print(f"[ERROR] 堆栈信息: {''.join(traceback.format_exception(*sys.exc_info()))}")

        # 若没有成功的订单项，删除订单
        #print(f"\n[DEBUG] 处理完成 - 成功项: {len(success_items)}, 错误项: {len(errors)}")
        if not success_items:
            #print(f"[DEBUG] 删除空订单: {order.id}")
            order.delete()
            #print("[DEBUG] 订单已删除")
            return None, errors

        #print(f"[SUCCESS] 订单创建成功: {order.id}")
        return order, errors

class SearchService:
    @staticmethod
    def search_products(query):
        """商品搜索（带缓存）"""
        cache_key = f"search_{query}"
        conn = get_redis_connection("default")
        #print(f"[DEBUG] 搜索关键词: {query}")
        #print(f"[DEBUG] 缓存键: {cache_key}")

        # 尝试从缓存获取
        try:
            #print("[DEBUG] 尝试从缓存获取结果...")
            if conn.exists(cache_key):
                #print("[DEBUG] 缓存命中")
                cache_result = conn.smembers(cache_key)
                #print(f"[DEBUG] 缓存结果: {cache_result}")
                return cache_result
            else:
                print("[DEBUG] 缓存未命中")
        except Exception as e:
            #print(f"[ERROR] 缓存查询失败: {e}")
            import traceback
            #print(f"[ERROR] 堆栈信息: {traceback.format_exc()}")

        # 缓存失效时查询数据库
        #print("[DEBUG] 开始查询数据库...")
        results = Product.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        ).values_list('id', flat=True)
        #print(f"[DEBUG] 数据库查询结果: {list(results)}")

        # 回填缓存（异步执行）
        try:
            if results:
                #print(f"[DEBUG] 开始回填缓存，结果数量: {len(results)}")
                conn.sadd(cache_key, *results)
                conn.expire(cache_key, 60 * 5)  # 缓存5分钟
                #print("[DEBUG] 缓存回填成功")
            else:
                #print("[DEBUG] 结果为空，不进行缓存")
        except Exception as e:
            #print(f"[ERROR] 缓存回填失败: {e}")
            import traceback
            #print(f"[ERROR] 堆栈信息: {traceback.format_exc()}")

        #print(f"[DEBUG] 返回结果: {list(results)}")
        return results