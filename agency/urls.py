from django.urls import path

from . import views
from . import shop


urlpatterns = [
    path("", views.home, name="home"),
    path("join/", views.join, name="join"),
    path("academy-opportunity/", shop.academy_opportunity, name="academy_opportunity"),
    path("shop/", shop.shop, name="training_shop"),
    path("shop/cart/", shop.cart, name="training_cart"),
    path("shop/cart/remove/<int:index>/", shop.remove_item, name="training_cart_remove"),
    path("shop/checkout/", shop.checkout, name="training_checkout"),
    path("shop/order/<uuid:token>/", shop.payment, name="training_payment"),
    path("shop/order/<uuid:token>/return/", shop.payment_return, name="training_payment_return"),
    path("shop/order/<uuid:token>/cancel/", shop.payment_return, {"cancelled": True}, name="training_payment_cancel"),
    path("shop/payfast/notify/", shop.notify, name="payfast_notify"),
]
