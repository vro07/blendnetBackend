from django.urls import path, include
from .views import RegisterView, LoginView,UserView,AddTickerView,WatchListView,DummyWatchlistAPIView,GiveTickerPrice
urlpatterns=[
    path('register',RegisterView.as_view()),
    path('login',LoginView.as_view()),
    path('user',UserView.as_view()),
    path('addTicker',AddTickerView.as_view()),
    path('watchlists',WatchListView.as_view()),
    path('dummy',DummyWatchlistAPIView.as_view()),
    path('price',GiveTickerPrice.as_view()),
]
