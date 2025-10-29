# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Custom Invoice Report",
    'category': "Hidden",
    'summary': 'Customisation of invoice report',
    'version': '18.0',
    'description': """
        Customisation of invoice report
    """,
    "license": "LGPL-3",

    'depends': ['account', 'web', 'sale', 'stock'],
    'data': [
        #'report/header_and_footer_for_reports.xml',
        ],
    'installable': True,
}
