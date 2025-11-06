from store.models import Product, Profile

class Cart():
	def __init__(self, request):
		self.session = request.session
		# Get request
		self.request = request
		# Get the current session key if it exists
		cart = self.session.get('session_key')

		# If the user is new, no session key!  Create one!
		if 'session_key' not in request.session:
			cart = self.session['session_key'] = {}


		# Make sure cart is available on all pages of site
		self.cart = cart

	def db_add(self, product, quantity):
		product_id = str(product)
		product_qty = str(quantity)
		# Logic
		if product_id in self.cart:
			pass
		else:
			#self.cart[product_id] = {'price': str(product.price)}
			self.cart[product_id] = int(product_qty)

		self.session.modified = True

		# Deal with logged in user
		if self.request.user.is_authenticated:
			# Get the current user profile
			current_user = Profile.objects.filter(user__id=self.request.user.id)
			# Convert {'3':1, '2':4} to {"3":1, "2":4}
			carty = str(self.cart)
			carty = carty.replace("\'", "\"")
			# Save carty to the Profile Model
			current_user.update(old_cart=str(carty))


	def add(self, product, quantity, size):
		product_id = str(product.id)
		product_qty = int(quantity)

		# Logic
		if product_id in self.cart:
			# Update quantity and size if product already exists
			self.cart[product_id]['quantity'] += product_qty
			self.cart[product_id]['size'] = size
		else:
			# Store as dict instead of plain int
			self.cart[product_id] = {
				'quantity': product_qty,
				'size': size,
			}

		self.session.modified = True

		# Deal with logged in user
		if self.request.user.is_authenticated:
			current_user = Profile.objects.filter(user__id=self.request.user.id)
			carty = str(self.cart).replace("\'", "\"")
			current_user.update(old_cart=str(carty))


	def cart_total(self):
		print("DEBUG CART:", self.cart)
		product_ids = self.cart.keys()
		products = Product.objects.filter(id__in=product_ids)
		total = 0
		
		for key, value in self.cart.items():
			key = int(key)
			qty = value['quantity']   # ✅ extract quantity
			for product in products:
				if product.id == key:
					if product.is_sale:
						total += product.sale_price * qty
					else:
						total += product.price * qty
		return total




	def __len__(self):
		return len(self.cart)

	def get_prods(self):
		# Get ids from cart
		product_ids = self.cart.keys()
		# Use ids to lookup products in database model
		products = Product.objects.filter(id__in=product_ids)

		# Return those looked up products
		return products

	def get_quants(self):
		return self.cart


	def update(self, product, quantity, size=None):
		product_id = str(product)
		product_qty = int(quantity)

		if product_id in self.cart:
			if isinstance(self.cart[product_id], dict):
				self.cart[product_id]['quantity'] = product_qty
				# ✅ always update size, even if it's the same or empty
				self.cart[product_id]['size'] = size
			else:
				# Normalize old data
				self.cart[product_id] = {'quantity': product_qty, 'size': size}
		else:
			self.cart[product_id] = {'quantity': product_qty, 'size': size}

		self.session.modified = True


	def delete(self, product):
		product_id = str(product)
		# Delete from dictionary/cart
		if product_id in self.cart:
			del self.cart[product_id]

		self.session.modified = True

		# Deal with logged in user
		if self.request.user.is_authenticated:
			# Get the current user profile
			current_user = Profile.objects.filter(user__id=self.request.user.id)
			# Convert {'3':1, '2':4} to {"3":1, "2":4}
			carty = str(self.cart)
			carty = carty.replace("\'", "\"")
			# Save carty to the Profile Model
			current_user.update(old_cart=str(carty))