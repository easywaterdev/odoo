from odoo import models, fields, api
from datetime import date, datetime

class ReturnRefundSalesWizard(models.TransientModel):
    _name = 'return.refund.sales.wizard'
    _description = 'Return/Refund Sales Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def print_report(self):
        datas = self._get_data()
        return self.env.ref('ew_refund_sale_report.action_sales_return_refund').report_action([], data=datas)

    def _get_data(self):
        report_data = []
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'report_data': report_data,
            'subtotals': {},
            'grand_total': 0.0,
        }

        sales_orders = self.env['sale.order.line'].search([
            ('state', '=', 'sale'),
            ('order_id.date_order', '>=', self.start_date),
            ('order_id.date_order', '<=', self.end_date),
        ])

        credit_memos = self.env['account.move.line'].search([
            ('move_id.move_type', '=', 'out_refund'),
            ('move_id.invoice_date', '>=', self.start_date),
            ('move_id.invoice_date', '<=', self.end_date),
            ('parent_state', '=', 'posted'),
            ('product_id', '!=', False),
        ])

        salesperson_sequences = {}
        for order_line in sales_orders:
            salesperson = order_line.order_id.user_id.name
            if salesperson not in salesperson_sequences:
                salesperson_sequences[salesperson] = 1
            else:
                salesperson_sequences[salesperson] += 1

            report_data.append({
                'salesperson': order_line.order_id.user_id.name,
                'salesperson_id': order_line.order_id.user_id.id,
                'salesperson_name': order_line.order_id.user_id.name,
                'date': order_line.order_id.date_order.date(),
                'order_number': order_line.order_id.name,
                'line_sequence': salesperson_sequences[salesperson],
                'product_name': order_line.product_id.name,
                'quantity': order_line.product_uom_qty,
                'price': order_line.price_unit,
                'total': order_line.price_total,
            })

            salesperson = order_line.order_id.user_id.name
            if salesperson not in data['subtotals']:
                data['subtotals'][salesperson] = 0.0
            data['subtotals'][salesperson] += order_line.price_total
            data['grand_total'] += order_line.price_total

        salesperson_sequences = {}
        for credit_memo_line in credit_memos:
            salesperson = credit_memo_line.move_id.user_id.name
            if salesperson not in salesperson_sequences:
                salesperson_sequences[salesperson] = 1
            else:
                salesperson_sequences[salesperson] += 1

            report_data.append({
                'salesperson': credit_memo_line.move_id.user_id.name,
                'salesperson_id': credit_memo_line.move_id.user_id.id,
                'salesperson_name': credit_memo_line.move_id.user_id.name,
                'date': credit_memo_line.move_id.invoice_date,
                'order_number': credit_memo_line.move_id.name,
                'line_sequence': salesperson_sequences[salesperson],
                'product_name': credit_memo_line.product_id.name,
                'quantity': -credit_memo_line.quantity,
                'price': credit_memo_line.price_unit,
                'total': -credit_memo_line.price_total,
            })

            if salesperson not in data['subtotals']:
                data['subtotals'][salesperson] = 0.0
            data['subtotals'][salesperson] -= credit_memo_line.price_total
            data['grand_total'] -= credit_memo_line.price_total

        return data



