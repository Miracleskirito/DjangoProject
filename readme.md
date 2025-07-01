# 电商核心模块系统（Django + Redis + MySQL）

这是一个基于 Django 构建的电商核心模块，实现了 **批量订单处理** 和 **商品搜索** 两大核心功能，支持高并发场景下的稳定运行。


功能概述

批量订单处理：支持一次提交多个商品订单，自动扣减库存，处理部分失败场景
商品搜索：支持按关键词搜索商品，内置Redis缓存优化查询性能
高并发支持：使用悲观锁防止超卖，缓存降级机制保证系统稳定性
数据一致性：确保数据库与缓存的数据同步

系统依赖

Python(Pycharm)
Django
Django REST Framework
Redis
MySQL

工具：

以下是使用方法：

首先先将代码部署在本地：
终端：git clone https://github.com/Miracleskirito/DjangoProject.git
     cd DjangoProject

打开编译软件和终端
要打开redis-server
现在settings中配置数据库连接文件

终端运行以下指令
#通过models创建迁移脚本
python manage.py makemigrations
#执行同步创建表
python manage.py migrate

然后再shop_product表中随便写几行，
descripstion是关键字，
搜索功能会检索description和name
stock是库存
剩下两个表：（都是自动写入，记录购买信息的）
shop_orderitem:储存订单明细
shop_order:储存订单

接下来是两个接口：
1.可以直接运行后，在浏览器访问127.0.0.1/shop/来访问页面


2.postman访问接口：
商品搜索接口：
http://127.0.0.1:8000/shop/products/search/?q=关键字
关键字处换成想搜索的字，GET请求
回复应类似：
{
    "results": [
        "智能手机",
        "智能电脑"
    ]
}

商品购买接口：
http://127.0.0.1:8000/shop/products/
POST请求，附带上如下的请求信息
{
    "items": [
        {
            "product_id": 1,  
            "quantity": 500  
        },
        {
            "product_id": 3,
            "quantity": 500
        }
    ]
}
product_id是商品id
quantity是购买数量

回复应类似：
{
    "order_id": null,
    "success_items": 0,
    "errors": [
        "商品 1: ['库存不足，当前库存: 82']",
        "商品 3: ['库存不足，当前库存: 191']"
    ]
}

