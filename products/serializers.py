from rest_framework import serializers
from .models import Brand, Category, Size, Product, ProductImage, Review, StorePolicy, Sale


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo', 'description']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'value']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'product', 'rating', 'comment', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), source='brand', write_only=True, required=False, allow_null=True)
    category = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Category.objects.all(), source='category', write_only=True, required=False)
    sizes = SizeSerializer(many=True, read_only=True)
    size_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Size.objects.all(), source='sizes', write_only=True, required=False)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'brand', 'brand_id', 'category', 'category_ids', 'sizes', 'size_ids', 'price', 'old_price', 'description', 'image', 'stock', 'is_active', 'payment_policy', 'return_policy', 'stock_status', 'images', 'reviews']

    def create(self, validated_data):
        # Pop related writable fields
        categories = validated_data.pop('category', [])
        sizes = validated_data.pop('sizes', [])
        product = super().create(validated_data)
        if categories:
            product.category.set(categories)
        if sizes:
            product.sizes.set(sizes)
        return product


class StorePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = StorePolicy
        fields = ['id', 'title', 'payment_policy', 'return_policy']


class SaleSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all())

    class Meta:
        model = Sale
        fields = [
            'id',
            'title',
            'products',
            'discount_type',
            'discount_value',
            'start_date',
            'end_date',
            'active',
            'created_at',
        ]
        read_only_fields = ['created_at']
