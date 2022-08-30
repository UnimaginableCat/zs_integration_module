import datetime
import json
import requests
import retailcrm

from integration_api.models import QuantityChecker, PriceChecker
from integration_api.dataclasses import ProductFilter, JWT, ProductConverter, ZoneSmartListing, ListingConverter, \
    TrackedProduct, PriceQuantitySync


def create_periodic_tasks(sync_settings: PriceQuantitySync, listings_of_tracked_products: list[TrackedProduct],
                          retail_auth, access: str, refresh: str):
    """Method that creates periodic tasks depending on settings."""
    temp_exported_products_creds = [obj.__dict__ for obj in listings_of_tracked_products]
    json_exported_products_creds = json.dumps(temp_exported_products_creds) # need to convert array of products to json because celery cant understand complex python objects.

    if sync_settings.quantity_sync:
        QuantityChecker.objects.create(retail_address=retail_auth['address'],
                                       retail_api_key=retail_auth['api_key'],
                                       access_token=access,
                                       refresh_token=refresh,
                                       period=sync_settings.quantity_sync_period,
                                       products=json_exported_products_creds)

    if sync_settings.price_sync:
        PriceChecker.objects.create(retail_address=retail_auth['address'],
                                    retail_api_key=retail_auth['api_key'],
                                    access_token=access,
                                    refresh_token=refresh,
                                    period=sync_settings.quantity_sync_period,
                                    products=json_exported_products_creds)


def try_retail_login(address: str, api_key: str) -> bool:
    """Checks RetailCRM credentials.

    :param address: RetailCRM shop address.
    :param api_key: RetailCRM shop api_key.
    :return: Boolean login state.
    """
    client = retailcrm.v5(address, api_key)
    login_state = client.product_groups({'active': '1'}).get_response()['success']
    return login_state


def get_zone_jwt(email: str, password: str) -> JWT | bool:
    """Gets auth tokens from ZS Api

    :param email: Zonesmart account email.
    :param password: Zonesmart account password.
    :return: JWT if credentials are valid. Otherwise, false.
    """
    header = {
        'Content-Type': 'application/json',
    }
    data = {
        "email": email,
        "password": password
    }
    r = requests.post("https://api.zonesmart.com/v1/auth/jwt/create/", headers=header, json=data)

    tokens = json.loads(r.text)

    if r.status_code == 200:
        access = tokens['access']
        refresh = tokens['refresh']
        return JWT(access, refresh)
    else:
        return False


def get_access_token(refresh: str) -> str | bool:
    """Method that gets new access token from Zonesmart Api.

    :param refresh: Zonesmart Api refresh token.
    :return: Zonesmart Api access token.
    """
    header = {
        'Content-Type': 'application/json',
    }
    data = {
        "refresh": refresh
    }
    response = requests.post("https://api.zonesmart.com/v1/auth/jwt/refresh/", headers=header, json=data)
    converted_response = json.loads(response.text)
    if response.status_code == 200:
        access_token = converted_response['access']
        return access_token
    else:
        return False


