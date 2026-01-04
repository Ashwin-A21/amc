{
    'name': 'AMC & Renewal Management',
    'version': '1.0.0',
    'category': 'AMC & Renewal Management',
    'summary': 'Manage Annual Maintenance Contracts (AMC) and Renewals',
    'author': 'Concept Solutions LLC',
    'company': 'Concept Solutions LLC',
    'description': """
        AMC Management module helps you:
        - Manage AMCs
        - Auto generate quotations
        - Integrate with CRM and Sales
        """,
    'maintainer': 'Concept Solutions LLC',
    'website': 'https://www.csloman.com',
    'depends': ['base','project','mail','crm','sale_management','stock','account','sale_crm','account','sale'],
    'data': [
            'views/amc_dashboard.xml',
            'views/sale_views.xml',
            'views/crm_views.xml',
            'wizard/amc_link_wizard.xml',
            'views/menus.xml',
            'views/account_move_view.xml',
            'security/ir.model.access.csv',
            'data/ir_cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'concept_amc_and_renew_management/static/src/css/amc_hide_label.css',
        ],
    },
    'assets': {},
    'installable': True, 
    'auto_install': False,
}