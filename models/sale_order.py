# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import requests
import json
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _default_get_is_have_token(self):
        """Add the company of the parent as default if we are creating a child partner."""
        have_token = self.env['ir.config_parameter'].sudo().get_param('integrate_shipping.is_token')
        if have_token:
            return True

    is_have_token = fields.Boolean(default=_default_get_is_have_token)

    def get_slug(self):
        """

        :return:
        """
        list_slug = []
        if self.env['ir.config_parameter'].sudo().get_param('integrate_shipping.is_token'):
            token = self.env['ir.config_parameter'].sudo().get_param('integrate_shipping.token')
            url = 'https://api.aftership.com/v4/couriers'
            headers = {
                'aftership-api-key': token,
                'Content-Type': 'application/json'
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            str_res = str(response)
            if str_res == '<Response [200]>' or str_res == '<Response [201]>':
                for i in range(0, len(data['data']['couriers'])):
                    list_slug.extend([(data['data']['couriers'][i]['slug'], data['data']['couriers'][i]['name'])])
                return list_slug
            else:
                raise ValidationError(
                    'There is no response from the API Token. Please make sure the api entered is valid!')
        else:
            return list_slug

    slug_order = fields.Char(store=True)
    tracking_number_order = fields.Char(store=True)
    slug_type = fields.Selection(selection=get_slug, string='Slug Category')
    delivery_type = fields.Selection(string='Delivery Type', selection=[('pickup_at_store', 'Pickup At Store'),
                                                                        ('pickup_at_courier', 'Pickup At Courier'),
                                                                        ('door_to_door', 'Door To Door')])
    language = fields.Selection(string='Language', selection=[('vi', 'Vietnam'), ('en', 'English')])
    pickup_note = fields.Text(string='Pickup Note')

    def action_confirm(self):
        if self.env['ir.config_parameter'].sudo().get_param('integrate_shipping.is_token'):
            token = self.env['ir.config_parameter'].sudo().get_param('integrate_shipping.token')
            url = 'https://api.aftership.com/v4/trackings'
            headers = {
                'aftership-api-key': token,
                'Content-Type': 'application/json'
            }
            for records in self:
                for record in records.order_line:
                    code = self.name
                    transfer_code = str(code[2:])
                    pickup_note = records.pickup_note if records.pickup_note else ''
                    language = records.language if records.language else ''
                    if records.partner_invoice_id.street and records.partner_id.state_id and records.partner_id.country_id:
                        address = str(records.partner_invoice_id.street) + ' - ' + str(
                            records.partner_invoice_id.state_id.name) + ' - ' + str(
                            records.partner_invoice_id.country_id.name)
                    else:
                        address = ''
                    data = {
                        "tracking": {
                            "slug": records.slug_type,
                            "tracking_number": str(datetime.now().strftime('%y%m%d')) + transfer_code,
                            "title": "Transfer Order " + str(records.name),
                            "smses": records.partner_id.phone,
                            "emails": records.partner_id.email,
                            "order_id": records.name,
                            "custom_fields": {
                                "product_name": record.product_id.name,
                                "product_price": record.product_id.lst_price
                            },
                            "language": language,
                            "customer_name": records.partner_id.name,
                            "order_promised_delivery_date": str(
                                (records.date_order + timedelta(days=10)).strftime('%Y-%m-%d')),
                            "delivery_type": records.delivery_type,
                            "pickup_location": address,
                            "pickup_note": pickup_note
                        }
                    }
                    tracking_number = data['tracking']['tracking_number']
                    slug = data['tracking']['slug']
                    data_json = json.dumps(data, indent=4)
                    data_json.replace(" ' ", ' " ')
                    requests.post(url, data=data_json, headers=headers)
                    records.slug_order = slug
                    records.tracking_number_order = tracking_number
            res = super(SaleOrderInherit, self).action_confirm()
            return res
        else:
            res = super(SaleOrderInherit, self).action_confirm()
            return res
