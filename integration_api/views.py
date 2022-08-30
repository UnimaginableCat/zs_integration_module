from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from integration_api.dataclasses import ZsListingsOut
from integration_api.serializers import RetailAuthInputSerializer, ZsAuthInputSerializer,\
    RetailGetProductsWithFilterInputSerializer, RetailAuthWithCheckInputSerializer, ZsListingsOutputSerializer, \
    ZsCreateListingsInputSerializer, ZsRefreshTokenInputSerializer, ZsCreateAllListingsInputSerializer
from integration_api.services import try_retail_login, get_zone_jwt, RetailCRMService, get_access_token, \
    ZoneSmartService, create_periodic_tasks


class RetailCRMLogin(APIView):
    """Endpoint that checks RetailCRM credentials."""

    def post(self, request) -> Response:
        """
        :param request: Request with RetailCRM address and api key fields.
        :return: Response with login state status.
        """
        serializer = RetailAuthInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if try_retail_login(**serializer.validated_data):
            return Response({"login_state": True}, status=status.HTTP_200_OK)
        else:
            return Response({"login_state": False}, status=status.HTTP_400_BAD_REQUEST)


class ZsLogin(APIView):
    """Endpoint that checks ZoneSmart credentials and return access and refresh tokens."""

    def post(self, request) -> Response:
        """
        :param request: Request with ZoneSmart email and password fields.
        :return: Response with access and refresh tokens if credentials are valid.
        """
        serializer = ZsAuthInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = get_zone_jwt(**serializer.validated_data)
        if result is False:
            return Response({"reason": "Check credentials"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(result.get_fields(), status=status.HTTP_200_OK)


class ZsRefresh(APIView):
    """Endpoint that creates listings in ZoneSmart Api"""

    def post(self, request) -> Response:
        """

        :param request: Request with ZoneSmart Api refresh token.
        :return: Response with new access token.
        """
        serializer = ZsRefreshTokenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_token = get_access_token(serializer.validated_data['refresh'])
        if access_token is not False:
            return Response({"access": access_token}, status=status.HTTP_200_OK)
        else:
            return Response({"reason": "Refresh token is not valid!"}, status=status.HTTP_400_BAD_REQUEST)


class ZsCreateAllListings(APIView):
    """Endpoint that gets all available products from retail api and then creates listings in zonesmart api"""
    def post(self, request) -> Response:
        """

        :param request:  Request with zs auth data, retail auth data and price and quantity sync settings.
        :return: Response with created listings.
        """
        serializer = ZsCreateAllListingsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data['zonesmart_auth']['access']
        refresh = serializer.validated_data['zonesmart_auth']['refresh']
        sync_settings = serializer.validated_data['price_quantity_sync']
        retail_auth = serializer.validated_data['retail_auth']

        retail_service = RetailCRMService(retail_auth['address'], retail_auth['api_key'])
        zs_service = ZoneSmartService(access)

        zone_listings = retail_service.get_all_products()  # list of Zonesmart listings

        exported_listings, listings_of_tracked_products = zs_service.create_listings(zone_listings)

        if len(listings_of_tracked_products) > 0:
            create_periodic_tasks(sync_settings, listings_of_tracked_products, retail_auth, access, refresh)

        if len(exported_listings) > 0:
            listings_output = ZsListingsOut(listings=exported_listings)
            output_serializer = ZsListingsOutputSerializer(instance=listings_output)
            return Response(output_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"reason": "No listings were created:("}, status=status.HTTP_200_OK)


class ZsCreateListings(APIView):
    """Endpoint that creates listings in Zonesmart Api."""

    def post(self, request) -> Response:
        """
        :param request: Request with array of Zonesmart listings, zs auth data, retail auth data and price and quantity sync settings.
        :return: Response with created listings.
        """
        serializer = ZsCreateListingsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data['zonesmart_auth']['access']
        refresh = serializer.validated_data['zonesmart_auth']['refresh']

        zs_service = ZoneSmartService(access)

        sync_settings = serializer.validated_data['price_quantity_sync']
        retail_auth = serializer.validated_data['retail_auth']

        exported_listings, listings_of_tracked_products = zs_service.create_listings(serializer.validated_data['listings'])

        if len(listings_of_tracked_products) > 0:
            create_periodic_tasks(sync_settings, listings_of_tracked_products, retail_auth, access, refresh)

        if len(exported_listings) > 0:
            listings_output = ZsListingsOut(listings=exported_listings)
            output_serializer = ZsListingsOutputSerializer(instance=listings_output)
            return Response(output_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"reason": "No listings were created:("}, status=status.HTTP_200_OK)


class RetailAllProducts(APIView):
    """Endpoint that gets all products from RetailCRM api"""

    def post(self, request) -> Response:
        """
        :param request: Request with retail address and api key.
        :return: Response with list of products. If no products available returns 204 http status code.
        """
        serializer = RetailAuthWithCheckInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        retail_service = RetailCRMService(serializer.validated_data['address'], serializer.validated_data['api_key'])

        zone_listings = retail_service.get_all_products()  # list of Zonesmart listings
        listings_output = ZsListingsOut(listings=zone_listings)  # class with attribute listings so serializer can work

        if len(zone_listings) == 0:
            return Response({"Reason": "No available products"}, status=status.HTTP_204_NO_CONTENT)

        output_serializer = ZsListingsOutputSerializer(instance=listings_output)

        return Response(output_serializer.data, status=status.HTTP_200_OK)


class RetailProductsWithFilter(APIView):
    """Endpoint that gets products from RetailCRM api depending on filters."""

    def post(self, request) -> Response:
        """
        :param request: Request with retail address, api key and filters. Filters are min_quantity: int, active: 0|1,
        groups: [int](array of ids).

        :return: Response with list of products depending on filters. If no products available returns 204 http status code
        """

        serializer = RetailGetProductsWithFilterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        retail_service = RetailCRMService(**serializer.validated_data['retail_auth'])

        filters = serializer.validated_data['filters']

        zone_listings = retail_service.get_products_with_filters(filters)

        listings_output = ZsListingsOut(listings=zone_listings)  # class with attribute listings so serializer can work

        if len(zone_listings) == 0:
            return Response({"Reason": "No available products"}, status=status.HTTP_204_NO_CONTENT)

        output_serializer = ZsListingsOutputSerializer(instance=listings_output)

        return Response(output_serializer.data, status=status.HTTP_200_OK)


class RetailProductGroups(APIView):
    """Endpoint that gets product groups from RetailCRM Api."""

    def post(self, request) -> Response:
        """
        :param request: Request with RetailCRM address and api key fields.
        :return: Response with groups dictionary if address and api key are valid.
        """

        serializer = RetailAuthInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        retail_service = RetailCRMService(**serializer.validated_data)

        groups = retail_service.get_product_groups()
        if len(groups) > 0:
            return Response(groups, status=status.HTTP_200_OK)
        else:
            return Response({"reason": "No groups available"}, status=status.HTTP_204_NO_CONTENT)
