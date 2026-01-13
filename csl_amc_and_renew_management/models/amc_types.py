from odoo import models, fields

class RenewsCategoriesModel(models.Model):
    _name = 'amc.types.model'
    _description = 'AMC Types'
 
    name = fields.Char(string='Type name', required=True)  
    category = fields.Selection([
        ('hardware_product', 'Hardware Products'),
        ('software_product', 'Software Product'),
        ('web_services', 'Web Services'),
    ], string='Category', required=True, tracking=True)



class CustomerTypeModel(models.Model):
    _name = 'renew.customertype.model'
    _description = 'Renew category Model'

    name = fields.Char(string='Category name', required=True)
   
