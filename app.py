from flask import Flask,jsonify,request
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from marshmallow import fields,validate, ValidationError 
from sqlalchemy.orm import relationship, Session
from sqlalchemy import text
from flask_cors import CORS

# (myvenvalch)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql+mysqlconnector://root:password@localhost/e_commerce_db'
db = SQLAlchemy(app)
ma = Marshmallow(app)
# giving acsess to our db from a website 'CORS'
CORS(app)

#------------------------------------------------------------------------------------------------------
#                                   SQL Table Classes
class Customer(db.Model):
  __tablename__ = "Customers"
  id = db.Column(db.Integer,primary_key=True)
  name = db.Column(db.String(255),nullable=False) 
  email = db.Column(db.String(320))
  phone = db.Column(db.String(15))
  orders = db.relationship("Order", backref="customer")
  carts = relationship('Cart', back_populates='customer')

# many to many relationship
order_product = db.Table("Order_Product",
  db.Column("order_id",db.Integer,db.ForeignKey('Orders.id'),primary_key=True),
  db.Column("product_id",db.Integer,db.ForeignKey("Products.id"),primary_key=True),
  db.Column("quantity",db.Integer,nullable=False)
  )

class Order(db.Model):
  __tablename__ = "Orders"
  id = db.Column(db.Integer,primary_key=True)
  order_date = db.Column(db.DATETIME,server_default=text('CURRENT_TIMESTAMP'))
  delivery_date = db.Column(db.DATETIME)
  customer_id = db.Column(db.Integer,db.ForeignKey("Customers.id"))
  products = relationship("Product", secondary=order_product, back_populates="orders")
  

class Product(db.Model):
  __tablename__ = "Products"
  id = db.Column(db.Integer,primary_key=True)
  name = db.Column(db.String(255),nullable=False) 
  price = db.Column(db.Float, nullable=False)
  quantity = db.Column(db.Integer,nullable=False)
  description = db.Column(db.TEXT(65535),nullable=False)
  orders = relationship("Order", secondary=order_product, back_populates="products")

# one to one relationship
class CustomerAccount(db.Model):
  __tablename__ = "Customer_Accounts"
  id = db.Column(db.Integer,primary_key=True)
  username = db.Column(db.String(255),unique=True, nullable=False)
  password = db.Column(db.String(255),nullable=False)
  customer_id = db.Column(db.Integer,db.ForeignKey("Customers.id"))
  customer = db.relationship("Customer", backref="Customer_account", uselist=False)

class Cart(db.Model):
  __tablename__ = 'Carts'
  id = db.Column(db.Integer, primary_key=True)
  customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'), nullable=False)
  items = relationship('CartItem', back_populates='cart')
  customer = relationship('Customer', back_populates='carts')

class CartItem(db.Model):
  __tablename__ = 'Cart_Items'
  id = db.Column(db.Integer, primary_key=True)
  cart_id = db.Column(db.Integer, db.ForeignKey('Carts.id'), nullable=False)
  product_id = db.Column(db.Integer, db.ForeignKey('Products.id'), nullable=False)
  quantity = db.Column(db.Integer, nullable=False)
  cart = relationship('Cart', back_populates='items')
  product = relationship('Product')
#------------------------------------------------------------------------------------------------------
#                                        Schema Tables

class CustomerSchema(ma.Schema):
  name = fields.String(required=True)
  email=fields.String(required=True)
  phone=fields.String(required=True)
  order = fields.Integer(required=False)
  class Meta:
    fields = ("name","email","phone","order","id")

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

class OrderSchema(ma.Schema):
  order_date = fields.DateTime(required=False)
  delivery_date = fields.DateTime(required=False)
  customer_id=fields.Integer(required=True)
  products = fields.List(fields.Nested(lambda: ProductQuantitySchema()), required=True)
  class Meta:
    fields = ('order_date','delivery_date',"customer_id","products","id")

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

