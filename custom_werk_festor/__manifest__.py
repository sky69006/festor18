# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Custom werk Festor",
    'category': "Hidden",
    'summary': 'Custom werk Festor by Dataforge',
    'version': '18.0.5.0.0',
    'description': """
        Custom werk Festor
    """,
    "license": "LGPL-3",
    'depends': ['account', 'sale', 'sale_renting', 'planning', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/rental_availability_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/account_move.xml',
        'views/product_template.xml',
        'views/picking_views.xml',
        'report/report_saleorder_custom.xml',
        'views/account_analytic_line_views.xml',
        'views/account_journal_dashboard.xml',
    ],
    'installable': True,
}
