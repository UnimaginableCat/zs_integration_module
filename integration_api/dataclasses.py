import dataclasses
import json
import typing
from dataclasses import dataclass

from integration_api.enums import TimeInterval


@dataclasses.dataclass
class ProductFilter:
    """Class that represents product filter"""
    active: typing.Optional[int] = dataclasses.field(metadata={'serializer_kwargs': {'min_value': 0, 'max_value': 1}})
    min_quantity: typing.Optional[int] = dataclasses.field(metadata={'serializer_kwargs': {'min_value': 0}})
    groups: typing.Optional[list[int]]


@dataclass
class JWT:
    """
    Class that represents JWT
    """
    access: str
    refresh: str

    def get_fields(self) -> dict:
        """
        :return: Access and refresh tokens as JSON
        """
        return{
            "access": self.access,
            "refresh": self.refresh
        }


@dataclass
class ZoneSmartProduct:
    """Class representing ZoneSmart Product"""
    sku: str
    quantity: int
    price: str
    product_code: typing.Optional[str]
    condition: typing.Optional[str]
    attributes: typing.Optional[typing.List[dict]]


class ProductConverter:
    """Class that converts RetailCRM representation of product to Zonesmart product."""
    def __init__(self, sku: str, quantity: int, price: str, product_code: str, attributes: dict):
        """
        :param sku: Product SKU.
        :param quantity: Product quantity.
        :param price: Product price.
        :param product_code: Product code.
        :param attributes: Product attributes.
        """
        self.sku = sku
        self.quantity = quantity
        self.price = price

        if product_code is None:
            self.product_code = "pcode"
        else:
            self.product_code = product_code

        self.condition = "NEW"

        self.attributes = list()
        if attributes is not None:
            for key in attributes:
                temp = {
                    'name': key,
                    'value': attributes[key]
                }
                self.attributes.append(temp)

    def get_zonesmart_product(self) -> ZoneSmartProduct:
        """Method that returns ZonesmartProduct object"""
        return ZoneSmartProduct(self.sku, self.quantity, self.price, self.product_code, self.condition, self.attributes)


@dataclass
class ZoneSmartListing:
    """
    Class representing ZoneSmart listing.
    """
    title: str
    description: str
    listing_sku: typing.Optional[str]
    category_name: typing.Optional[str]
    brand: typing.Optional[str]
    currency: typing.Optional[str]
    products: typing.List[ZoneSmartProduct]
    main_image: typing.Optional[str]
    extra_images: typing.Optional[list[str]]

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, ensure_ascii=False)


class ListingConverter:
    """Class that converts RetailCRM representation of listing to Zonesmart listing."""
    def __init__(self, title: str, desc: str, list_sku: str, cat_name: str, brand: str,
                 products: list[ZoneSmartProduct], main_image: str, ext_images: [str]):
        """
        :param title: Listing title.
        :param desc: Listing desctipiton.
        :param list_sku: Listing SKU.
        :param cat_name: Listing category name.
        :param brand: Listing brand name.
        :param products: Listing products.
        :param main_image: Listing main image url.
        :param ext_images: Listing extra images url.
        """
        self.title = title
        if desc == "":
            self.description = "Exported from RetailCRM"
        else:
            self.description = desc

        self.listing_sku = list_sku

        self.category_name = cat_name
        self.brand = brand
        self.currency = "RUB"
        self.products = products
        self.main_image = main_image
        self.extra_images = ext_images

    def get_zonesmart_listing(self):
        """Method that returns ZonesmartListing object"""
        return ZoneSmartListing(self.title, self.description, self.listing_sku, self.category_name, self.brand,
                                self.currency, self.products, self.main_image, self.extra_images)


@dataclass
class ZsListingsOut:
    """Class that helps to output listings."""
    listings: typing.List[ZoneSmartListing]


@dataclass
class TrackedProduct:
    """Class representing successfully exported product(From retail to zonesmart) that is going to be used in periodic tasks."""
    retail_id: str
    zone_listing_id: str
    zone_product_id: str
    warehouse_id: str


@dataclass
class PriceQuantitySync:
    """Class that handles price and quantity sync settings."""
    quantity_sync: bool
    price_sync: bool
    price_sync_period: typing.Optional[TimeInterval]
    quantity_sync_period: typing.Optional[TimeInterval]