class ProductQuantitySchema(ma.Schema):
    product_id = fields.Integer(required=True)
    quantity = fields.Integer(required=True)

class ProductSchema(ma.Schema):
  name = fields.String(required=True, validate=validate.Length(min=1))
  price=fields.Float(required=True, validate=validate.Range(min=0))
  quantity=fields.Integer(required=True,validate=validate.Range())
  description = fields.String(required=True,validate=validate.Length(min=1))
  class Meta:
    fields = ("name","price","quantity","description","id")

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

class OrderedSchema(ma.Schema):
  customer_id = fields.Integer(required=True)
  delivery_date = fields.Date(required=True)
  product_id = fields.Integer(required=True)
  products = fields.List(fields.String(),required=True)
    
  class Meta:
    fields = ("customer_id","order_date",'delivery_date' ,"products","id")

ordered_schema = OrderedSchema()
ordered_many_schema = OrderedSchema(many=True)

class CustomerAccountSchema(ma.Schema):
  username = fields.String(required=True)
  password=fields.String(required=True)
  customer_id=fields.Integer(required=True)
  class Meta:
    fields = ("username","password","customer_id","id")

customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True)

class CartItemSchema(ma.Schema):
    product_id = fields.Integer(required=True)
    quantity = fields.Integer(required=True)

class CartSchema(ma.Schema):
    customer_id = fields.Integer(required=True)
    items = fields.List(fields.Nested(CartItemSchema), required=True)
    
    class Meta:
        fields = ('customer_id', 'items', 'id')

cart_schema = CartSchema()


# Initializing Database
with app.app_context():
  db.create_all()

#----------------------------------------------------------------------------
#                               Home Page
@app.route('/')
def home():
    return 'Welcome to our e-commerce app!'

#---------------------------------------------------------------------------------------------
#                                   Customer Functions For end routes
# getting all the customers in the database
@app.route("/customers",methods=["GET"])
def get_customer():
  customers = Customer.query.all()
  return customers_schema.jsonify(customers)

@app.route("/customers/<int:id>",methods=["GET"])
def get_customer_by_id(id):
  customer = Customer.query.get_or_404(id)
  if customer:
    return customer_schema.jsonify(customer)
  else:
    return jsonify({"message": "Customer Not Found"}),404
  
# adding a customer to the database
@app.route("/customers",methods=["POST"])
def create_customer():
  try:
    customer_data = customer_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages), 400
  new_customer = Customer(name=customer_data["name"], email=customer_data["email"], phone=customer_data["phone"])
  db.session.add(new_customer)
  db.session.commit()
  return jsonify({"message": "New Customer Added Successfully!"}), 201

# PUT MEANS UPDATE
@app.route("/customers/<int:id>",methods=["PUT"])
def update_customer(id):
  customer = Customer.query.get_or_404(id)
  try:
    # Validates and deserialize the input
    customer_data = customer_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages), 400
  
  customer.name = customer_data['name']
  customer.email = customer_data['email']
  customer.phone = customer_data['phone']
  db.session.commit()
  return jsonify({"message": "Customer details updated successfully"}), 200

# deleting the customer of your choice the <int:id> is to target the id of the customer to delete
@app.route("/customers/<int:id>",methods=["DELETE"])
def delete_customer(id):
  customer = Customer.query.get_or_404(id)
  db.session.delete(customer)
  db.session.commit()
  return jsonify({"message": "Customer removed successfully"}), 200

#-------------------------------------------------------------------------------------------------------
#                                          Order/Cart Functions For end routes
@app.route("/orders/status/<id>",methods=["GET"])
def order_status(id):
  order= Order.query.get_or_404(id)
  order_data = {
    'order_id': order.id,
    'order_date':order.order_date,
    'delivery_date':order.delivery_date,
    'customer':{
      'customer_id':order.customer.id,
      'name':order.customer.name,
      'email':order.customer.email,
      'phone':order.customer.phone
      }}
  return jsonify(order_data)

