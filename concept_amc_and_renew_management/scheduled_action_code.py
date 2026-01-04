
records = env['renew.model'].search([
    ('renew_type', '=', 'yearly'),
    ('status', '!=', 'cancelled'),
    ('due_on', '>', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
    ('due_on', '<=',
     datetime.datetime.strptime((datetime.datetime.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                                '%Y-%m-%d'))
])
for record in records:
    record.write({'status': 'due'})
# # for critical
records = env['renew.model'].search([
    ('renew_type', '=', 'yearly'),
    ('status', '!=', 'cancelled'),
    ('due_on', '>', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
    ('due_on', '<=',
     datetime.datetime.strptime((datetime.datetime.today() + datetime.timedelta(days=5)).strftime('%Y-%m-%d'),
                                '%Y-%m-%d'))
])

project_task_model = env['project.task']
for record in records:
    # task_values = {
    #     'name': f"{record.title} is critical",  # Adjust the task name as needed
    #     'description': f"Renewal task for {record.title}. Due on {record.due_on}",  # Adjust the description as needed
    #     'project_id': record.projects.id
    #     # Add other relevant fieldsas needed
    # }

    if not record.is_notified:  # Checks if the value is false
        # Actions to perform if the value is false
        # new_task = project_task_model.create(task_values)
        # record.write({'is_notified': True})
        record.write({'status': 'critical'})
        # Other actions as needed
    else:
        # Actions to perform if the value is true
        record.write({'status': 'critical'})
        # Other actions as needed

# # for overdue
records = env['renew.model'].search([
    ('renew_type', '=', 'yearly'),
    ('status', '!=', 'cancelled'),
    ('due_on', '<', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'))
])

for record in records:
    record.write({'status': 'over_due'})  # Or any other action you want to take

# # for monthly 
# # for due
records = env['renew.model'].search([
    ('renew_type', '=', 'yearly'),
    ('status', '!=', 'cancelled'),
    ('due_on', '>', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
    ('due_on', '<=',
     datetime.datetime.strptime((datetime.datetime.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
                                '%Y-%m-%d'))
])
for record in records:
    record.write({'status': 'due'})
# # for critical
records = env['renew.model'].search([
    ('renew_type', '=', 'yearly'),
    ('status', '!=', 'cancelled'),
    ('due_on', '>', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d')),
    ('due_on', '<=',
     datetime.datetime.strptime((datetime.datetime.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d'),
                                '%Y-%m-%d'))
])
tproject_task_model = env['project.task']
for record in records:
    # task_values = {
    #     'name': f"{record.title} is critical",  # Adjust the task name as needed
    #     'description': f"Renewal task for {record.title}. Due on {record.due_on}",  # Adjust the description as needed
    #     'project_id': record.projects.id
    #     # Add other relevant fields as needed
    # }

    if not record.is_notified:  # Checks if the value is false
        # Actions to perform if the value is false
        # new_task = tproject_task_model.create(task_values)
        # record.write({'is_notified': True})
        record.write({'status': 'critical'})
        # Other actions as needed
    else:
        # Actions to perform if the value is true
        record.write({'status': 'critical'})
        # Other actions as needed

# # for overdue
records = env['renew.model'].search([
    ('renew_type', '=', 'yearly'),
    ('status', '!=', 'cancelled'),
    ('due_on', '<', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'))
])

for record in records:
    record.write({'status': 'over_due'})  # Or any other action you want to take
    
 
# for alert
records = env['renew.model'].search([
    ('is_notified', '=', False),
    ('status', '!=', 'cancelled'),
    ('due_on', '>', datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'))
])
filtered_records = records.filtered(lambda r: r.due_on <= datetime.date.today() + datetime.timedelta(days=r.alert_before))

for record in filtered_records:
  
  lead_values = {
    'name': f'Renewal Lead - {record.title}',
    'contact_name': record.customer.name,
    'email_from': record.customer.email,
    'description': record.description,
    'phone': record.phone,
    'partner_id': record.customer.id,
    'user_id': record.responsible_person.id,
        # Add other relevant fields here
  }
  lead = env['crm.lead'].sudo().create(lead_values)
    
  # email_body = f"This is an automated email triggered by Concept Group to remind you to renew <b>{record.title}</b>."  # Customize message

  # email_values = {
  #     'subject': f'Renewal Reminder - {record.title}',
  #     'body_html': email_body,
  #     'email_to': record.responsible_person.email,
  # }
   
  # env['mail.mail'].sudo().create(email_values).send()
  
  # user_groups = record.responsible_person.groups_id
  # domain = [('group_ids', 'in', user_groups.ids)]
  # channels = env['mail.channel'].search(domain)
  # user_channel = channels[0]
  # message_body = f'Renewal Reminder - {record.title}'
  # channel_id = user_channel  # Replace with channel ID
  # channel_id.message_post(body=message_body, type='comment')
  # record.write({'is_notified': True})
   
  record.activity_schedule(
      'mail.mail_activity_data_todo',
      note=f'<b>{record.title}</b> is due soon.',
      date_deadline=record.due_on,
      user_id=record.responsible_person.id,
      res_id=record.id,
      res_model=record._name,
  )
  
  # Update the record
  record.write({'is_notified': True})



