# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
{
    "name": "Product Variant Extra Price ",
    "category": 'Uncategorized',
    "summary": """
        This module allows you to manually apply additional extra prices for Product's variants.""",
    "description": """

====================
**Help and Support**
====================
.. |icon_features| image:: variant_price_extra/static/src/img/icon-features.png
.. |icon_support| image:: variant_price_extra/static/src/img/icon-support.png
.. |icon_help| image:: variant_price_extra/static/src/img/icon-help.png

|icon_help| `Help <https://webkul.com/ticket/open.php>`_ |icon_support| `Support <https://webkul.com/ticket/open.php>`_ |icon_features| `Request new Feature(s) <https://webkul.com/ticket/open.php>`_
    """,
    "sequence": 1,
    "author": "Webkul Software Pvt. Ltd.",
    "website": "http://www.webkul.com",
    "version": '1.1',
    "depends": ['product'],
    "data": ['views.xml'],
    'demo': [ ],
    'images':['static/description/Banner.png'],
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 20,
    "currency": 'EUR',
}