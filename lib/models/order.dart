class OrderItem {
  final int id;
  final int product;
  final String productName;
  final int quantity;
  final double priceAtPurchase;
  final double subtotal;

  OrderItem({
    required this.id,
    required this.product,
    required this.productName,
    required this.quantity,
    required this.priceAtPurchase,
    required this.subtotal,
  });

  factory OrderItem.fromJson(Map<String, dynamic> json) => OrderItem(
        id: json['id'],
        product: json['product'],
        productName: json['product_name'] ?? '',
        quantity: json['quantity'],
        priceAtPurchase: double.tryParse(json['price_at_purchase'].toString()) ?? 0,
        subtotal: double.tryParse(json['subtotal'].toString()) ?? 0,
      );
}

class Order {
  final int id;
  final int customer;
  final String? customerName;
  final int? district;
  final String? districtName;
  final int? hub;
  final String? hubName;
  final int? assignedAgent;
  final String? assignedAgentName;
  final String status;
  final String transportReference;
  final double totalAmount;
  final String paymentStatus;
  final DateTime? confirmBy;
  final DateTime createdAt;
  final DateTime? dispatchedAt;
  final DateTime? deliveredAt;
  final List<OrderItem> items;
  final int? itemsCount;

  Order({
    required this.id,
    required this.customer,
    this.customerName,
    this.district,
    this.districtName,
    this.hub,
    this.hubName,
    this.assignedAgent,
    this.assignedAgentName,
    required this.status,
    required this.transportReference,
    required this.totalAmount,
    required this.paymentStatus,
    this.confirmBy,
    required this.createdAt,
    this.dispatchedAt,
    this.deliveredAt,
    this.items = const [],
    this.itemsCount,
  });

  bool get canConfirmOrFlag =>
      ['dispatched', 'picked_up', 'awaiting_confirmation'].contains(status);

  factory Order.fromJson(Map<String, dynamic> json) => Order(
        id: json['id'],
        customer: json['customer'],
        customerName: json['customer_name'],
        district: json['district'],
        districtName: json['district_name'],
        hub: json['hub'],
        hubName: json['hub_name'],
        assignedAgent: json['assigned_agent'],
        assignedAgentName: json['assigned_agent_name'],
        status: json['status'],
        transportReference: json['transport_reference'] ?? '',
        totalAmount: double.tryParse(json['total_amount'].toString()) ?? 0,
        paymentStatus: json['payment_status'] ?? '',
        confirmBy: json['confirm_by'] != null ? DateTime.tryParse(json['confirm_by']) : null,
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
        dispatchedAt: json['dispatched_at'] != null ? DateTime.tryParse(json['dispatched_at']) : null,
        deliveredAt: json['delivered_at'] != null ? DateTime.tryParse(json['delivered_at']) : null,
        items: json['items'] != null
            ? (json['items'] as List).map((e) => OrderItem.fromJson(e)).toList()
            : const [],
        itemsCount: json['items_count'],
      );
}
