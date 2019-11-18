# -*- coding: utf-8 -*-
{
    'name': "Easy Water: Delivery Customization",

    'summary': """
        Easy Water ships products primarily via UPS parcel service.
A given product will almost always be shipped in one of its default packages.""",

    'description': """
Task: 2007397
===============================================================
        1. Product and Operation Type Configuration
1.1. Product Configuration
On the product form view, at the bottom of the the Inventory notebook page provide an in-form list where any number of default package types may be defined.

A default package has a product, quantity of product, weight (lbs), length, width, height (all ideally in inches). These fields should be displayed on the in-form list in the order listed here.

1.2. Operation Type Configuration
On the Operation Type form view, add a new checkbox, "Automated Packaging".

2. Automatic creation of packages on delivery orders
2.1. Operation type check
When reserving products against a transfer, apply item 2.2 below only if the transfer's operation type has "Automated Packaging" enabled.

2.2. Automated Packaging
For each line on the delivery order, if the product has one or more default packages defined, divide the unpackaged product into the smallest possible number of default packages. Use product quantity only when deciding how to assign packages. The packages created in this way should have their weight and dimensions populated from the information configured on the product's default packaging. 
Note:
This will result in the creation of stock move lines and stock quant packages. At this time we are waiting on confirmatino from the customer as to whether partially empty boxes should be allowed.

Do not change any existing packages already defined on the delivery order.
Note:
Packages will be able to be recomputed according to defaults by unreserving and then re-reserving against the order.

If the product does not have any default packages defined, leave the line with no packages defined.

The user should be able to manually edit the packages after their automatic creation.
    """,

    'author': "Odoo PS-US",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock', 'delivery'],

    # always loaded
    'data': [
        'views/stock_views.xml',
        'views/product_views.xml',
    ],
}
