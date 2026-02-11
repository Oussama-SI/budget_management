{
    'name': "Indicateurs KPIs",

    'summary': """
        Somachame Gestion de Budget""",

    'description': """
        suivie l'avancement financie du ^projet sous Axes Analytiques
    """,

    'author': "YelTech",
    'website': "http://www.yeltech.ma",
    'category': 'Uncategorized',
    'depends': ['account', 'projet_stock_depot', 'mrp', 'hr', 'btp_customisation'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/project_fiancial_create_view.xml',
        'views/project_financial_axis_line.xml',
        'views/project_financial_axis.xml',
        'views/project_financial_progress.xml',
        'views/project_financial_axis_budget_line.xml',
        'views/res_config_settings_views.xml',
        'views/ddff.xml',
    ],
    'application': True,
    'auto_install': False,
    'licence': 'OEEL-1'
}
