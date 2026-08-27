class Product {
  final int id;
  final String name;
  final String description;
  final double price;
  final int stock;
  final String category;
  final String? imageUrl;
  final bool isInStock;

  Product({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.stock,
    required this.category,
    required this.isInStock,
    this.imageUrl,
  });

  factory Product.fromJson(Map<String, dynamic> json) => Product(
        id: json['id'],
        name: json['name'] ?? '',
        description: json['description'] ?? '',
        price: double.tryParse(json['price'].toString()) ?? 0,
        stock: json['stock'] ?? 0,
        category: json['category'] ?? '',
        isInStock: json['is_in_stock'] ?? (json['stock'] ?? 0) > 0,
        imageUrl: json['image'],
      );
}