@app.route("/orders",methods=['GET'])
def get_orders():
  orders = Order.query.all()
  return ordered_many_schema.jsonify(orders)

@app.route("/order/<int:id>",methods=["GET"])
def get_one_order(id):
  order = OrderedSchema.query.get_or_404(id)
  if order:
    return order_schema.jsonify(order)
  else:
    return jsonify({"message": "Customer Not Found"}),404

@app.route("/orders/by_customer_id/<int:id>",methods=["GET"])
def get_order_by_customer_id(id):
  customer_order = Order.query.filter_by(customer_id=id).all()
  if customer_order:
    return ordered_many_schema.jsonify(customer_order)
  else:
    return jsonify({"message": "Not Found"})

@app.route("/orders/<id>", methods=["GET"])
def get_order_id(id):
    order = Order.query.get_or_404(id)
    order_data = {
        'order_id': order.id,
        'order_date': order.order_date,
        'delivery_date': order.delivery_date,
        'customer': {
            'customer_id': order.customer.id,
            'name': order.customer.name,
            'email': order.customer.email,
            'phone': order.customer.phone
        },
        'products': []
    }
    results = db.session.query(
        Product.id,
        Product.name,
        Product.price,
        order_product.c.quantity
    ).join(order_product, Product.id == order_product.c.product_id).filter(order_product.c.order_id == id).all()
    for product_id, name, price, quantity in results:
        product_data = {
            'product_id': product_id,
            'name': name,
            'price': price,
            'quantity': quantity
        }
        order_data['products'].append(product_data)
    return jsonify(order_data)
 
@app.route("/orders/<id>", methods=["PUT"])
def update_order(id):
    order = Order.query.get_or_404(id)
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    order.customer_id = order_data.get('customer_id', order.customer_id)
    db.session.execute(order_product.delete().where(order_product.c.order_id == id))
    for product_data in order_data["products"]:
        product_id = product_data["product_id"]
        quantity = product_data["quantity"]
        product = Product.query.get_or_404(product_id)
        db.session.execute(order_product.insert().values(order_id=order.id, product_id=product.id, quantity=quantity))
    db.session.commit()
    return jsonify({"message": "Order Updated Successfully!"}), 200

@app.route("/orders", methods=["POST"])
def create_order():
  try:
      order_data = order_schema.load(request.json)
  except ValidationError as err:
      return jsonify(err.messages), 400
  new_order = Order(customer_id=order_data["customer_id"])
  db.session.add(new_order)
  db.session.commit()
  for product_data in order_data["products"]:
      product_id = product_data["product_id"]
      quantity = product_data["quantity"]
      product = Product.query.get_or_404(product_id)
      db.session.execute(order_product.insert().values(order_id=new_order.id, product_id=product.id, quantity=quantity))
      
  db.session.commit()

  return jsonify({"message": "New Order Added Successfully!"}), 201

@app.route("/orders/<int:id>",methods=["DELETE"])
def delete_order(id):
  order = Order.query.get_or_404(id)
  db.session.delete(order)
  db.session.commit()
  return jsonify({"message": "Order removed successfully"}), 200

#----------------------------------------------------------------------------
#                              Product Functions For end routes   

@app.route("/products",methods=["GET"])
def get_product():
  products = Product.query.all()
  return products_schema.jsonify(products)

@app.route("/products/<int:id>",methods=["GET"])
def get_product_by_id(id):
  product = Product.query.get_or_404(id)
  if product:
    return product_schema.jsonify(product)
  else:
    return jsonify({"message": "Customer Not Found"}),404


@app.route("/products/<int:id>",methods=["PUT"])
def update_product(id):
  product = Product.query.get_or_404(id)
  try:
    # Validates and deserialize the input
    product_data = product_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages), 400
  
  product.name = product_data['name']
  product.price = product_data['price']
  product.quantity = product_data['quantity']
  product.description = product_data['description']
  db.session.commit()
  return jsonify({"message": "Product details updated successfully"}), 200


