import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/product.dart';
import '../services/product_service.dart';

final productServiceProvider = Provider((ref) => ProductService());

class ProductFilter {
  final String? category;
  final String? search;
  const ProductFilter({this.category, this.search});

  @override
  bool operator ==(Object other) =>
      other is ProductFilter && other.category == category && other.search == search;
  @override
  int get hashCode => Object.hash(category, search);
}

final productListProvider =
    FutureProvider.family<List<Product>, ProductFilter>((ref, filter) async {
  return ref.read(productServiceProvider).listProducts(category: filter.category, search: filter.search);
});

final productDetailProvider = FutureProvider.family<Product, int>((ref, id) async {
  return ref.read(productServiceProvider).getProduct(id);
});
