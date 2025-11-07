from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from store.models import Product, Profile
import datetime
from django.core.mail import get_connection, send_mail
from django.conf import settings
import ssl, certifi

# Import Some Paypal Stuff
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
import uuid # unique user id for duplictate orders

def orders(request, pk):
	if request.user.is_authenticated and request.user.is_superuser:
		# Get the order
		order = Order.objects.get(id=pk)
		# Get the order items
		items = OrderItem.objects.filter(order=pk)

		if request.POST:
			status = request.POST['shipping_status']
			# Check if true or false
			if status == "true":
				# Get the order
				order = Order.objects.filter(id=pk)
				# Update the status
				now = datetime.datetime.now()
				order.update(shipped=True, date_shipped=now)
			else:
				# Get the order
				order = Order.objects.filter(id=pk)
				# Update the status
				order.update(shipped=False)
			messages.success(request, "Shipping Status Updated")
			return redirect('home')


		return render(request, 'payment/orders.html', {"order":order, "items":items})




	else:
		messages.success(request, "Access Denied")
		return redirect('home')



def not_shipped_dash(request):
	if request.user.is_authenticated and request.user.is_superuser:
		orders = Order.objects.filter(shipped=False)
		if request.POST:
			status = request.POST['shipping_status']
			num = request.POST['num']
			# Get the order
			order = Order.objects.filter(id=num)
			# grab Date and time
			now = datetime.datetime.now()
			# update order
			order.update(shipped=True, date_shipped=now)
			# redirect
			messages.success(request, "Shipping Status Updated")
			return redirect('home')

		return render(request, "payment/not_shipped_dash.html", {"orders":orders})
	else:
		messages.success(request, "Access Denied")
		return redirect('home')

def shipped_dash(request):
	if request.user.is_authenticated and request.user.is_superuser:
		orders = Order.objects.filter(shipped=True)
		if request.POST:
			status = request.POST['shipping_status']
			num = request.POST['num']
			# grab the order
			order = Order.objects.filter(id=num)
			# grab Date and time
			now = datetime.datetime.now()
			# update order
			order.update(shipped=False)
			# redirect
			messages.success(request, "Shipping Status Updated")
			return redirect('home')


		return render(request, "payment/shipped_dash.html", {"orders":orders})
	else:
		messages.success(request, "Access Denied")
		return redirect('home')