@app.route("/products",methods=["POST"])
def create_product():
  try:
    product_data = product_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages),400
  
  new_product = Product(name=product_data['name'],price=product_data['price'],quantity=product_data['quantity'],description=product_data['description'])
  db.session.add(new_product)
  db.session.commit()
  return jsonify({"message": "Product has been added successfully"}), 201


@app.route("/products/<int:id>",methods=["DELETE"])
def delete_product(id):
  product = Product.query.get_or_404(id)
  db.session.delete(product)
  db.session.commit()
  return jsonify({"message": "Product removed successfully"}), 200

#------------------------------------------------------------------------
#                                 Customer Accounts Functions For end routes

@app.route("/customer_accounts",methods=["GET"])
def get_customer_account():
  customer_accounts = CustomerAccount.query.all()
  return customer_accounts_schema.jsonify(customer_accounts)


@app.route("/customer_accounts/<int:id>",methods=["GET"])
def get_customer_account_by_id(id):
  customer_account = CustomerAccount.query.get_or_404(id)
  if customer_account:
    return customer_account_schema.jsonify(customer_account)
  else:
    return jsonify({"message": "Customer Not Found"}),404

@app.route('/customer_accounts/by_customer_id/<int:id>',methods=["GET"])
def get_customer_account_by_customer_id(id):
  customer_account = CustomerAccount.query.filter_by(customer_id=id).first()
  if customer_account:
    return customer_account_schema.jsonify(customer_account)
  else:
    return jsonify({"message": "Not Found"})
  
@app.route('/customer_accounts/by_customer_username/<string:username>',methods=["GET"])
def get_customer_account_by_customer_username(username):
  customer_account = CustomerAccount.query.filter_by(username=username).first()
  if customer_account:
    return customer_account_schema.jsonify(customer_account)
  else:
    return jsonify({"message": "Not Found"})

@app.route("/customer_accounts/<int:id>",methods=["PUT"])
def update_customer_account(id):
  customer_account = CustomerAccount.query.get_or_404(id)
  try:
    # Validates and deserialize the input
    customer_account_data = customer_account_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages), 400
  
  customer_account.username = customer_account_data['username']
  customer_account.password = customer_account_data['password']
  customer_account.customer_id = customer_account_data['customer_id']
  db.session.commit()
  return jsonify({"message": "Customer Account details has been updated successfully"}), 200


@app.route("/customer_accounts",methods=["POST"])
def create_customer_account():
  try:
    customer_account_data = customer_account_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages),400
  
  new_customer_account = CustomerAccount(username=customer_account_data['username'],password=customer_account_data['password'],customer_id=customer_account_data['customer_id'])
  db.session.add(new_customer_account)
  db.session.commit()
  return jsonify({"message": "New Customer Account has created successfully"}),201


@app.route("/customer_accounts/<int:id>",methods=["DELETE"])
def delete_customer_account(id):
  customer_account = CustomerAccount.query.get_or_404(id)
  db.session.delete(customer_account)
  db.session.commit()
  return jsonify({"message": "Customer Account has been removed successfully"}), 200

#-----------------------------------------------------------------------
#                             Cart functions for end routes

@app.route("/cart", methods=["POST"])
def add_to_cart():
  try:
      cart_data = cart_schema.load(request.json)
  except ValidationError as err:
      return jsonify(err.messages), 400

  cart = Cart(customer_id=cart_data["customer_id"])
  db.session.add(cart)
  db.session.commit()
  for item_data in cart_data["items"]:
      product_id = item_data["product_id"]
      quantity = item_data["quantity"]
      product = Product.query.get_or_404(product_id)
      
      cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
      db.session.add(cart_item)
  db.session.commit()
  return jsonify({"message": "Products added successfully"}),201

