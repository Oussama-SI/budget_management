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
    'depends': ['account', 'project', 'mrp', 'hr'],

    'data': [
        'security/ir.model.access.csv',
        # 'security/account_budget_security.xml',
        'views/account_analytic_views.xml',
        'views/project_financial_axis_line.xml',
        'views/project_financial_axis.xml',
        'views/project_financial_progress.xml',
        'views/res_config_settings_views.xml',
    ],
    'application': True,
    'auto_install': False,
    'licence': 'OEEL-1'
}
