# wizard/amc_link_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AmcLinkWizard(models.TransientModel):
    _name = 'amc.link.wizard'
    _description = 'Link AMC to Quotation'

    sale_order_id = fields.Many2one('sale.order', string='Quotation', required=True, readonly=True)
    amc_id = fields.Many2one('amc.model', string='AMC', required=True)

    def action_link(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("No quotation to link."))

        self.sale_order_id.write({'amc_id': self.amc_id.id})

        self.sale_order_id.message_post(
            body=_("Linked to AMC %(amc)s by %(user)s", amc=self.amc_id.display_name, user=self.env.user.display_name)
        )
        self.amc_id.message_post(
            body=_("Linked to quotation %(so)s", so=self.sale_order_id.name)
        )  
        return {'type': 'ir.actions.client', 'tag': 'reload'}  
