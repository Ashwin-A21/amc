from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class AmcDashboard(models.Model):
    _name = 'amc.model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Renew Model'

    title = fields.Char(string="Title", required=True, tracking=True)
    customer = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    description = fields.Text(string="Details (optional)", tracking=True)
    category = fields.Many2one('amc.types.model', string="Type", required=True, tracking=True)
    customertype = fields.Many2one('renew.customertype.model', string='Category', required=True, tracking=True)
    status = fields.Char(string="Status", default='pending')
    due_on = fields.Date(string="Expiry on", store=True, readonly=False, required=True, tracking=True)
    alert_before = fields.Integer(string="Alert before (in days)", required=True, default=7, tracking=True)
    responsible_person = fields.Many2one(
        'res.users', 
        string="Responsible person", 
        required=True, 
        tracking=True, 
        domain="[('company_ids', 'in', company_id)]", 
        default=lambda self: self.env.user
    )
    reference_no = fields.Char(
        string="Reference No",
        tracking=True,
        readonly=True,
        copy=False,
        index=True,
    )
    is_visitable = fields.Boolean(string="Is Visitable?", tracking=True)
    alert_days = fields.Integer(string="Alert Days", tracking=True)
    frequency = fields.Selection(
        [('yearly', 'Yearly'), ('monthly', 'Monthly'), ('weekly', 'Weekly'), ('daily', 'Daily')],
        string="Frequency",
        tracking=True
    )
    is_notified = fields.Boolean(string='Is Active', default=False, tracking=True)
    name = fields.Char(
        string='AMC Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'  # Set temporary default
    )
    renew_type = fields.Selection(
        [('yearly', 'Yearly'), ('monthly', 'Monthly'), ('weekly', 'Weekly'), ('daily', 'Daily')],
        string='Expiry type',
        default='yearly',
        required=True,
        tracking=True,
    )
    amc_line_ids = fields.One2many(
        'amc.lines.model',
        'amc_dashboard_id',
    )
    sale_order_ids = fields.Many2many(
        'sale.order',
        string='Quotations Created',
        compute='_compute_customer_sale_orders',
        store=False,
        readonly=True
    )
    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices Created',
        compute='_compute_customer_invoices',
        store=False,
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        help="Company for which this AMC record is created"
    )

    def _compute_customer_sale_orders(self):
        for record in self:
            record.sale_order_ids = self.env['sale.order'].search([
                ('amc_id', '=', record.id)
            ])

    @api.depends('sale_order_ids')
    def _compute_customer_invoices(self):
        for record in self:
            record.invoice_ids = self.env['account.move'].search([
                ('amc_id', '=', record.id),
                ('move_type', '=', 'out_invoice')
            ])
            invoice_ids = self.env['account.move']
            for so in record.sale_order_ids:
                invoice_ids |= self.env['account.move'].search([
                    ('invoice_origin', '=', so.name),
                    ('move_type', '=', 'out_invoice')
                ])
            record.invoice_ids = invoice_ids

    def action_open_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.env.context.get('active_id'),
            'target': 'current',
        }

    @api.depends('title')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"Renewal Lead - {record.title or ''}"

    display_name = fields.Char(compute=_compute_display_name, store=True)

    @api.depends('title', 'reference_no')
    def name_get(self):
        result = []
        for record in self:
            name = "Renewal Lead"
            if record.title:
                name += f" - {record.title}"
            elif record.reference_no:
                name += f" - {record.reference_no}"
            else:
                name += f" - {record.id}"
            result.append((record.id, name))
        return result

    @api.model
    def _generate_reference(self):
        sequence_code = 'amc.model.reference.no'
        return self.env['ir.sequence'].next_by_code(sequence_code) or 'New'

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_restore(self):
        self.write({'status': 'pending'})

    @api.onchange('renew_type')
    def _compute_date(self):
        for rec in self:
            today = datetime.today()
            if rec.renew_type == 'yearly':
                rec.due_on = today.replace(year=today.year + 1)
            else:
                rec.due_on = today + relativedelta(months=1)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('amc.model.reference.no')
        vals['reference_no'] = vals.get('name', 'New')
        return super(AmcDashboard, self).create(vals)

    def write(self, values):
        if 'due_on' in values or 'alert_before' in values:
            values['is_notified'] = False
            values['status'] = 'pending'
        result = super(AmcDashboard, self).write(values)
        return result

    @api.onchange('category', 'customer', 'customertype')
    def _onchange_concatenate_fields(self):
        concatenated_value = f"{self.category.name or ''}" + (" - " if self.category.name else "") + f"{self.customer.name or ''}"
        self.title = concatenated_value

    @api.model
    def cron_check_amc_renewals(self):
        env = self.env

        records = env['amc.model'].search([
            ('renew_type', '=', 'yearly'),
            ('status', '!=', 'cancelled'),
            ('due_on', '>', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
            ('due_on', '<=',
             datetime.strptime((date.today() + timedelta(days=30)).strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])
        for record in records:
            record.write({'status': 'due'})

        records = env['amc.model'].search([
            ('renew_type', '=', 'yearly'),
            ('status', '!=', 'cancelled'),
            ('due_on', '>', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
            ('due_on', '<=',
             datetime.strptime((date.today() + timedelta(days=5)).strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])

        project_task_model = env['project.task']
        for record in records:
            if not record.is_notified:
                record.write({'status': 'critical'})
            else:
                record.write({'status': 'critical'})

        records = env['amc.model'].search([
            ('renew_type', '=', 'yearly'),
            ('status', '!=', 'cancelled'),
            ('due_on', '<', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])
        for record in records:
            record.write({'status': 'over_due'})

        # for monthly (there is probably a typo with the 'renew_type', you likely intended 'monthly' in these two)
        records = env['amc.model'].search([
            ('renew_type', '=', 'yearly'),
            ('status', '!=', 'cancelled'),
            ('due_on', '>', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
            ('due_on', '<=',
             datetime.strptime((date.today() + timedelta(days=7)).strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])
        for record in records:
            record.write({'status': 'due'})
        records = env['amc.model'].search([
            ('renew_type', '=', 'yearly'),
            ('status', '!=', 'cancelled'),
            ('due_on', '>', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
            ('due_on', '<=',
             datetime.strptime((date.today() + timedelta(days=2)).strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])
        for record in records:
            if not record.is_notified:
                record.write({'status': 'critical'})
            else:
                record.write({'status': 'critical'})

        records = env['amc.model'].search([
            ('renew_type', '=', 'yearly'),
            ('status', '!=', 'cancelled'),
            ('due_on', '<', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])
        for record in records:
            record.write({'status': 'over_due'})

        # for alert/CRM lead creation
        records = env['amc.model'].search([
            ('is_notified', '=', False),
            ('status', '!=', 'cancelled'),
            ('due_on', '>', datetime.strptime(date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'))
        ])
        filtered_records = records.filtered(lambda r: r.due_on <= date.today() + timedelta(days=r.alert_before))

        for record in filtered_records:
            lead_values = {
                'name': f'Renewal Lead - {record.title}',
                'contact_name': record.customer.name,
                'email_from': record.customer.email,
                'description': record.description,
                'phone': record.customer.phone,
                'partner_id': record.customer.id,
                'user_id': record.responsible_person.id,
                'amc_id': record.id,
                'company_id': record.company_id.id,  # KEY: assign company/branch from AMC record
            }
            # If desired, run in branch context:
            lead = self.env['crm.lead'].sudo().create(lead_values)

            record.activity_schedule(
                'mail.mail_activity_data_todo',
                note=f'<b>{record.title}</b> is due soon.',
                date_deadline=record.due_on,
                user_id=record.responsible_person.id,
                res_id=record.id,
                res_model=record._name,
            )

            record.write({'is_notified': True})
