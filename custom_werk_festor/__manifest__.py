# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Custom werk Festor",
    'category': "Hidden",
    'summary': 'Custom werk Festor by Dataforge',
    'version': '18.0',
    'description': """
        Custom werk Festor
    """,
    "license": "LGPL-3",
    'depends': ['sale', 'planning', 'stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/account_move.xml',
        'views/product_template.xml',
        'views/picking_views.xml',
    ],
    'installable': True,
}
