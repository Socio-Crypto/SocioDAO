from django.urls import path
from . import views

urlpatterns = [
    path('', views.init_dapp, name='initialize'),
    path('dapp/<int:dao_id>', views.call_dapp, name='call'),
    path('dapp/<int:dao_id>/register', views.register_dapp, name='register'),
    path('dapp/<int:dao_id>/propose', views.propose_dapp, name='propose'),
    path('dapp/<int:dao_id>/vote', views.vote_dapp, name='vote'),
    path('dapp/<int:dao_id>/crowdfunding', views.crowdfund_dapp, name='crowdfunding'),


    
]
