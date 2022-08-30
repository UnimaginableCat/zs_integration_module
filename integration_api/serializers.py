from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_dataclasses.serializers import DataclassSerializer
from integration_api.dataclasses import ProductFilter, ZoneSmartListing, PriceQuantitySync
from integration_api.services import try_retail_login, ZoneSmartService, get_access_token


class RetailAuthInputSerializer(serializers.Serializer):
    """RetailCRM input credentials serializer."""
    address = serializers.CharField(required=True)
    api_key = serializers.CharField(required=True)


class ZsAuthInputSerializer(serializers.Serializer):
    """Zonesmart input credentials serializer."""
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class ZsAccessTokenInputSerializer(serializers.Serializer):
    """Serializer that checks Zonesmart access token"""
    access = serializers.CharField(required=True)

    def validate(self, data):
        access = data['access']
        zs_service = ZoneSmartService(access)
        access_status = zs_service.check_access_token()
        if not access_status:
            raise ValidationError({"zonesmart_auth_error": "access token is not valid!"})
        return data


class ZsRefreshTokenInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)


class ZsRefreshAccessTokenInputSerializer(serializers.Serializer):
    """Serializer that checks Zonesmart refresh and access tokens."""
    access = serializers.CharField(required=True)
    refresh = serializers.CharField(required=True)

    def validate(self, data):

        refresh = data['refresh']
        refresh_check = get_access_token(refresh)
        if refresh_check is False:
            raise ValidationError({"zonesmart_auth_error": "refresh token is not valid!"})

        access = data['access']
        zs_service = ZoneSmartService(access)
        access_status = zs_service.check_access_token()
        if not access_status:
            raise ValidationError({"zonesmart_auth_error": "access token is not valid!"})


        return data


class FilterInputSerializer(DataclassSerializer):
    """Serializer that checks filter input"""
    class Meta:
        dataclass = ProductFilter


class RetailAuthWithCheckInputSerializer(serializers.Serializer):
    """RetailCRM input credentials serializer that makes request to RetailCRM api to check account data."""

    address = serializers.CharField(required=True)
    api_key = serializers.CharField(required=True)

    def validate(self, data):
        """Override of the validate func to check RetailCRM credentials"""
        address = data['address']
        api_key = data['api_key']
        retail_login_status = try_retail_login(address, api_key)
        if not retail_login_status:
            raise ValidationError({"retail_auth_error": "Check RetailCRM Credentials!"})
        return data


class RetailGetProductsWithFilterInputSerializer(serializers.Serializer):
    """Serializer that checks RetailCRM auth data and filters to get products from Retail Api"""
    retail_auth = RetailAuthWithCheckInputSerializer()
    filters = FilterInputSerializer()


class ZsListingSerializer(DataclassSerializer):
    """Serializer that outputs zs listing data(one instance)"""

    class Meta:
        dataclass = ZoneSmartListing


class PriceQuantitySyncInputSerializer(DataclassSerializer):

    class Meta:
        dataclass = PriceQuantitySync

    def validate(self, data: PriceQuantitySync):
        if data.quantity_sync is True:
            if data.quantity_sync_period is None:
                raise ValidationError({"quantity_sync_period": "You need to provide period!"})
        if data.price_sync is True:
            if data.price_sync_period is None:
                raise ValidationError({"price_sync_period": "You need to provide period!"})
        return data


class ZsCreateListingsInputSerializer(serializers.Serializer):
    """Serializer that checks Zonesmart auth data(access token) and a list of listings."""
    zonesmart_auth = ZsRefreshAccessTokenInputSerializer()
    retail_auth = RetailAuthWithCheckInputSerializer()
    listings = ZsListingSerializer(many=True)
    price_quantity_sync = PriceQuantitySyncInputSerializer()

    def validate(self, data):
        listings = data['listings']
        if len(listings) == 0:
            raise ValidationError({"listings": "Array is empty!"})
        return data


class ZsListingsOutputSerializer(serializers.Serializer):
    """Serializer that outputs zs listing data(many instances)"""
    listing_count = serializers.SerializerMethodField(method_name='get_count', read_only=True)
    listings = ZsListingSerializer(many=True)

    def get_count(self, obj):
        return len(obj.listings)


class ZsCreateAllListingsInputSerializer(serializers.Serializer):
    """Serializer that checks Zonesmart auth data(access token) and a list of listings."""
    zonesmart_auth = ZsRefreshAccessTokenInputSerializer()
    retail_auth = RetailAuthWithCheckInputSerializer()
    price_quantity_sync = PriceQuantitySyncInputSerializer()
