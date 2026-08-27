import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../providers/cart_provider.dart';
import '../../providers/product_provider.dart';
import '../../widgets/loading_button.dart';
import '../../core/constants.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);

class ProductDetailScreen extends ConsumerStatefulWidget {
  final int productId;
  const ProductDetailScreen({super.key, required this.productId});

  @override
  ConsumerState<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends ConsumerState<ProductDetailScreen> {
  int _quantity = 1;
  bool _adding = false;

  @override
  Widget build(BuildContext context) {
    final productAsync = ref.watch(productDetailProvider(widget.productId));

    return Scaffold(
      appBar: AppBar(title: const Text('Product')),
      body: productAsync.when(
        data: (product) => SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AspectRatio(
                aspectRatio: 1,
                child: product.imageUrl != null
                    ? Image.network(product.imageUrl!, fit: BoxFit.cover)
                    : Container(
                        color: AppTheme.surface2,
                        child: Icon(Icons.checkroom, size: 80, color: Colors.white24),
                      ),
              ),
              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(product.name,
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text(_currency.format(product.price),
                        style: const TextStyle(fontSize: 18, color: AppTheme.pinkDark, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 16),
                    if (product.description.isNotEmpty) Text(product.description),
                    const SizedBox(height: 24),
                    if (!product.isInStock)
                      const Text('Out of stock', style: TextStyle(color: Colors.red)),
                    if (product.isInStock) ...[
                      Row(
                        children: [
                          const Text('Quantity'),
                          const SizedBox(width: 16),
                          IconButton(
                            icon: const Icon(Icons.remove_circle_outline),
                            onPressed: _quantity > 1 ? () => setState(() => _quantity--) : null,
                          ),
                          Text('$_quantity', style: const TextStyle(fontSize: 16)),
                          IconButton(
                            icon: const Icon(Icons.add_circle_outline),
                            onPressed: _quantity < product.stock
                                ? () => setState(() => _quantity++)
                                : null,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      LoadingButton(
                        label: 'Add to cart',
                        icon: Icons.shopping_bag_outlined,
                        isLoading: _adding,
                        onPressed: () async {
                          setState(() => _adding = true);
                          try {
                            await ref.read(cartProvider.notifier).addItem(product.id, quantity: _quantity);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Added to cart')),
                              );
                            }
                          } catch (e) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(apiErrorMessage(e))),
                              );
                            }
                          } finally {
                            if (mounted) setState(() => _adding = false);
                          }
                        },
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load product: ${apiErrorMessage(e)}')),
      ),
    );
  }
}
