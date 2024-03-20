import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.contacts.doctype.contact.test_contact import create_contact
from frappe.tests.test_api import FrappeAPITestCase


class TestExotel(FrappeAPITestCase):
	@classmethod
	def setUpClass(cls):
		frappe.db.delete("Call Log")
		cls.CURRENT_DB_CONNECTION = frappe.db
		cls.test_employee_name = make_employee(
			user="test_employee_exotel@company.com", cell_number="9999999999"
		)
		frappe.db.set_value("Exotel Settings", "Exotel Settings", "enabled", 1)
		phones = [
			{"phone": "+91 9999999991", "is_primary_phone": 0, "is_primary_mobile_no": 1}
		]
		create_contact(name="Test Contact", salutation="Mr", phones=phones)
		cls.webhook_key = "exotel_integration_key"
		frappe.db.set_value("Exotel Settings", "Exotel Settings", "webhook_key", cls.webhook_key)
		frappe.db.commit()

	def test_for_successful_call(self):
		from .exotel_test_data import call_end_data, call_initiation_data

		self.emulate_api_call_from_exotel(call_initiation_data)
		self.emulate_api_call_from_exotel(call_end_data)
		call_log = frappe.get_doc("Call Log", call_initiation_data.CallSid)

		self.assertEqual(call_log.get("from"), call_initiation_data.CallFrom)
		self.assertEqual(call_log.get("to"), call_initiation_data.DialWhomNumber)
		self.assertEqual(call_log.get("call_received_by"), self.test_employee_name)
		self.assertEqual(call_log.get("status"), "Completed")

	def test_for_disconnected_call(self):
		from .exotel_test_data import call_disconnected_data

		self.emulate_api_call_from_exotel(call_disconnected_data)
		call_log = frappe.get_doc("Call Log", call_disconnected_data.CallSid)
		self.assertEqual(call_log.get("from"), call_disconnected_data.CallFrom)
		self.assertEqual(call_log.get("to"), call_disconnected_data.DialWhomNumber)
		self.assertEqual(call_log.get("call_received_by"), self.test_employee_name)
		self.assertEqual(call_log.get("status"), "Canceled")

	def test_for_call_not_answered(self):
		from .exotel_test_data import call_not_answered_data

		self.emulate_api_call_from_exotel(call_not_answered_data)
		call_log = frappe.get_doc("Call Log", call_not_answered_data.CallSid)
		self.assertEqual(call_log.get("from"), call_not_answered_data.CallFrom)
		self.assertEqual(call_log.get("to"), call_not_answered_data.DialWhomNumber)
		self.assertEqual(call_log.get("call_received_by"), self.test_employee_name)
		self.assertEqual(call_log.get("status"), "No Answer")

	def emulate_api_call_from_exotel(self, data):
		self.post(
			f"/api/method/exotel_integration.handler.handle_request?key={self.webhook_key}",
			data=data,
			content_type="application/json",
		)
		# restart db connection to get latest data
		frappe.connect()

	@classmethod
	def tearDownClass(cls):
		frappe.db = cls.CURRENT_DB_CONNECTION
