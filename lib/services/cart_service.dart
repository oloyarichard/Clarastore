import '../core/api_client.dart';
import '../models/cart_item.dart';

class CartService {
  final _dio = ApiClient.instance.dio;

  Future<Cart> getCart() async {
    final resp = await _dio.get('/cart/');
    return Cart.fromJson(resp.data);
  }

  Future<void> addItem({required int productId, int quantity = 1}) async {
    await _dio.post('/cart/', data: {'product_id': productId, 'quantity': quantity});
  }

  Future<void> updateQuantity({required int itemId, required int quantity}) async {
    await _dio.patch('/cart/', data: {'item_id': itemId, 'quantity': quantity});
  }

  Future<void> removeItem(int itemId) async {
    await _dio.delete('/cart/', data: {'item_id': itemId});
  }

  Future<void> clearCart() async {
    await _dio.delete('/cart/');
  }

  /// Called right after login/signup so a guest's pre-signup cart (tracked
  /// by the session cookie) merges into their new account's cart. Reads
  /// the actual sessionid cookie rather than requiring the caller to
  /// supply one.
  Future<void> mergeGuestCartIfAny() async {
    final sessionKey = await ApiClient.instance.getGuestSessionId();
    if (sessionKey == null) return;
    await _dio.post('/cart/merge/', data: {'session_key': sessionKey});
  }
}
