class Wallet {
  final int id;
  final double balance;
  final DateTime? updatedAt;

  Wallet({required this.id, required this.balance, this.updatedAt});

  factory Wallet.fromJson(Map<String, dynamic> json) => Wallet(
        id: json['id'],
        balance: double.tryParse(json['balance'].toString()) ?? 0,
        updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) : null,
      );
}

class WalletTransaction {
  final int id;
  final String type;
  final double amount;
  final double balanceAfter;
  final String reference;
  final DateTime createdAt;

  WalletTransaction({
    required this.id,
    required this.type,
    required this.amount,
    required this.balanceAfter,
    required this.reference,
    required this.createdAt,
  });

  static const Map<String, String> typeLabels = {
    'topup_gateway': 'Wallet top-up',
    'topup_via_agent_credit': 'Top-up from agent',
    'topup_via_agent_debit': 'Top-up given to customer',
    'payment': 'Order payment',
    'commission': 'Delivery commission',
    'refund': 'Refund',
    'adjustment': 'Adjustment',
  };

  String get label => typeLabels[type] ?? type;

  factory WalletTransaction.fromJson(Map<String, dynamic> json) => WalletTransaction(
        id: json['id'],
        type: json['type'],
        amount: double.tryParse(json['amount'].toString()) ?? 0,
        balanceAfter: double.tryParse(json['balance_after'].toString()) ?? 0,
        reference: json['reference'] ?? '',
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      );
}

class TopUpRequest {
  final int id;
  final String provider; // mtn_momo / airtel_money
  final String phoneNumber;
  final double amount;
  final String status; // pending / successful / failed
  final DateTime createdAt;

  TopUpRequest({
    required this.id,
    required this.provider,
    required this.phoneNumber,
    required this.amount,
    required this.status,
    required this.createdAt,
  });

  String get providerLabel => provider == 'mtn_momo' ? 'MTN MoMo' : 'Airtel Money';

  factory TopUpRequest.fromJson(Map<String, dynamic> json) => TopUpRequest(
        id: json['id'],
        provider: json['provider'],
        phoneNumber: json['phone_number'] ?? '',
        amount: double.tryParse(json['amount'].toString()) ?? 0,
        status: json['status'],
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      );
}

class AgentCommission {
  final int id;
  final int orderId;
  final String productName;
  final double profitAmount;
  final double commissionAmount;
  final DateTime createdAt;

  AgentCommission({
    required this.id,
    required this.orderId,
    required this.productName,
    required this.profitAmount,
    required this.commissionAmount,
    required this.createdAt,
  });

  factory AgentCommission.fromJson(Map<String, dynamic> json) => AgentCommission(
        id: json['id'],
        orderId: json['order_id'],
        productName: json['product_name'] ?? '',
        profitAmount: double.tryParse(json['profit_amount'].toString()) ?? 0,
        commissionAmount: double.tryParse(json['commission_amount'].toString()) ?? 0,
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      );
}
