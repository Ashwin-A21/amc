from odoo import api,models, fields
from markupsafe import Markup
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    amc_id = fields.Many2one('amc.model', string="AMC Reference")

    amc_renewal_updated = fields.Boolean(
        string="AMC Renewal Updated",
        copy=False,
        help="Indicates if the AMC renewal date has been updated using this invoice."
    )

    def button_draft(self):
        """
        Overrides the standard button_draft method to add a log note on AMC.
        """
        # Call the super method first to revert the invoice to draft
        result = super().button_draft()

        for invoice in self:
            if invoice.move_type != 'out_invoice':
                continue

            sale_order = self.env['sale.order'].search([
                ('name', '=', invoice.invoice_origin),
                ('amc_id', '!=', False)
            ], limit=1)

            if sale_order and sale_order.amc_id:
                amc = sale_order.amc_id

                # Add a log note to the AMC record
                amc.message_post(
                    body=Markup(f"""
                        <div class="o_notification card border-warning shadow-sm mb-2">
                            <div class="card-header bg-warning text-dark py-2">
                                <strong><i class="fa fa-undo me-2"></i>Invoice Reset to Draft</strong>
                            </div>
                            <div class="card-body">
                                <p>
                                    Invoice <b>{invoice.name}</b> was reset to draft.
                                    This may affect the AMC renewal status if it was previously updated by this invoice.
                                </p>
                            </div>
                        </div>
                    """),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
                _logger.info(f"AMC {amc.name} log note added: Invoice {invoice.name} reset to draft.")
        return result

    def action_post(self, *args, **kwargs):
        result = super().action_post(*args, **kwargs)

        for invoice in self:
            if invoice.move_type != 'out_invoice':
                continue

            sale_order = self.env['sale.order'].search([
                ('name', '=', invoice.invoice_origin),
                ('amc_id', '!=', False)
            ], limit=1)

            if sale_order and sale_order.amc_id:
                amc = sale_order.amc_id

                # if amc.renew_type == 'yearly':
                #     new_due = amc.due_on + relativedelta(years=1)
                # elif amc.renew_type == 'monthly':
                #     new_due = amc.due_on + relativedelta(months=1)
                # elif amc.renew_type == 'weekly':
                #     new_due = amc.due_on + relativedelta(weeks=1)
                # elif amc.renew_type == 'daily':
                #     new_due = amc.due_on + relativedelta(days=1)
                # else:
                #     new_due = amc.due_on


                invoice_card = Markup("""
                    <div class="o_notification card border-success shadow-sm mb-2">
                        <div class="card-header bg-success text-white d-flex justify-content-between align-items-center py-2">
                            <span class="d-flex align-items-center">
                                <i class="fa fa-check-circle me-2"></i>
                                <strong>Invoice Posted</strong>
                            </span>
                            <span class="badge bg-light text-dark">Done</span>
                        </div>
                        <div class="card-body p-3">
                            <div class="d-flex align-items-center mb-2">
                                <i class="fa fa-file text-muted me-2"></i>
                                <div>
                                    <span class="text-muted small">Invoice:</span>
                                    <span class="ms-2 fw-bold text-success">%(invoice_name)s</span>
                                </div>
                            </div>
                            <div class="d-flex align-items-center mb-2">
                                <i class="fa fa-handshake text-muted me-2"></i>
                                <div>
                                    <span class="text-muted small">Sales Order:</span>
                                    <span class="ms-2 fw-bold">%(so_name)s</span>
                                </div>
                            </div>
                            <div class="d-flex align-items-center">
                                <i class="fa fa-calendar-check text-muted me-2"></i>
                                <div>
                                    <span class="text-muted small">Posted On:</span>
                                    <span class="ms-2">%(posted_date)s</span>
                                </div>
                            </div>
                        </div>
                        <div class="card-footer bg-light text-muted py-2 text-end">
                            <small><i class="fa fa-clock me-1"></i>Invoice Validation Complete</small>
                        </div>
                    </div>
                """) % {
                    'invoice_name': invoice.name,
                    'so_name': sale_order.name,
                    'posted_date': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                amc.message_post(
                    body=invoice_card,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
                # if amc.due_on:
                #     new_due = amc.due_on + relativedelta(years=1)
                # else:
                #     new_due = fields.Date.today() + relativedelta(years=1)

                # amc.write({
                #     'due_on': new_due,
                #     'status': 'pending',
                #     'is_notified': False,
                # })
                # amc.message_post(
                #     body=Markup(f" AMC auto-renewed for next year due to invoice <b>{invoice.name}</b>. "
                #     f"New due date: <b>{new_due.strftime('%Y-%m-%d')}</b>."),
                #     message_type='comment',
                #     subtype_xmlid='mail.mt_note'
                # )
        return result
    
    def button_renew_amc(self):
        self.ensure_one()

        if self.state != 'posted':
            raise ValidationError("You can only update AMC renewal from a posted invoice.")

        # Prevent multiple updates from the same invoice
        if self.amc_renewal_updated:
            raise ValidationError("AMC renewal has already been updated using this invoice.")

        sale_order = self.env['sale.order'].search([
            ('name', '=', self.invoice_origin),
            ('amc_id', '!=', False)
        ], limit=1)

        if not sale_order or not sale_order.amc_id:
            raise ValidationError("No AMC record linked with this invoice's sale order.")

        amc = sale_order.amc_id

        if not amc.due_on:
            raise ValidationError("AMC does not have a due date.")

        old_due = amc.due_on

        # Calculate new due date
        if amc.renew_type == 'yearly':
            new_due = amc.due_on + relativedelta(years=1)
        elif amc.renew_type == 'monthly':
            new_due = amc.due_on + relativedelta(months=1)
        elif amc.renew_type == 'weekly':
            new_due = amc.due_on + relativedelta(weeks=1)
        elif amc.renew_type == 'daily':
            new_due = amc.due_on + relativedelta(days=1)
        else:
            raise ValidationError("AMC does not have a valid renewal type.")

        amc.write({
            'due_on': new_due,
            'status': 'pending', # Reset status to pending
            'is_notified': False, # Reset notification flag
        })

        # Mark this invoice as having updated the AMC renewal
        self.write({'amc_renewal_updated': True})

        # amc.message_post(
        #     body=Markup(
        #         f"Invoice: <b>{self.name}</b><br/>"
        #         f"New Due Date: <b>{new_due.strftime('%Y-%m-%d')}</b>"
        #     ),
        #     message_type='comment',
        #     subtype_xmlid='mail.mt_note'
        # )

        self.message_post(
            body=Markup(f"""
                <div class="o_notification card border-success shadow-sm mb-2">
                    <div class="card-header bg-success text-white py-2">
                        <strong><i class="fa fa-sync-alt me-2"></i>AMC Renewal Updated</strong>
                    </div>
                    <div class="card-body">
                        <p>
                            <b>{amc.title}</b> due date updated from
                            <b>{old_due.strftime('%Y-%m-%d')}</b> to
                            <b>{new_due.strftime('%Y-%m-%d')}</b>.
                        </p>
                    </div>
                </div>
            """),
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

        return True


    def action_open_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': self.env.context,
        }

    # Method to open the associated AMC record from an invoice (kept for potential future use or if a direct link exists)
    def action_open_amc_from_invoice(self):
        self.ensure_one()
        # Find the AMC record that has this invoice's partner as its customer
        amc_record = self.env['amc.model'].search([('customer', '=', self.partner_id.id)], limit=1)
        if amc_record:
            return {
                'type': 'ir.actions.act_window',
                'name': 'AMC Contract',
                'res_model': 'amc.model',
                'view_mode': 'form',
                'res_id': amc_record.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No AMC Linked',
                    'message': 'This invoice is not directly linked to any AMC record.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
