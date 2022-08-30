from django.urls import path

from integration_api.views import RetailCRMLogin, ZsLogin, RetailProductGroups, RetailProductsWithFilter, \
    RetailAllProducts, ZsRefresh, ZsCreateListings, ZsCreateAllListings

urlpatterns = [
    path('retail_login', RetailCRMLogin.as_view()),
    path('zs_login', ZsLogin.as_view()),
    path('retail_get_product_groups', RetailProductGroups.as_view(),),
    path('retail_get_products', RetailProductsWithFilter.as_view()),
    path('retail_get_all_products', RetailAllProducts.as_view()),
    path('zs_refresh', ZsRefresh.as_view()),
    path('zs_create_listings', ZsCreateListings.as_view()),
    path('zs_create_all_listings', ZsCreateAllListings.as_view()),
]
