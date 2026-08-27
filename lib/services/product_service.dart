import '../core/api_client.dart';
import '../models/product.dart';

class ProductService {
  final _dio = ApiClient.instance.dio;

  Future<List<Product>> listProducts({String? category, String? search}) async {
    final resp = await _dio.get('/products/', queryParameters: {
      if (category != null && category.isNotEmpty) 'category': category,
      if (search != null && search.isNotEmpty) 'search': search,
    });
    final results = resp.data is Map && resp.data['results'] != null ? resp.data['results'] : resp.data;
    return (results as List).map((e) => Product.fromJson(e)).toList();
  }

  Future<Product> getProduct(int id) async {
    final resp = await _dio.get('/products/$id/');
    return Product.fromJson(resp.data);
  }
}
