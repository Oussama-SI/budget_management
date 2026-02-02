# -*- coding: utf-8 -*-
{
    'name': "Mapsly: Smart map for Odoo",

    'summary': "Map. Geo-analysis. Multi-day Routing. Territories. Embeddable maps. Automation.",
    'description': """
        Connects your models and records to Mapsly
    """,
    'author': "Mapsly",
    'website': "https://mapsly.com/",
    'license': "OPL-1",
    'version': '18.0.0.1.0',
    'category': 'Connector',
    'depends': ['base', 'web','somachame_finance'],
    'data': [
        "views/mapsly_frame_view.xml"
    ],
    'images': [
        'static/description/thumbnail.png',
        'static/description/desc_img_02.png',
        'static/description/desc_img_03.png',
        'static/description/desc_img_04.jpeg',
        'static/description/desc_img_05.png',
        'static/description/desc_img_06.jpeg',
        'static/description/desc_img_07.png',
        'static/description/desc_img_08.png',
        'static/description/icon.png'
    ],
    'assets': {
        'web.assets_backend': [
            'mapsly_connector/static/src/js/MapslyFrameView.js',
            'mapsly_connector/static/src/xml/MapslyFrameView.xml',
            'mapsly_connector/static/src/scss/MapslyFrameView.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
