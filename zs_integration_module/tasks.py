import json

from celery import shared_task

from integration_api.models import PriceChecker, QuantityChecker
from integration_api.services import ZoneSmartService, RetailCRMService, try_retail_login, compare_and_update_prices, \
    compare_and_update_quantity


@shared_task(name='update_products_price')
def update_products_price(retail_address: str, retail_api_key: str, access_token: str, refresh_token: str, products):
    retail_login_check = try_retail_login(retail_address, retail_api_key)  # checking retail auth data
    zonesmart_service = ZoneSmartService(access_token)
    refresh_check = zonesmart_service.check_refresh(refresh_token)  # checking refresh token
    if refresh_check is False or retail_login_check is False:
        PriceChecker.objects.get(retail_address=retail_address, # deleting periodic task if retail or zonesmart auth data is not valid
                                 retail_api_key=retail_api_key,
                                 products=products).delete()

    retail_service = RetailCRMService(retail_address, retail_api_key)
    json_products = json.loads(products)
    compare_and_update_prices(json_products, retail_service, zonesmart_service)

@shared_task(name='update_products_quantity')
def update_products_quantity(retail_address, retail_api_key, access_token, refresh_token, products):
    retail_login_check = try_retail_login(retail_address, retail_api_key) # checking retail auth data
    zonesmart_service = ZoneSmartService(access_token)
    refresh_check = zonesmart_service.check_refresh(refresh_token)  # checking refresh token
    if refresh_check is False or retail_login_check is False:
        QuantityChecker.objects.get(retail_address=retail_address, # deleting periodic task if retail or zonesmart auth data is not valid
                                    retail_api_key=retail_api_key,
                                    products=products).delete()

    retail_service = RetailCRMService(retail_address, retail_api_key)
    json_products = json.loads(products)
    compare_and_update_quantity(json_products, retail_service, zonesmart_service)