class ZoneSmartService:
    """Class that helps with requests to Zonesmart Api"""

    def __init__(self, access: str):
        """
        :param access: Zonesmart api access token.
        """
        self.access = access

    def _get_request_header_auth(self) -> dict[str, str]:
        """Private method that returns headers with authorization field."""
        return {
            'Content-Type': 'application/json',
            'Authorization': 'JWT ' + self.access
        }

    def check_access_token(self) -> bool:
        """Method that sends request to Zonesmart api to check access token."""
        r = requests.get("https://api.zonesmart.com/v1/zonesmart/marketplace/", headers=self._get_request_header_auth())
        if r.status_code == 200:
            return True
        else:
            return False

    def check_refresh(self, refresh: str) -> bool:
        """Method that checks refresh token and gets new access token if refresh token is valid.
        :param refresh: Refresh token.
        :return: Refresh token status.
        """
        access = get_access_token(refresh)
        if access is False:
            return False
        else:
            self.access = access
            return True

    def _create_warehouse(self) -> str:
        """Method that creates warehouse in Zonesmart api.

        :return: Created warehouse id.
        """
        data = {
            'name': 'Export from RetailCRM at: ' + datetime.datetime.now().__str__()
        }
        response = requests.post("https://api.zonesmart.com/v1/zonesmart/warehouse/",
                                 headers=self._get_request_header_auth(), json=data)
        warehouse_id = json.loads(response.text)['id']
        return warehouse_id

    def _set_default_warehouse(self, warehouse_id: str) -> bool:
        """Method thad sets warehouse as default.

        :param warehouse_id: Warehouse id.
        :return: Setting status.
        """
        response = requests.post(f"https://api.zonesmart.com/v1/zonesmart/warehouse/{warehouse_id}/set_default/",
                                 headers=self._get_request_header_auth())
        if response.status_code == 200:
            return True
        else:
            return False

    def get_product_price(self, listing_id: str, product_id: str) -> str:
        """Method that gets product price from Zonesmart Api."""
        response = requests.get(f"https://api.zonesmart.com/v1/zonesmart/listing/{listing_id}/product/{product_id}/",
                                headers=self._get_request_header_auth())
        if response.status_code == 200:
            listing = json.loads(response.text)
            price = listing['price']
            return price
        else:
            return "0"

    def update_price(self, product_id: str, listing_id: str, price: str) -> bool:
        """Method that updates price of product in Zonesmart Api."""
        data = {
            'price': price
        }
        response = requests.patch(f"https://api.zonesmart.com/v1/zonesmart/listing/{listing_id}/product/{product_id}/",
                                  headers=self._get_request_header_auth(),
                                  json=data)
        if response.status_code == 200:
            return True
        else:
            return False

    def get_product_quantity(self, listing_id: str, product_id: str, warehouse_id: str) -> int:
        """Method that gets quantity of product from zonesmart api."""
        response = requests.get(f"https://api.zonesmart.com/v1/zonesmart/listing/{listing_id}/product/{product_id}/",
                                headers=self._get_request_header_auth())
        if response.status_code == 200:
            listing = json.loads(response.text)
            products_inventories = listing['product_inventories']
            for product in products_inventories:
                temp_warehouse_id = product['warehouse']
                if warehouse_id == temp_warehouse_id:
                    return product['quantity']
        else:
            return 0

    def update_product_quantity(self, product_id, warehouse_id, quantity):
        """Method that updates quantity of product in zonesmart api."""
        data = {
            'inventory': [{
                'product': product_id,
                'warehouse': warehouse_id,
                'quantity': quantity
            }]
        }
        response = requests.post("https://api.zonesmart.com/v1/zonesmart/product_inventory/bulk_update/",
                                 headers=self._get_request_header_auth(),
                                 json=data)
        if response.status_code == 200:
            return True
        else:
            return False

    def create_listings(self, listings: list[ZoneSmartListing]) -> tuple[list[ZoneSmartListing], list[TrackedProduct]]:
        """Method that creates listings in Zonesmart api.

        :param listings: List of Zonesmart listings.
        :return: List of successfully exported listings and list of products that will be used in periodic tasks.
        """
        warehouse_id = self._create_warehouse()
        self._set_default_warehouse(warehouse_id)

        exported_listings = list()
        listings_of_tracked_products = list()
        for listing in listings:
            json_listing = listing.to_json()
            correct_json_listing = json.loads(json_listing)
            response = requests.post("https://api.zonesmart.com/v1/zonesmart/listing/",
                                     headers=self._get_request_header_auth(),
                                     json=correct_json_listing)
            if response.status_code == 201:
                exported_listings.append(listing)
                created_listing = json.loads(response.text)
                created_listing_products = created_listing['products']
                for product in created_listing_products:
                    listings_of_tracked_products.append(TrackedProduct(product['sku'],
                                                                       created_listing['id'],
                                                                       product['id'],
                                                                       warehouse_id))
        return exported_listings, listings_of_tracked_products


