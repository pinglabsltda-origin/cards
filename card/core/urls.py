# game/urls.py ou urls.py principal
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'), 
    path('mesa/', views.board_view, name='board_view'), 
    path('api/play-card/', views.play_card_api, name='play_card_api'),
    
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Deck & Coleção
    path('user/cards/', views.my_cards_view, name='my_cards'),
    path('user/deck/save/', views.save_deck_api, name='save_deck'),
    
    #mercado 
    path('market/', views.market_view, name='market'),
    path('api/market/buy/', views.market_buy, name='market_buy'),
    path('api/market/sell/', views.market_sell, name='market_sell'),
]