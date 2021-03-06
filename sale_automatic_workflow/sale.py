# -*- coding: utf-8 -*-
###############################################################################
#
#    sale_automatic_workflow for OpenERP
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>
#    Copyright 2013 Camptocamp SA (Guewen Baconnier)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from openerp import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class sale_order(models.Model):
    _inherit = "sale.order"

    workflow_process_id = fields.Many2one(comodel_name='sale.workflow.process',
                                          string='Automatic Workflow',
                                          ondelete='restrict')

    @api.multi
    def validate_sales(self):
        _logger.info("Sale start validate %s" % self)
        self.action_button_confirm()

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        invoice_vals = super(sale_order, self)._prepare_invoice(
            cr, uid, order, lines, context=context)
        workflow = order.workflow_process_id
        if not workflow:
            return invoice_vals
        invoice_vals['workflow_process_id'] = workflow.id
        if workflow.invoice_date_is_order_date:
            invoice_vals['date_invoice'] = order.date_order
        if workflow.property_journal_id:
            invoice_vals['journal_id'] = workflow.property_journal_id.id
        return invoice_vals

    def _prepare_order_picking(self, cr, uid, order, context=None):
        picking_vals = super(sale_order, self)._prepare_order_picking(
            cr, uid, order, context=context)
        if order.workflow_process_id:
            picking_vals['workflow_process_id'] = order.workflow_process_id.id
        return picking_vals

#    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
#        vals = super(sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
#        #stock_picking = self.pool.get('stock.picking').browse(cr, uid, [order.picking_ids], context=context)
#        _logger.info("Prepare procurations %s:%s" % (order.picking_ids.id, vals))
#        #for stock_picking_line in stock_picking:
#        if order.picking_ids:
#            ids = order.picking_ids
#            if isinstance(ids, (int, long)):
#                ids = [ids]
#            self.pool.get('stock.picking').write(cr, uid, ids, {'workflow_process_id': order.workflow_process_id.id}, context=context)
#        return vals

    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        _logger.info("Order %s" % vals)
        if not vals.get('workflow_process_id') and vals.get('section_id'):
            workflow = self.env['sale.workflow.process'].search([['section_id', '=', vals.get('section_id')]])
            vals['workflow_process_id'] = workflow.id
        return super(sale_order, self).create(vals)

    @api.onchange('workflow_process_id')
    def onchange_workflow_process_id(self):
        if not self.workflow_process_id:
            return
        workflow = self.workflow_process_id
        if workflow.picking_policy:
            self.picking_policy = workflow.picking_policy
        if workflow.order_policy:
            self.order_policy = workflow.order_policy
        if workflow.invoice_quantity:
            self.invoice_quantity = workflow.invoice_quantity
        if workflow.section_id:
            self.section_id = workflow.section_id.id
        if workflow.warning:
            warning = {'title': _('Workflow Warning'),
                       'message': workflow.warning}
            return {'warning': warning}

    @api.multi
    def test_create_invoice(self):
        """ Workflow condition: test if an invoice should be created,
        based on the automatic workflow rules """
        self.ensure_one()
        if self.order_policy != 'manual' or not self.workflow_process_id:
            return False
        invoice_on = self.workflow_process_id.create_invoice_on
        if invoice_on == 'on_order_confirm':
            return True
        elif invoice_on == 'on_picking_done':
            if self.shipped:
                return True
            # case of a sale order with only product service
            sale_obj = self.env['sale.order']
            no_products = [sale_obj.test_no_product(order) for order in self]
            if no_products.count(False) == 0:
                return True
        return False
