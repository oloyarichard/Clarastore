import '../core/api_client.dart';
import '../models/order.dart';

class OrderService {
  final _dio = ApiClient.instance.dio;

  /// Checkout pays from the customer's wallet balance (per the payment
  /// decision: pay at checkout, wallet-based). Backend rejects this with
  /// a clear error if the balance is insufficient — surface that message
  /// so the UI can prompt a top-up.
  Future<Order> checkout({required int districtId}) async {
    final resp = await _dio.post('/orders/checkout/', data: {'district_id': districtId});
    return Order.fromJson(resp.data);
  }

  Future<List<Order>> listOrders() async {
    final resp = await _dio.get('/orders/');
    final results = resp.data is Map && resp.data['results'] != null ? resp.data['results'] : resp.data;
    return (results as List).map((e) => Order.fromJson(e)).toList();
  }

  Future<List<Order>> listFlaggedOrders() async {
    final resp = await _dio.get('/orders/flagged/');
    final results = resp.data is Map && resp.data['results'] != null ? resp.data['results'] : resp.data;
    return (results as List).map((e) => Order.fromJson(e)).toList();
  }

  Future<Order> getOrder(int id) async {
    final resp = await _dio.get('/orders/$id/');
    return Order.fromJson(resp.data);
  }

  /// Generic status transition — used for every role. What's actually
  /// allowed from the current status is enforced server-side, so a bad
  /// attempt here just comes back as a 400 with a clear message.
  Future<Order> updateStatus({
    required int orderId,
    required String status,
    String? transportReference,
  }) async {
    final resp = await _dio.patch('/orders/$orderId/status/', data: {
      'status': status,
      if (transportReference != null) 'transport_reference': transportReference,
    });
    return Order.fromJson(resp.data);
  }

  // --- Convenience wrappers for common transitions ---

  Future<Order> markPickedUp(int orderId) => updateStatus(orderId: orderId, status: 'picked_up');

  Future<Order> markDispatched(int orderId, String transportReference) =>
      updateStatus(orderId: orderId, status: 'dispatched', transportReference: transportReference);

  Future<Order> confirmReceived(int orderId) => updateStatus(orderId: orderId, status: 'delivered');

  Future<Order> reportNotReceived(int orderId) => updateStatus(orderId: orderId, status: 'flagged');
}