def process_order(request):
	if request.POST:
		# Get the cart
		cart = Cart(request)
		cart_products = cart.get_prods
		quantities = cart.get_quants
		totals = cart.cart_total()

		# Get Billing Info from the last page
		payment_form = PaymentForm(request.POST or None)
		if payment_form.is_valid():
			payment_data = payment_form.cleaned_data
		else:
			messages.error(request, "Invalid payment details")
			return redirect("checkout")

		# Get Shipping Session Data
		my_shipping = request.session.get('my_shipping')

		# Gather Order Info
		full_name = my_shipping['shipping_full_name']
		email = my_shipping['shipping_email']

		# Create Shipping Address from session info
		shipping_address = f"{my_shipping['shipping_address']}\n{my_shipping['shipping_country']}\n{my_shipping['shipping_county']}\n{my_shipping['shipping_constituency']}"

		shipping_data = {
		"Full Name": my_shipping.get("shipping_full_name"),
		"Email": my_shipping.get("shipping_email"),
		"Address": my_shipping.get("shipping_address"),
		"Country": my_shipping.get("shipping_country"),
		"County": my_shipping.get("shipping_county"),
		"Constituency": my_shipping.get("shipping_constituency"),
	}

		amount_paid = totals

		# Create an Order
		if request.user.is_authenticated:
			# logged in
			user = request.user
			# Create Order
			create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
			create_order.save()

			# Add order items
			
			# Get the order ID
			order_id = create_order.pk
			
			# Get product Info
			for product in cart_products():
				# Get product ID
				product_id = product.id
				# Get product price
				if product.is_sale:
					price = product.sale_price
				else:
					price = product.price

				# Get quantity + size
			for key, value in quantities().items():
				if int(key) == product.id:
					qty = value['quantity']   # ✅ extract integer
					size = value['size']      # ✅ extract shoe size

					# Create order item
					create_order_item = OrderItem(
						order_id=order_id,
						product_id=product_id,
						user=user,
						quantity=qty,          # ✅ now just number
						size=size,             # ✅ store size
						price=price
					)
					create_order_item.save()

			# Prepare email content
			subject = "New Order Received"
			message = f"""
			You have a new order!

			Order ID: {order_id}
			"""

			# Add Shipping Information
			message += "\nShipping Information:\n"
			for field, value in shipping_data.items():
				message += f"{field}: {value}\n"

			# Add Contact (PaymentForm) Information
			message += "\nContact Information:\n"
			for field, value in payment_data.items():
				message += f"{field.replace('_', ' ').title()}: {value}\n"

			# Add Order Summary
			message += "\nOrder Summary:\n"
			for product in cart_products():
				for key, value in quantities().items():
					if int(key) == product.id:
						price = product.sale_price if product.is_sale else product.price
						message += f"- {product.name} (x{value}) @ {price} each\n"

			message += "\nThank you!"

			email_connection = get_connection(
				backend=settings.EMAIL_BACKEND,
				host=settings.EMAIL_HOST,
				port=settings.EMAIL_PORT,
				username=settings.EMAIL_HOST_USER,
				password=settings.EMAIL_HOST_PASSWORD,
				use_tls=settings.EMAIL_USE_TLS,
				ssl_context=ssl.create_default_context(cafile=certifi.where())
			)

			# Send email to admin
			send_mail(
				subject,
				message,
				settings.DEFAULT_FROM_EMAIL,
				["lilflame694@gmail.com"],
				fail_silently=False,
				connection=email_connection
			)

			# Send confirmation email to customer
			customer_subject = "Order Confirmation"
			customer_message = f"""
			Hi {full_name},

			Thank you for your order!

			Your order (ID: {order_id}) has been received and will be processed.
			We will deliver it within 2 days.

			Order Summary:
			"""

			for product in cart_products():
				for key, value in quantities().items():
					if int(key) == product.id:
						price = product.sale_price if product.is_sale else product.price
						customer_message += f"- {product.name} (x{value}) @ {price} each\n"

			customer_message += "\nThank you for shopping with us!"

			# Send confirmation email to customer
			send_mail(
				customer_subject,
				customer_message,
				settings.DEFAULT_FROM_EMAIL,
				[email],  # send to the customer
				fail_silently=False,
				connection=email_connection,
			)

			# Delete our cart
			for key in list(request.session.keys()):
				if key == "session_key":
					# Delete the key
					del request.session[key]

			# Delete Cart from Database (old_cart field)
			current_user = Profile.objects.filter(user__id=request.user.id)
			# Delete shopping cart in database (old_cart field)
			current_user.update(old_cart="")

			messages.success(request, "Order Placed!")
			return redirect('home')

		else:
			# not logged in
			# Create Order
			create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
			create_order.save()

			# Add order items
			
			# Get the order ID
			order_id = create_order.pk
			
			# Get product Info
			for product in cart_products():
				# Get product ID
				product_id = product.id
				# Get product price
				if product.is_sale:
					price = product.sale_price
				else:
					price = product.price

				# Get quantity + size
				for key, value in quantities().items():
					if int(key) == product.id:
						qty = value['quantity']   # ✅ extract integer
						size = value['size']      # ✅ extract shoe size

						# Create order item
						create_order_item = OrderItem(
							order_id=order_id,
							product_id=product_id,
							quantity=qty,          # ✅ now just number
							size=size,             # ✅ store size
							price=price
						)
						create_order_item.save()

			# Delete our cart
			for key in list(request.session.keys()):
				if key == "session_key":
					# Delete the key
					del request.session[key]

			messages.success(request, "Order Placed!")
			return redirect('home')

	else:
		messages.success(request, "Access Denied")
		return redirect('home')

def billing_info(request):
	if request.POST:
		# Get the cart
		cart = Cart(request)
		cart_products = cart.get_prods
		quantities = cart.get_quants
		totals = cart.cart_total()

		# Create a session with Shipping Info
		my_shipping = request.POST
		request.session['my_shipping'] = my_shipping

		# Get the host
		host = request.get_host()
		# Create Paypal Form Dictionary
		paypal_dict = {
			'business': settings.PAYPAL_RECEIVER_EMAIL,
			'amount': totals,
			'item_name': 'Book Order',
			'no_shipping': '2',
			'invoice': str(uuid.uuid4()),
			'currency_code': 'USD', # EUR for Euros
			'notify_url': 'https://{}{}'.format(host, reverse("paypal-ipn")),
			'return_url': 'https://{}{}'.format(host, reverse("payment_success")),
			'cancel_return': 'https://{}{}'.format(host, reverse("payment_failed")),
		}

		# Create acutal paypal button
		paypal_form = PayPalPaymentsForm(initial=paypal_dict)


		# Check to see if user is logged in
		if request.user.is_authenticated:
			# Get The Billing Form
			billing_form = PaymentForm()
			return render(request, "payment/billing_info.html", {"paypal_form":paypal_form, "cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":request.POST, "billing_form":billing_form})

		else:
			# Not logged in
			# Get The Billing Form
			billing_form = PaymentForm()
			return render(request, "payment/billing_info.html", {"paypal_form":paypal_form, "cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":request.POST, "billing_form":billing_form})


		
		shipping_form = request.POST
		return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})	
	else:
		messages.success(request, "Access Denied")
		return redirect('home')


def checkout(request):
	# Get the cart
	cart = Cart(request)
	cart_products = cart.get_prods
	quantities = cart.get_quants
	totals = cart.cart_total()

	if request.user.is_authenticated:
		# Checkout as logged in user
		# Shipping User
		shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
		# Shipping Form
		shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
		return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form })
	else:
		# Checkout as guest
		shipping_form = ShippingForm(request.POST or None)
		return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})

	

def payment_success(request):
	return render(request, "payment/payment_success.html", {})


def payment_failed(request):
	return render(request, "payment/payment_failed.html", {})