class RetailCRMService:
    """
    Class that helps with requests to RetailCRM Api.
    """

    def __init__(self, address: str, api_key: str):
        """
        :param address: RetailCRM address.
        :param api_key: RetailCRM api key.
        """
        self.address = address
        self.api_key = api_key
        self.client = retailcrm.v5(self.address, self.api_key)

    def get_product_quantity(self, product_id: str) -> int:
        """Method that gets product quantity from Retail Api."""
        product_filter = {
            'ids': [product_id]
        }

        total_count = self.client.inventories(product_filter).get_response()['pagination']['totalCount']

        if total_count != 0:
            offers_query = self.client.inventories(product_filter, 20, 1).get_response()
            offer = offers_query['offers']
            quantity = offer[0]['quantity']
            return quantity
        else:
            return 0

    def get_offer_price(self, offer_id: str) -> str:
        """Method that gets offer price from retail api.

        :return: Offer price. If offer is deleted from retail api, returns "0".
        """
        product_filter = {
            'offerIds': [offer_id]
        }
        total_count = self.client.products(product_filter).get_response()['pagination']['totalCount']
        if total_count != 0:
            total_page_count = self.client.products(product_filter).get_response()['pagination']['totalPageCount']
            for i in range(1, total_page_count + 1):
                products_query = self.client.products(product_filter, 20, i).get_response()['products']

                for product in products_query:
                    for offer in product['offers']:
                        price = offer['prices'][0]['price']
                        return price
        else:
            return "0"

    def get_product_groups(self) -> dict[str, str]:
        """Method that gets product groups from RetailCRM Api.

        :return: Dictionary with product groups. Id as key, name as value.
        """
        groups = dict()

        groups_filter = {}

        total_page_count = self.client.product_groups(groups_filter).get_response()['pagination']['totalPageCount']
        for i in range(1, total_page_count + 1):
            group_query = self.client.product_groups(groups_filter, 20, i).get_response()['productGroup']
            for group in group_query:
                groups[group['id']] = group['name']

        return groups

    def _convert_filter(self, p_filter: ProductFilter) -> dict:
        """Method that converts filters so RetailCRM understands them.

        :param p_filter: Instance of class Product filter.
        :return: Product filter that RetailCRM api understands.
        """
        product_filter = dict()
        if p_filter.active is not None:
            product_filter['active'] = p_filter.active
        if p_filter.min_quantity is not None:
            product_filter['minQuantity'] = p_filter.min_quantity
        if p_filter.groups is not None:
            product_filter['groups'] = p_filter.groups
        return product_filter

    def _fetch_products(self, product_filter: dict) -> list[ZoneSmartListing]:
        """Method that fetches products from RetailCRM api.

        :param product_filter: Product filter converted by function _convert_filter.
        :return: List of ZoneSmart listings. If no products available in Retail api, returns empty list.
        """
        groups = self.get_product_groups()
        products = []
        total_count = self.client.products(product_filter).get_response()['pagination']['totalCount']

        if total_count != 0:
            total_page_count = self.client.products(product_filter).get_response()['pagination']['totalPageCount']

            for i in range(1, total_page_count + 1):
                products_query = self.client.products(product_filter, 20, i).get_response()['products']

                for product in products_query:
                    offers = []
                    images = None
                    for offer in product['offers']:
                        images = offer.get('images')
                        product_converter = ProductConverter(offer.get('id'),
                                                             offer.get('quantity'),
                                                             offer.get('price'),
                                                             offer.get('barcode'),
                                                             offer.get('properties'))
                        new_offer = product_converter.get_zonesmart_product()
                        offers.append(new_offer)
                    listing_converter = ListingConverter(product.get('name'),
                                                         product.get('description'),
                                                         product.get('id'),
                                                         groups.get(product['groups'][0]['id']),
                                                         product.get('manufacturer'),
                                                         offers,
                                                         product.get('imageUrl'),
                                                         images)
                    new_listing = listing_converter.get_zonesmart_listing()
                    products.append(new_listing)
        return products

    def get_all_products(self) -> list[ZoneSmartListing]:
        """Method that returns all products from RetailCRM api.

        :return: Array of products from RetailCRM Api(converted to ZoneSmart format). Empty list if no products available."""
        product_filter = {}

        return self._fetch_products(product_filter)

    def get_products_with_filters(self, p_filter: ProductFilter) -> list[ZoneSmartListing]:
        """Method that returns products from Retail Api depending of filters.

        :param p_filter: Instance of class Product filter.
        :return: Array of products from RetailCRM api(converted to ZoneSmart format). Empty list if no products available.
        """

        product_filter = self._convert_filter(p_filter)
        return self._fetch_products(product_filter)


def compare_and_update_prices(json_products, retail_service: RetailCRMService, zonesmart_service: ZoneSmartService):
    """Method that compares prices of product in retail api and listing in zonesmart api and if prices are different updates price in zonesmart api."""
    for product in json_products:
        retail_price = retail_service.get_offer_price(product['retail_id'])
        zone_price = zonesmart_service.get_product_price(product['zone_listing_id'],
                                                         product['zone_product_id'])
        if retail_price != zone_price:
            if zonesmart_service.update_price(product['zone_product_id'], product['zone_listing_id'], retail_price):
                print("Successfully updated price")
            else:
                print("Price wasn't updated")


def compare_and_update_quantity(json_products, retail_service: RetailCRMService, zonesmart_service: ZoneSmartService):
    """Method that compares quantity of product in retail api and listing in zonesmart api and if prices are different updates price in zonesmart api."""
    for product in json_products:
        retail_quantity = retail_service.get_product_quantity(product['retail_id'])
        zone_quantity = zonesmart_service.get_product_quantity(product['zone_listing_id'],
                                                               product['zone_product_id'],
                                                               product['warehouse_id'])
        if retail_quantity != zone_quantity:
            if zonesmart_service.update_product_quantity(product['zone_product_id'],
                                                         product['warehouse_id'],
                                                         retail_quantity):
                print("Successfully updated quantity")
            else:
                print("Quantity wasn't updated")