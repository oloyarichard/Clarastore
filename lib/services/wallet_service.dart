import '../core/api_client.dart';
import '../models/wallet.dart';

class WalletService {
  final _dio = ApiClient.instance.dio;

  Future<Wallet> getWallet() async {
    final resp = await _dio.get('/wallet/');
    return Wallet.fromJson(resp.data);
  }

  Future<List<WalletTransaction>> getTransactions() async {
    final resp = await _dio.get('/wallet/transactions/');
    final results = resp.data is Map && resp.data['results'] != null ? resp.data['results'] : resp.data;
    return (results as List).map((e) => WalletTransaction.fromJson(e)).toList();
  }

  /// Starts an MTN MoMo / Airtel Money top-up. Provider is optional — if
  /// omitted, the backend guesses from the phone prefix. Returns a
  /// TopUpRequest the caller should poll with [checkTopUpStatus].
  Future<TopUpRequest> initiateTopUp({
    required double amount,
    required String phoneNumber,
    String? provider,
  }) async {
    final resp = await _dio.post('/wallet/topup/', data: {
      'amount': amount,
      'phone_number': phoneNumber,
      if (provider != null) 'provider': provider,
    });
    return TopUpRequest.fromJson(resp.data);
  }

  Future<TopUpRequest> checkTopUpStatus(int topUpRequestId) async {
    final resp = await _dio.get('/wallet/topup/$topUpRequestId/status/');
    return TopUpRequest.fromJson(resp.data);
  }

  /// Agent-only: credits a customer's wallet from the agent's own float,
  /// after collecting cash from them in person.
  Future<void> agentTopUpCustomer({
    required String customerIdentifier,
    required double amount,
  }) async {
    await _dio.post('/wallet/agent/topup-customer/', data: {
      'customer_identifier': customerIdentifier,
      'amount': amount,
    });
  }

  /// Agent-only: their own delivery commission history.
  Future<List<AgentCommission>> getCommissions() async {
    final resp = await _dio.get('/wallet/agent/commissions/');
    final results = resp.data is Map && resp.data['results'] != null ? resp.data['results'] : resp.data;
    return (results as List).map((e) => AgentCommission.fromJson(e)).toList();
  }
}
