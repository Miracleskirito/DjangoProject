from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import services


@api_view(['POST'])
def bulk_order(request):
    try:
        order_data = request.data['items']
        if not isinstance(order_data, list):
            return Response({"error": "无效的订单格式"}, status=400)

        order, errors = services.OrderService.create_bulk_order(order_data)

        response = {
            "order_id": order.id if order else None,
            "success_items": order.items.count() if order else 0,
            "errors": errors
        }
        return Response(response)

    except KeyError:
        return Response({"error": "缺少订单数据"}, status=400)


@api_view(['GET'])
def product_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return Response({"error": "搜索词不能为空"}, status=400)

    product_ids = services.SearchService.search_products(query)
    return Response({"results": list(product_ids)})