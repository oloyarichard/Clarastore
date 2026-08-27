import 'product.dart';

class CartItem {
  final int id;
  final Product product;
  final int quantity;
  final double subtotal;

  CartItem({required this.id, required this.product, required this.quantity, required this.subtotal});

  factory CartItem.fromJson(Map<String, dynamic> json) => CartItem(
        id: json['id'],
        product: Product.fromJson(json['product']),
        quantity: json['quantity'],
        subtotal: double.tryParse(json['subtotal'].toString()) ?? 0,
      );
}

class Cart {
  final List<CartItem> items;
  final double total;
  final int count;

  Cart({required this.items, required this.total, required this.count});

  factory Cart.fromJson(Map<String, dynamic> json) => Cart(
        items: (json['items'] as List).map((e) => CartItem.fromJson(e)).toList(),
        total: double.tryParse(json['total'].toString()) ?? 0,
        count: json['count'] ?? 0,
      );

  factory Cart.empty() => Cart(items: [], total: 0, count: 0);
}
