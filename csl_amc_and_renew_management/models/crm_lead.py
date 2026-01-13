# crm_lead.py
from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import UserError

class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    amc_id = fields.Many2one('amc.model', string='AMC Contract')

    def action_new_quotation(self):
        self.ensure_one()
        if not self.amc_id or not self.amc_id.amc_line_ids:
            return super().action_new_quotation()

        SaleOrder = self.env['sale.order']
        order_vals = {
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
            'origin': self.amc_id.name or '',
            'amc_id': self.amc_id.id,  # link AMC here
            'fiscal_position_id': self.partner_id.property_account_position_id.id or False,
            'order_line': [],
        }
        for line in self.amc_id.amc_line_ids:
            if getattr(line, 'display_type', False):
                order_vals['order_line'].append((0, 0, {
                    'display_type': line.display_type,
                    'name': line.name or '',
                }))  # section/note supported via display_type
                continue
            if not line.product_id:
                continue
            amc_tax_ids = [line.tax_id.id] if line.tax_id else []
            order_vals['order_line'].append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.display_name,
                'product_uom_qty': line.quantity or 1.0,
                'price_unit': line.price or 0.0,
                'tax_id': [(6, 0, amc_tax_ids)],  # exact AMC tax or none
            }))
        order = SaleOrder.with_context(from_amc=True).create(order_vals)
        return {
            'type': 'ir.actions.act_window', 'name': _('Quotation'),
            'res_model': 'sale.order', 'view_mode': 'form', 'res_id': order.id,
        }
    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        odoobot = self.env.ref('base.partner_root')  # OdooBot partner [7]
        ctx_amc_id = self.env.context.get('default_amc_id')
        for lead, vals in zip(leads, vals_list):
            amc = lead.amc_id or (ctx_amc_id and self.env['amc.model'].browse(ctx_amc_id))
            if amc:
                if not lead.amc_id:
                    lead.amc_id = amc.id
                body = _("CRM Lead %s was created.", lead._get_html_link(title=lead.name))
                amc.message_post(
                    body=Markup(body),
                    author_id=odoobot.id,                # post as OdooBot
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )  # standard chatter API [2][1]
        return leads

