from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import UserError
from odoo.tools import float_round

class AmcLines(models.Model):
    _name = 'amc.lines.model'
    _description = 'AMC Lines'

    display_type = fields.Selection(
        [('line_section', 'Section'), ('line_note', 'Note')],
        default=False,
        help="Technical field for UX; display lines carry no amounts."
    )
    name = fields.Char(string='Description')  # text for section/note

    product_id = fields.Many2one('product.product', string='Product', required=False)
    quantity = fields.Float(string='Quantity', default=1.0)
    price = fields.Float(string='Price', compute='_compute_price', store=True, readonly=False)
    amount = fields.Float(string='Amount', compute='_compute_amount', store=True, readonly=False)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    # tax_ids = fields.Many2many('account.tax', string='Taxes', domain=[('active', '=', True)])
    tax_id = fields.Many2one(
        'account.tax',
        string='Tax',
        domain=[('active', '=', True), ('type_tax_use', 'in', ['sale', 'none'])],
    )
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_tax_details', store=True)
    grand_total = fields.Float(string='Grand Total', compute='_compute_grand_total', store=True)
    amc_dashboard_id = fields.Many2one('amc.model', string='AMC Dashboard')

    @api.onchange('product_id')
    def _onchange_product_id_set_name(self):
        for line in self:
            if line.display_type or not line.product_id:
                continue
            # same idea as sale.order.line label
            line.name = line.product_id.get_product_multiline_description_sale() or line.product_id.display_name

    @api.depends('price', 'quantity', 'display_type')
    def _compute_amount(self):
        for line in self:
            line.amount = 0.0 if line.display_type else (line.price * (line.quantity or 0.0))

    @api.depends('amount', 'display_type')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = 0.0 if line.display_type else line.amount

    @api.depends('subtotal', 'tax_id', 'display_type')
    def _compute_tax_details(self):
        for line in self:
            if line.display_type or not line.tax_id:
                line.tax_amount = 0.0
                continue
            taxes = line.tax_id.compute_all(
                line.subtotal,
                currency=line.amc_dashboard_id.company_id.currency_id or self.env.company.currency_id,
                quantity=1.0,
                product=line.product_id,
                partner=line.amc_dashboard_id.customer,
            )
            line.tax_amount = taxes['total_included'] - taxes['total_excluded']

    @api.depends('subtotal', 'tax_amount', 'display_type')
    def _compute_grand_total(self):
        for line in self:
            line.grand_total = 0.0 if line.display_type else (line.subtotal + line.tax_amount)

    @api.model_create_multi
    def create(self, vals_list):
        # Drop legacy key if it comes from old views/browsers
        for vals in vals_list:
            vals.pop('tax_ids', None)
        return super().create(vals_list)

    def write(self, values):
        values.pop('tax_ids', None)
        return super().write(values)
    def _line_label(self):
        self.ensure_one()
        if self.display_type == 'line_section':
            return _("Section: %s", self.name or "-")
        if self.display_type == 'line_note':
            return _("Note")
        return self.product_id.display_name or (self.name or _("Line"))
    def _post_to_amc(self, html_body):
        self.ensure_one()
        if self.amc_dashboard_id:
            self.amc_dashboard_id.message_post(body=Markup(html_body), subtype_xmlid='mail.mt_note', message_type='comment')

    def unlink(self):
        for line in self:
            label = line._line_label()
            html = _("Removed line: %s (Qty %s, Price %s)", label, line.quantity or 0.0, line.price or 0.0)
            line._post_to_amc(html)
        return super().unlink()
    def write(self, vals):
        track_map = {
            'product_id': _("Product"),
            'name': _("Description"),
            'quantity': _("Quantity"),
            'price': _("Price"),
            'tax_id': _("Tax"),
        }
        before = {rec.id: {f: getattr(rec, f) for f in vals.keys() if f in track_map} for rec in self}
        res = super().write(vals)
        for rec in self:
            changes = []
            for f, label in track_map.items():
                if f in vals:
                    old = before.get(rec.id, {}).get(f)
                    new = getattr(rec, f)
                    # Make m2o readable
                    if hasattr(old, 'display_name'):
                        old = old.display_name
                    if hasattr(new, 'display_name'):
                        new = new.display_name
                    if old != new:
                        changes.append(f"{label}: {old} → {new}")
            if changes:
                html = _("Updated line: %s — %s", rec._line_label(), ", ".join(changes))
                rec._post_to_amc(html)
        return res



     