@app.route("/cart/<id>", methods=["GET"])
def get_cart(id):
  cart = Cart.query.get_or_404(id)
  cart_data = {
      'cart_id': cart.id,
      'customer_id': cart.customer_id,
      'items': []
  }
  for item in cart.items:
      item_data = {
          'product_id': item.product.id,
          'name': item.product.name,
          'price': item.product.price,
          'quantity': item.quantity
      }
      cart_data['items'].append(item_data)

  return jsonify(cart_data)

@app.route("/carts", methods=["GET"])
def get_all_carts():
    carts = Cart.query.all()
    all_carts = []
    for cart in carts:
        cart_data = {
            'cart_id': cart.id,
            'customer_id': cart.customer_id,
            'items': []
        }
        for item in cart.items:
            item_data = {
                'product_id': item.product.id,
                'name': item.product.name,
                'price': item.product.price,
                'quantity': item.quantity
            }
            cart_data['items'].append(item_data)
        all_carts.append(cart_data)

    return jsonify(all_carts)
  
@app.route("/carts_by_customer", methods=["GET"])
def get_carts_by_customer():
  carts = Cart.query.all()
  customers_carts = {}
  for cart in carts:
    customer_id = cart.customer_id
    if customer_id not in customers_carts:
      customers_carts[customer_id] = []
    cart_data = {
      'cart_id': cart.id,
      'customer_id': cart.customer_id,
      'items': []
  }
    for item in cart.items:
      item_data = {
      'product_id': item.product.id,
      'name': item.product.name,
      'price': item.product.price,
      'quantity': item.quantity
    }
    cart_data['items'].append(item_data)  
    customers_carts[customer_id].append(cart_data)
  return jsonify(customers_carts)
  
@app.route("/carts_by_customer/<customer_id>", methods=["GET"])
def get_carts_by_customer_id(customer_id):
  carts = Cart.query.filter_by(customer_id=customer_id).all()
  customer_carts = []
  for cart in carts:
      cart_data = {
        'cart_id': cart.id,
        'customer_id': customer_id,
        'items': []
      }
      for item in cart.items:
          item_data = {
            'product_id': item.product.id,
            'name': item.product.name,
            'price': item.product.price,
            'quantity': item.quantity
          }
          cart_data['items'].append(item_data)
      customer_carts.append(cart_data)
  return jsonify(customer_carts)

@app.route("/cart/<int:id>", methods=["DELETE"])
def delete_cart(id):
    cart = Cart.query.get_or_404(id)
    cart_items = CartItem.query.get_or_404(id)
    db.session.delete(cart_items)
    db.session.delete(cart)
    db.session.commit()
    return jsonify({"message": "Cart deleted successfully"}), 200
  
@app.route("/cart/<int:cart_id>/item/<int:item_id>", methods=["DELETE"])
def delete_cart_item(cart_id, item_id):
    item = CartItem.query.filter_by(cart_id=cart_id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted successfully"}), 200
  
@app.route("/cart/<int:cart_id>", methods=["PUT"])
def update_cart(cart_id):
    cart = Cart.query.get_or_404(cart_id)
    data = request.get_json()
    
    for item_data in data.get('items', []):
        item = CartItem.query.filter_by(cart_id=cart_id, product_id=item_data['product_id']).first()
        if item:
            item.quantity = item_data['quantity']
    
    db.session.commit()
    return jsonify({"message": "Cart updated successfully"}), 200
  
  
#------------------------------------------------------------------------
#                         advanced lookups

# possible i need to change these

@app.route("/customers/by-email",methods=["GET"])
def get_customer_by_email():
  email = request.args.get('email')
  customer = Customer.query.filter_by(email=email).first()
  if customer:
    return customer_schema.jsonify(customer)
  else:
    return jsonify({"message": "Customer Not Found"}),404


@app.route("/products/by-name",methods=["GET"])
def get_product_by_name():
  name = request.args.get("name")
  # with filter i have to say the class for the Class.name==name
  product = Product.query.filter_by(name=name).first()
  if product:
    return product_schema.jsonify(product)
  else:
    return jsonify({"message": "Product Not Found"}),404


if __name__ == "__main__":
  app.run(debug=True)