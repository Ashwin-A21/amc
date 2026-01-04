from odoo import models, fields,api, _
from markupsafe import Markup

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amc_id = fields.Many2one('amc.model', string="Source AMC", copy=False, readonly=True,)
    is_cancel_note_posted = fields.Boolean(string="AMC Cancel Note Posted", default=False)

    @api.depends('product_id', 'company_id', 'order_partner_id', 'order_id.fiscal_position_id')
    def _compute_tax_id(self):
        if self.env.context.get('from_amc'):
            return  # keep AMC-provided tax_id
        super()._compute_tax_id()

    def action_open_sale_order(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': self.env.context,
        }
    def action_open_amc(self):
        self.ensure_one()
        if self.amc_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'AMC Contract',
                'res_model': 'amc.model',
                'view_mode': 'form',
                'res_id': self.amc_id.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No AMC Linked',
                    'message': 'This sale order is not linked to any AMC.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if not order.amc_id:
                continue
                
            # Sale Order notification with fixed percentage symbols
            so_notification = Markup("""
                <div class="o_notification card border-success shadow-sm mb-2">
                    <div class="card-header bg-success text-white d-flex justify-content-between align-items-center py-2">
                        <span class="d-flex align-items-center">
                            <i class="fa fa-check-circle me-2"></i>
                            <strong>AMC Order Confirmed</strong>
                        </span>
                        <span class="badge bg-light text-dark">Success</span>
                    </div>
                    <div class="card-body p-3">
                        <div class="d-flex align-items-center mb-2">
                            <i class="fa fa-link text-muted me-2"></i>
                            <div>
                                <span class="text-muted small">AMC Contract:</span>
                                <span class="ms-2 fw-bold">%(amc_title)s</span>
                            </div>
                        </div>
                        <div class="d-flex align-items-center">
                            <i class="fa fa-calendar-check text-muted me-2"></i>
                            <div>
                                <span class="text-muted small">Confirmed On:</span>
                                <span class="ms-2">%(current_time)s</span>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer bg-light d-flex justify-content-end py-2">
                        <small class="text-muted">Sales Order Confirmation</small>
                    </div>
                </div>
            """) % {
                'amc_title': order.amc_id.title,
                'current_time': fields.Datetime.now()
            }

            # AMC notification with fixed percentage symbols
            amc_notification = Markup("""
                <div class="o_notification card border-success shadow-sm mb-2">
                    <div class="card-header bg-success text-white d-flex justify-content-between align-items-center py-2">
                        <span class="d-flex align-items-center">
                            <i class="fa fa-check-circle me-2"></i>
                            <strong>Quotation Confirmed</strong>
                        </span>
                        <div class="d-flex align-items-center">
                            <span class="badge bg-light text-dark">Complete</span>
                        </div>
                    </div>
                    <div class="card-body p-3">
                        <div class="d-flex align-items-center mb-2">
                            <i class="fa fa-file-alt text-muted me-2"></i>
                        </div>
                        <div class="d-flex align-items-center mb-2">
                            <i class="fa fa-file-signature text-muted me-2"></i>
                            <div>
                                <span class="text-muted small">Sales Order:</span>
                                <span class="ms-2 fw-bold text-success">%(order_name)s</span>
                            </div>
                        </div>
                        <div class="d-flex align-items-center">
                            <i class="fa fa-sync-alt text-muted me-2"></i>
                            <div>
                                <span class="text-muted small">Status Change:</span>
                                <span class="ms-2 badge bg-success">Quotation → Sales Order</span>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer bg-light d-flex justify-content-between align-items-center py-2">
                        <small class="text-muted">AMC Contract Update</small>
                        <small class="text-muted">
                            <i class="fa fa-clock me-1"></i>%(current_time)s
                        </small>
                    </div>
                </div>
            """) % {
                'order_name': order.name,
                'current_time': fields.Datetime.now()
            }

            # Post notifications
            order.message_post(body=so_notification)
            order.amc_id.message_post(body=amc_notification)
        return res
    def action_cancel(self):
        res = super().action_cancel()

        for order in self:
            if order.amc_id and not order.is_cancel_note_posted:
                current_time_str = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                amc_cancel_notification = Markup("""
                    <div class="o_notification card border-danger shadow-sm mb-2">
                        <div class="card-header bg-danger text-white d-flex justify-content-between align-items-center py-2">
                            <span class="d-flex align-items-center">
                                <i class="fa fa-exclamation-triangle me-2"></i>
                                <strong>Linked Quotation Cancelled</strong>
                            </span>
                            <span class="badge bg-light text-dark">Attention</span>
                        </div>
                        <div class="card-body p-3">
                            <div class="d-flex align-items-center mb-2">
                                <i class="fa fa-file-signature text-muted me-2"></i>
                                <div>
                                    <span class="text-muted small">Sales Order:</span>
                                    <span class="ms-2 fw-bold">%(order_name)s</span>
                                </div>
                            </div>
                            <div class="d-flex align-items-center mt-2">
                                <i class="fa fa-info-circle text-muted me-2"></i>
                                <span class="text-muted small">This sales order (%(order_name)s) linked to this AMC has been cancelled.</span>
                            </div>
                        </div>
                        <div class="card-footer bg-light d-flex justify-content-between align-items-center py-2">
                            <small class="text-muted">AMC Link Alert</small>
                            <small class="text-muted">
                                <i class="fa fa-clock me-1"></i>%(current_time)s
                            </small>
                        </div>
                    </div>
                """) % {
                    'order_name': order.name,
                    'current_time': current_time_str
                }

                order.amc_id.message_post(body=amc_cancel_notification)
                order.is_cancel_note_posted = True  # ✅ Prevent future duplicates

        return res
    def button_draft(self):
        res = super().button_draft()

        for move in self:
            if move.amc_id:
                current_time_str = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                draft_notification = Markup("""
                    <div class="o_notification card border-info shadow-sm mb-2">
                        <div class="card-header bg-info text-white d-flex justify-content-between align-items-center py-2">
                            <span class="d-flex align-items-center">
                                <i class="fa fa-undo-alt me-2"></i>
                                <strong>Invoice Reset to Draft</strong>
                            </span>
                            <span class="badge bg-light text-dark">Reverted</span>
                        </div>
                        <div class="card-body p-3">
                            <div class="d-flex align-items-center mb-2">
                                <i class="fa fa-file-invoice text-muted me-2"></i>
                                <div>
                                    <span class="text-muted small">Invoice Number:</span>
                                    <span class="ms-2 fw-bold">%(invoice_name)s</span>
                                </div>
                            </div>
                            <div class="d-flex align-items-center mt-2">
                                <i class="fa fa-history text-muted me-2"></i>
                                <span class="text-muted small">This invoice was reset to draft on %(time)s.</span>
                            </div>
                        </div>
                        <div class="card-footer bg-light d-flex justify-content-between align-items-center py-2">
                            <small class="text-muted">Invoice Reset Notification</small>
                            <small class="text-muted"><i class="fa fa-clock me-1"></i>%(time)s</small>
                        </div>
                    </div>
                """) % {
                    'invoice_name': move.name or 'Draft Invoice',
                    'time': current_time_str,
                }

                move.amc_id.message_post(body=draft_notification)

        return res
    
    def action_link_amc(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Link AMC'),  # works now
            'res_model': 'amc.link.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_company_id': self.company_id.id,
            },
        }

