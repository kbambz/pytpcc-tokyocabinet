# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# Copyright (C) 2011
# Marcelo Martins
# http://www.cs.brown.edu/~martins/
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# -----------------------------------------------------------------------

from __future__ import with_statement
from abstractdriver import *
from pprint import pprint.pformat

import commands
import constants
import logging
import os
import pytyrant
import sys

try:
	import psyco
except ImportError:
	pass
else:
	psyco.profile()

class TokyocabinetDriver(AbstractDriver):

	DEFAULT_CONFIG = {
		"Server1",
		{
			"ORDER",
			{
				"host": "localhost",
				"port": 1978,
				"persistent": True
			}
		}
	}

	def __init__(self, ddl):
		super(TokyocabinetDriver, self).__init__("tokyocabinet", ddl)
		self.databases = dict()
		self.conn = dict()

	##-----------------------------------------------
	## tupleToString
	##-----------------------------------------------
	def tupleToString(self, tuple, sep=":"):
		"""Tokyo-Cabinet table-type databases only accept strings as keys.
		   This function transforms a compound key (tuple) into a string.
		   Tuples elements are separated by the sep char"""
		   return sep.join(str(t) for t in tuple)

    ##-----------------------------------------------
	## getServer
	##-----------------------------------------------
	def getServer(self, warehouseID):
		"""Return server that contains partitioned data, according to warehouseID"""
		sID = self.partition.get(warehouseID, -1)
		return sID

	## ----------------------------------------------
	## makeDefaultConfig
	## ----------------------------------------------
	def makeDefaultConfig(self):
		return TokyocabinetDriver.DEFAULT_CONFIG

	## ----------------------------------------------
	## loadDefaultConfig
	## ----------------------------------------------
	def loadDefaultConfig(self, config):
		for key in map(lambda x:x[0], TokyocabinetDriver.DEFAULT_CONFIG):
			assert key in config, "Missing parameter '%s' in %s configuration" % (key, self.name)

		for serverId, tables in config.iteritems():
			self.databases[serverId] = tables

		# First connect to databases
		for serverId, tables in self.databases.iteritems():
			conn = self.conn.get(serverId, dict())
			for tab, values in tables.iteritems():
				conn[serverId][tab] = pyrant.Tyrant(values["host"], values["port"])
			self.conn[serverId] = conn

		## FOR

		if config["reset"]:
			for serverId, tables in self.conn.iteritems():
				for tab in tables.keys():
					logging.debug("Deleting database '%s'" % tab)
					self.conn[serverId][tab].vanish()

	## -------------------------------------------
	## loadTuples
	## -------------------------------------------
	def loadTuples(self, tableName, tuples):
		"""Load tuples into tables of database
		   Each table is a connection to a Tyrant server. Each record is a key-value pair,
		   where key = primary key, values = concatenation of columns (dictionary). If
		   key is compound we transform it into a string, since TC does not support
		   compound keys. Data partitioning occurs based on Warehouse ID."""

		## TODO:
		## 1. Use denormalized tables?
		## 2. Remove redundant columns
		## 3. Finish ITEM table filling
		## 4. Create indexes
		if len(tuples) == 0: return

		logging.debug("Loading %d tuples of tableName %s" % (len(tuples), tableName))

		assert tableName in TABLE_COLUMNS, "Unexpected table %s" % tableName
		columns = TABLE_COLUMNS[tableName]
		num_colums = xrange(len(columns))

		## We want to combine all of a CUSTOMER's ORDERS, ORDER_LINE, and
		## records into a single document
		if self.denormalize and tableName in TokyocabinetDriver.DENORMALIZED_TABLES:
			## TODO
		else:
			## If this is the CUSTOMER table, then we'll just store the record locally for now
			if tableName == constants.TABLENAME_CUSTOMER:
				for t in tuples:
					c_key = tupleToString(t[:3]) # C_ID, D_ID, W_ID
					self.w_customers[c_key] = dict(map(lambda i: (columns[i], t[i]), num_columns))
				## FOR

			## If this is an ORDER_LINE record, then we need to stick it inside of the right 
			## ORDERS record
			elif tableName == constants.TABLENAME_ORDER_LINE:
				for t in tuples:
					o_key = tupleToString(t[:3]) # O_ID, O_D_ID, O_W_ID
					(c_key, o_idx) = self.w_order[o_key]

			if tableName == constants.TABLENAME_WAREHOUSE:
				for t in tuples:
					w_key = t[:1] # W_ID
					sID = getServer(w_key)
					cols = dict(map(lambda i: (columns[i], t[i]), num_columns))
					try:
						self.conn[sID][tableName].put(str(w_key), cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif table == constants.TABLENAME_DISTRICT:
				for t in tuples:
					w_key = str(t[1:2]) # W_ID
					d_key = tupleToString(t[:2]) # D_ID, D_W_ID
					cols = dict(map(lambda i: (columns[i], t[i]), num_columns))
					self.conn[w_key][tableName].put(d_key, cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif table == constants.TABLENAME_ITEM:
					# TODO: Item table has no w_id. How to partition?

			elif tableName == constants.TABLENAME_CUSTOMER:
				for t in tuples:
					try:
						w_key = str(t[2:3]) # W_ID
						c_key = tupleToString(t[:3]) # C_ID, C_D_ID, C_W_ID
						cols = ditc(map(lambda i: (columns[i], t[i]), num_columns))
						self.conn[w_key][tableName].put(c_key, cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif tableName == constants.TABLENAME_HISTORY:
				for t in tuples:
					w_key = t[4:5] # W_ID
					sID = getServer(w_key)
					cols = dict(map(lambda i: (columns[i], t[i], num_columns)))
					try:
						self.conn[sID][tableName].put(str(w_key), cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif tableName == constants.TABLENAME_STOCK:
				for t in tuples:
					w_key = t[1:2] # W_ID
					sID = getServer(w_key)
					s_key = tupleToStriong(t[:2]) # S_ID, S_W_ID
					cols = dict(map(lambda i: (columns[i], t[i]), num_columns))
					try:
						self.conn[sID][tableName].put(s_key, cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif tableName == constants.TABLENAME_ORDERS:
				for t in tuples:
					w_key = t[3:4] # W_ID
					sID = getServer(w_key)
					o_key = tupleToString(t[1:4]) # O_ID, O_D_ID, O_W_ID
					cols = dict(map(lambda i: (columns[i], t[i], num_columns)))
					try:
						self.conn[sID][tableName].put(o_key, cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif tableName == constants.TABLENAME_NEW_ORDER:
				for t in tuples:
					w_key = t[2:3] # W_ID
					sID = getServer(w_key)
					no_key = tupleToString(t[:3]) # NO_O_ID, NO_D_ID, NO_W_ID
					cols = dict(map(lambda i: (columns[i], t[i], num_columns)))
					try:
						self.conn[sID][tableName].put(no_key, cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

			elif tableName == constants.TABLENAME_ORDER_LINE:
				for t in tuples:
					w_key = t[2:3] # W_ID
					sID = getServer(w_key)
					ol_key = tupleToString(t[:4]) # OL_O_ID, OL_D_ID, OL_W_ID, OL_NUMBER
					cols = dict(map(lambda i: (columns[i], t[i], num_columns)))
					try:
						self.conn[sID][tableName].put(ol_key, cols)
					except KeyError, err:
						sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
						sys.exit(1)
				## FOR

		logging.debug("Loaded %s tuples for tableName %s" % (len(tuples), tableName))
		return

	## -------------------------------------------
	## loadFinish
	## -------------------------------------------
	def loadFinish(self)
		logging.info("Finished loading tables")

	## --------------------------------------------
	## doDelivery
	## --------------------------------------------
	def doDelivery(self, params):
		"""Execute DELIVERY Transaction
		Parameters Dict:
			w_id
			o_carrier_id
			ol_delivery_id
		"""

		w_id = params["w_id"]
		o_carrier_id = params["o_carrier_id"]
		ol_delivery_d = params["ol_delivery_id"]

		sID = getServer(w_id)

		try:
			newOrderQuery = self.conn[sID]["NEW_ORDER"].query
			ordersQuery   = self.conn[sID]["ORDERS"].query
			orderLineQuery = self.conn[sID]["ORDER_LINE"].query
			customerQuery = self.conn[sID]["CUSTOMER"].query
		except KeyError, err:
			sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
			sys.exit(1)


		results = [ ]
		for d_id in xrange(1, constants.DISTRICTS_PER_WAREHOUSE+1):

			# getNewOrder
			newOrders = newOrderQuery.filter("NO_D_ID" = d_id, "NO_W_ID" = w_id, "NO_O_ID" = 1)
			if len(newOrders) == 0:
				## No orders for this district: skip it. Note: This must
				## reported if > 1%
				continue
			assert len(newOrders) > 0
			no_o_id = newOrders.columns("NO_O_ID")[0]["NO_O_ID"]

			# getCId
			cids = orderQuery.filter("O_ID" = no_o_id, "O_D_ID" = d_id, "O_W_ID" = w_id, "O_C_ID" = 1)
			assert len(c_ids) > 0
			c_id = cids.columns("O_C_ID")[0]["O_C_ID"]

			# sumOLAmount
			olines = orderLineQuery.filter("OL_O_ID" = no_o_id, "OL_D_ID" = d_id, "OL_W_ID" = w_id)

			# These must be logged in the "result file" according to TPC-C 
			# 2.7.22 (page 39)
			# We remove the queued time, completed time, w_id, and 
			# o_carrier_id: the client can figure them out
			# If there are no order lines, SUM returns null. There should
			# always be order lines.
			assert len(olines) > 0, "ol_total is NULL: there are no order lines. This should not happen"

			ol_total = sum(olines.columns("OL_AMOUNT").values())

			assert ol_total > 0.0

			# deleteNewOrder
			orders = newOrderQuery.filter("NO_D_ID" = d_id, "NO_W_ID" = w_id, "NO_O_ID" = no_o_id)
			orders.delete(quick=True)

			# updateOrders
			orders = orderQuery.filter("O_ID" = no_o_id, "O_D_ID" = d_id, "O_W_ID" = w_id)
			## UPDATE ORDERS SET O_CARRIER_ID = ?...
			for record in orders:
				key, cols = record
				cols["O_CARRIER_ID"] = o_carrier_id
				self.conn[sID]["ORDERS"].put(key, orders)

			# updateOrderLine
			orders = orderLineQuery.filter("OL_O_ID" = no_o_id, "OL_D_ID" = d_id, "OL_W_ID" = w_id)
			for record in orders:
				key, cols = record
				cols["OL_DELIVERY_ID"] = ol_delivery_id
				self.conn[sID]["ORDER_LINE"].put(key, ol_delivery_d)

			# updateCustomer
			customers = customerQuery.filter("C_ID" = c_id, "C_D_ID" = d_id, "C_W_ID" = w_id)
			for record in customers:
				key, cols = record
				cols["C_BALANCE"] += ol_total
				self.conn[sID]["CUSTOMER"].put(key, cols)
		
			result.append((d_id, no_o_id))
		## FOR

		return result

	def doNewOrder(self, params):
		"""Execute NEW_ORDER Transaction
		Parameters Dict:
			w_id
			d_id
			c_id
			o_entry_id
			i_ids
			i_w_ids
			i_qtys
		"""

		w_id = params["w_id"]
		d_id = params["d_id"]
		c_id = params["c_id"]
		o_entry_d = params["o_entry_d"]
		i_ids = params["i_ids"]
		i_w_ids = params["i_w_ids"]
		i_qtys = params["i_qtys"]

		assert len(i_ids) > 0
		assert len(i_ids) == len(i_w_ids)
		assert len(i_ids) == len(i_qtys)

		sID = getServer(w_id)

		try:
			warehouseQuery = self.conn[sID]["WAREHOUSE"].query
			districtQuery  = self.conn[sID]["DISTRICT"].query
			customerQuery  = self.conn[sID]["CUSTOMER"].query
			orderQuery = self.conn[sID]["ORDERS"].query
			newOrderQuery = self.conn[sID]["NEW_ORDER"].query
			itemQuery = self.conn[sID]["ITEM"].query
			stockQuery = self.conn[sID]["STOCK"].query
		except KeyError, err:
			sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
			sys.exit(1)

		all_local = True
		items = [ ]
		for i in xrange(len(i_ids)):
			## Determine if this is an all local order or not
			all_local = all_local and i_w_ids[i] == w_id
			# getItemInfo
			itemInfo = itemQuery.filter("I_PRICE" = i_ids[i])
			items.append(itemInfo[0])
		assert len(items) == len(i_ids)

		## TPCC define 1% of neworder gives a wrong itemid, causing rollback.
		## Note that this will happen with 1% of transactions on purpose.
		for item in items:
			if len(item) == 0:
				## TODO Abort here!
				return
		## FOR

		## -----------------
		## Collect Information from WAREHOUSE, DISTRICT, and CUSTOMER
		## -----------------
		
		# getWarehouseTaxRate
		taxes = warehouseQuery.filter("W_ID" = w_id)
		w_tax = taxes.columns("W_TAX")[0]("W_TAX")

		# getDistrict
		districts = districtQuery.filter("D_ID" = d_id, "D_W_ID" = w_id)
		districtInfo = districts.columns("D_TAX", "D_NEXT_O_ID")[0]
		d_tax = districtInfo["D_TAX"]
		d_next_o_id = districtInfo["D_NEXT_O_ID"]

		# getCustomer
		customers = customerQuery.filter("C_W_ID" = w_id, "C_D_ID" = d_id, "C_ID" = c_id)
		customerInfo = customers.columns("C_DISCOUNT", "C_LAST", "C_CREDIT")[0]
		c_discount = customerInfo["C_DISCOUNT"]

		## -----------------
		## Insert Order Information
		## -----------------
		ol_cnt = len(i_ids)
		o_carrier_id = constants.NULL_CARRIER_ID

		# incrementNextOrderId
		districts = districtQuery.filter("D_ID" = d_id, "D_W_ID" = w_id)
		for record in districts:
			key, cols = record
			cols["D_NEXT_O_ID"] = d_next_o_id + 1
			self.conn[sID]["DISTRICT"].put(key, cols)

		# createOrder
		key = tupleToString((d_next_o_id, d_id, w_id))
		cols = {"O_ID": d_next_o_id, "O_D_ID": d_id, "O_W_ID": w_id, "O_C_ID":
						c_id, "O_ENTRY_D": o_entry_d, "O_CARRIER_ID":
						o_carrier_id, "O_OL_CNT": o_ol_cnt, "O_ALL_LOCAL":
						all_local}
		self.conn[sID]["ORDERS"].put(key, cols)

		# createNewOrder
		key = tupleToString((d_next_o_id, d_id, w_id))
		cols = {"NO_O_ID": d_next_o_id, "NO_D_ID": d_id, "NO_W_ID": w_id}
		self.conn[sID]["NEW_ORDER"].put(key, cols)

		## -------------------------------
		## Insert Order Item Information
		## -------------------------------

		item_data = [ ]
		total = 0
		for i in xrange(len(i_id)):
			ol_number = i+1
			ol_supply_w_id = i_w_ids[i]
			ol_i_id = i_ids[i]
			ol_quantity = i_qtys[i]

			# getItemInfo
			key, itemInfo = items[i]
			i_price = itemInfo["I_PRICE"]
			i_name  = itemInfo["I_NAME"]
			i_data  = itemInfo["I_DATA"]

			# getStockInfo
			stocks = stockQuery.filter("S_I_ID" = ol_i_id, "S_W_ID" = ol_supply_w_id)
			if len(stocks) == 0:
				logging.warn("No STOCK record for (ol_i_id=%d, ol_supply_w_id=%d)"
								% (ol_i_id, ol_supply_w_id))
				continue
			stockInfo = stock.columns("S_QUANTITY", "S_DATA", "S_YTD", "S_ORDER_CNT",
						"S_REMOTE_CNT", "S_DIST_%02d"%d_id)[0]

			s_quantity = stockInfo["S_QUANTITY"]
			s_data = stockInfo["S_DATA"]
			s_ytd = stockInfo["S_YTD"]
			s_order_cnt = stockInfo["S_ORDER_CNT"]
			s_remote_cnt = stockInfo["S_REMOTE_CNT"]
			s_dist_xx = stockInfo["S_DIST_%02d"%d_id] # Fetches data from the
													# s_dist_[d_id] column

			# updateStock
			s_ytd += ol_quantity
			if s_quantity >= ol_quantity + 10:
				s_quantity = s_quantity - ol_quantity
			else:
				s_quantity = s_quantity + 91 - ol_quantity
			s_order_cnt += 1

			if ol_supply_w_id != w_id: s_remote_cnt += 1

			stocks = stockQuery.filter("S_I_ID" = ol_i_id, "S_W_ID" = ol_supply_w_id)
			for record in stocks:
				key, cols = record
				cols["S_QUANTITY"] = s_quantity
				cols["S_YTD"] = s_ytd
				cols["S_ORDER_CNT"] =  s_order_cnt
				cols["S_REMOTE_CNT"] = s_remote_cnt
				self.conn[sID]["STOCK"].put(key, cols)

			if i_data.find(constants.ORIGINAL_STRING) != -1 and s_data.find(constants.ORIGINAL_STRING) != -1:
				bran_generic = 'B'
			else:
				brand_generic = 'G'

			## Transaction profile states to use "ol_quantity * i_price"
			ol_amount = ol_quantity * i_price
			total += ol_amount

			# createOrderLine
			key = tupletoString((d_next_o_id, d_id, w_id, ol_number))
			cols = ("OL_O_ID": d_next_o_id, "OL_D_ID": d_id, "OL_W_ID": w_id,
							"OL_NUMBER": ol_number, "OL_I_ID": ol_i_id,
							"OL_SUPPLY_W_ID": ol_supply_w_id, "OL_DELIVERY_D":
							ol_entry_d, "OL_QUANTITY": ol_quantity, "OL_AMOUNT":
							ol_amount, "OL_DIST_INFO": s_dist_xx)
			self.conn[sID]["ORDER_LINE"].put(key, cols)

			## Add the info to be returned
			item_data.append((i_name, s_quantity, brand_generic, i_price, ol_amount))
		## FOR
		
		## Commit!
		# TODO Commit
		#for tab in self.conn[sID].keys():
		#	self.conn[sID][tab].sync()

		## Adjust the total for the discount
		#print "c_discount:", c_discount, type(c_discount)
		#print "w_tax:", w_tax, type(w_tax)
		#print "d_tax:", d_tax, type(d_tax)
		total *= (1 - c_discount) * (1 + w_tax + d_tax)

		## Pack up values the client is missing (see TPC-C 2.4.3.5)
		misc = [(w_tax, d_tax, d_next_o_id, total)]

		return [ customerInfo, misc, item_data ]

	def doOrderStatus(self, params):
		"""Execute ORDER_STATUS Transaction
		Parameters Dict:
			w_id
			d_id
			c_id
			c_last
		"""
		w_id = params["w_id"]
		d_id = params["d_id"]
		c_id = params["c_id"]
		c_last = params["c_last"]

		assert w_id, pformat(params)
		assert d_id, pformat(params)

		sID = getServer(w_id)

		try:
			customerQuery = self.conn["CUSTOMER"]
			orderQuery    = self.conn["ORDERS"]
			orderLineQuery= self.conn["ORDER_LINE"]
		except KeyError, err:
			sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
			sys.exit(1)

		if c_id != None:
			# getCustomerByCustomerId
			customers = customerQuery.filter("C_W_ID" = w_id, "C_D_ID" = d_id, "C_ID" = c_id)
			customerInfo = customer.columns("C_ID", "C_FIRST", "C_MIDDLE", "C_LAST", "C_BALANCE")[0]
		else:
			# Get the midpoint customer's id
			# getCustomersByLastName
			customers = customerQuery.filter("C_W_ID" = w_id, "C_D_ID" = d_id, "C_LAST" = c_last).order_by("C_FIRST")
			all_customers = customers.columns("C_ID", "C_FIRST", "C_MIDDLE", "C_LAST", "C_BALANCE")
			namecnt = len(all_customers)
			assert namecnt > 0
			index = (namecnt-1)/2
			customer = all_customers[index]
			c_id = customer["C_ID"]
		assert len(customer) > 0
		assert c_id != None

		# getLastOrder
		orders = orderQuery.filter("O_W_ID" = w_id, "O_D_ID" = d_id, "O_C_ID" =	c_id).order_by("-O_ID", numeric=True)
		orderInfo = orders.columns("O_ID", "O_CARRIER_ID", "O_ENTRY_D")[0]
		o_id = orderInfo["O_ID"]

		# getOrderLines
		if order:
			orders = orderLineQuery.filter("OL_W_ID" = w_id, "OL_D_ID" = d_id, "OL_O_ID" = o_id)
			orderLines = orderLines.columns("OL_SUPPLY_W_ID", "OL_I_ID", "OL_QUANTITY", "OL_AMOUNT", "OL_DELIVERY_D")
		else:
			orderLines = [ ]

		## Commit!
		# TODO Commit
		#for tab in self.conn[sID].keys():
		#	self.conn[sID][tab].sync()

		return [customerInfo, orderInfo, orderLines]

	def doPayment(self, params):
		"""Execute PAYMENT Transaction
		Parameters Dict:
			w_id
			d_id
			h_amount
			c_w_id
			c_d_id
			c_id
			c_last
			h_date
		"""

		w_id = params["w_id"]
		d_id = params["d_id"]
		h_amount = params["h_amount"]
		c_w_id = params["c_w_id"]
		c_d_id = params["c_d_id"]
		c_id = params["c_id"]
		c_last = params["c_last"]
		h_date = params["h_date"]

		sID = getServer(w_id)

		try:
			customerQuery  = self.conn["CUSTOMER"]
			wareHouseQuery = self.conn["WAREHOUSE"]
			districtQuery  = self.conn["DISTRICT"]
		except KeyError, err:
			sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
			sys.exit(1)

		if c_id != None:
			# getCustomerByCustomerId
			customers = customerQuery.filter("C_W_ID" = w_id, "C_D_ID" = d_id, "C_ID" = c_id)
			customerInfo = customer.columns("C_ID", "C_FIRST", "C_MIDDLE",
							"C_LAST", "C_BALANCE", "C_YTD_PAYMENT",
							"C_PAYMENT_CNT", "C_DATA" "C_CREDIT")[0]
		else:
			# Get the midpoint customer's id
			# getCustomersByLastName
			customers = customerQuery.filter("C_W_ID" = w_id, "C_D_ID" = d_id, "C_LAST" = c_last).order_by("C_FIRST")
			all_customers = customers.columns("C_ID", "C_FIRST", "C_MIDDLE",
							"C_LAST", "C_BALANCE", "C_YTD_PAYMENT",
							"C_PAYMENT_CNT", "C_DATA", "C_CREDIT")
			namecnt = len(all_customers)
			assert namecnt > 0
			index = (namecnt-1)/2
			customer = all_customers[index]
			c_id = customer["C_ID"]
		assert len(customer) > 0

		c_balance = customerInfo["C_BALANCE"] - h_amount
		c_ytd_payment = customerInfo["C_YTD_PAYMENT"] + h_amount
		c_payment_cnt = customerInfo["C_PAYMENT_CNT"] + 1
		c_data = customerInfo["C_DATA"]

		# getWarehouse
		warehouses = warehouseQuery.filter("W_ID" = w_id)
		warehouseInfo = warehouse.columns("W_NAME","W_STREET_1", "W_STREET_2", "W_CITY", "W_STATE", "W_ZIP")[0]

		# getDistrict
		districts = districtQuery.filter("D_W_ID" = w_id, "D_ID" = d_id)
		districtInfo = districts.columns("D_NAME", "D_STREET_1", "D_STREET_2", "D_CITY", "D_STATE", "D_ZIP")[0]

		# updateWarehouseBalance
		warehouses = warehouseQuery.filter("W_ID" = w_id)
		for record in warehouses:
			key, cols = record
			cols["W_YTD"] += h_amount
			self.conn[sID]["WAREHOUSE"].put(key, cols)

		# updateDistrictBalance
		districts = districtQuery.filter("W_ID" = w_id, "D_ID" = d_id)
		for record in districts:
			key, cols = record
			cols["D_YTD"] += h_amount
			self.conn[sID]["DISTRICT"].put(key, cols)

		# Customer Credit Information
		customers = customerQuery.filter("C_W_ID" = c_w_id, "C_D_ID" = c_d_id, "C_ID" = c_id)
		
		if customer["C_CREDIT"] == constants.BAD_CREDIT:
			newData = " ".join(map(str, [c_id, c_d_id, c_w_id, d_id, w_id, h_amount]))
			c_data = (newData + "|" + c_data)
			if len(c_data) > constants.MAX_C_DATA: c_data =	c_data[:constants.MAX_C_DATA]

			# updateBCCustomer
			for record in customers:
				key, cols = record
				cols["C_BALANCE"] = c_balance
				cols["C_YTD_PAYMENT"] = c_ytd_payment
				cols["C_PAYMENT_CNT"] = c_payment_cnt
				cols["C_DATA"] = c_data
				self.conn[sID]["CUSTOMER"].put(key, cols)
		else:
			c_data = ""

			# updateGCCustomer
			for record in customers:
				key, cols = record
				cols["C_BALANCE"] = c_balance
				cols["C_YTD_PAYMENT"] = c_ytd_payment
				cols["C_PAYMENT_CNT"] = c_payment_cnt
				self.conn[sID]["CUSTOMER"].put(key, cols)

		# Concatenate w_name, four space, d_name
		h_data = "%s    %s" % (warehouseInfo["W_NAME"], districtInfo["D_NAME"])

		# Create the history record
		# insertHistory
		key = self.conn[sid]["HISTORY"].genuid()
		cols = ("H_C_ID": c_id, "H_C_D_ID": c_d_id, "H_C_W_ID": c_w_id, "H_D_ID":
						d_id, "H_W_ID": w_id, "H_DATE": h_date, "H_AMOUNT":
						h_amount, "H_DATA": h_data)
		self.conn[sID]["HISTORY"].put(key, cols)

		## Commit!
		# TODO Commit
		#for tab in self.conn[sID].keys():
		#	self.conn[sID][tab].sync()

		# TPC-C 2.5.3.3: Must display the following fields:
		# W_ID, D_ID, C_ID, C_D_ID, C_W_ID, W_STREET_1, W_STREET_2, W_CITY,
		# W_STATE, W_ZIP, D_STREET_1, D_STREET_2, D_CITY, D_STATE, D_ZIP,
		# C_FIRST, C_MIDDLE, C_LAST, C_STREET_1, C_STREET_2, C_CITY, C_STATE,
		# C_ZIP, C_PHONE, C_SINCE, C_CREDIT, C_CREDIT_LIM, C_DISCOUNT,
		# C_BALANCE, the first 200 characters of C_DATA (only if C_CREDIT =
		# "BC"), H_AMMOUNT, and H_DATE.

		# Hand back all the warehouse, district, and customer data
		return [ warehouseInfo, districtInfo, customerInfo ]

	def doStockLevel(self, params):
		"""Execute STOCK_LEVEL Transaction
		Parameters Dict:
			w_id
			d_id
			threshold
		"""
		w_id = params["w_id"]
		d_id = params["d_id"]
		threshold = params["threshold"]

		try:
			districtQuery  = self.conn["DISTRICT"].query
			orderLineQuery = self.conn["ORDER_LINE"].query
			stockQuery     = self.conn["STOCK"].query
		except KeyError, err:
			sys.stderr.out("%s(%s): server ID does not exist or is offline\n" %(KeyError, err))
			sys.exit(1)

		# getOId
		districts = districtQuery.filter("D_W_ID" = w_id, "D_ID" = d_id)
		try:
			o_id = districts.columns("D_NEXT_O_ID")[0]["D_NEXT_O_ID"]
		except (KeyError, IndexError), err:
			sys.stderr.write("%s" % err)
			sys.exit(1)

		# getStockCount
		orders = orderLineQuery.filter("OL_W_ID" = w_id, "OL_D_ID" = d_id,
						"OL_O_ID" < o_id, "OL_O_ID" >= (o_id-20))
		ol_i_ids = orders.columns("OL_I_ID")

		cnt = 0
		for i_id in set(ol_i_ids):
			stocks = stockQuery.filter("S_W_ID" = w_id, "S_I_ID" = i_id, "S_QUANTITY" <	threshold)
			if len(stocks) > 0:
				cnt += 1

		## Commit!
		# TODO Commit
		#for tab in self.conn[sID].keys():
		#	self.conn[sID][tab].sync()

		return cnt

## CLASS
