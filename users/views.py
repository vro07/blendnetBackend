from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import UserSerializer
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from .models import User
from .models import Watchlist
from rest_framework import status
import datetime, jwt
import requests
from datetime import date,timedelta

# I've Polygon's API for stock data.
# todo: make API-key an environment variable
def get_close_price(ticker):
    API="vMn3iqIE7gSBJ0OXNr_dquQyT4ZH9zWQ"

    # the API returns the closing price of the date passed, so we must do current date -2 to ensure the date passed is always past date, as for future dates API complains.
    datee = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    url = f'https://api.polygon.io/v1/open-close/{ticker}/{datee}?adjusted=true&apiKey={API}'

    try:
        # Make a GET request to the API
        response = requests.get(url)
        response.raise_for_status()  
        
        # Parse the JSON response
        data = response.json()
        
        # Extract the close price from the response
        close_price = data.get('close')

        return close_price
    except requests.RequestException as e:
        print('Error:', e)

class RegisterView(APIView):
    # user registration or signup
    def post(self, req):
        serializer = UserSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        print(serializer.data)

        # jwt payload with expiry time of 1 day 
        payload = {
            'id': serializer.data['id'],
            'iat':datetime.datetime.utcnow(),
            'exp':datetime.datetime.utcnow()+datetime.timedelta(days=1),
        }
        token = jwt.encode(payload, 'secret', algorithm='HS256')


        return Response({"token":token})
    
class LoginView(APIView):
    # user login.
    def post(self, req):
        email = req.data['email']
        password = req.data['password']

        user = User.objects.filter(email =email).first()

        if user is None:
            raise AuthenticationFailed('User not found')
        
        if not user.check_password(password):
            raise AuthenticationFailed('Incorrect password')
        
        payload = {
            'id': user.id,
            'iat':datetime.datetime.utcnow(),
            'exp':datetime.datetime.utcnow()+datetime.timedelta(days=1),
        }
        #TODO: Make secret env var  
        token = jwt.encode(payload, 'secret', algorithm='HS256')

        return Response({"token":token})

class UserView(APIView):
    # get user details, for the navbar, and user state initialization on frontend
    def get_user_from_token(self, token):
        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
            user = User.objects.get(id=payload['id'])
            return user
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired, please login again')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

    def post(self, request):
        token = request.data.get('token')
        if not token:
            raise AuthenticationFailed('Unauthenticated')
        
        user = self.get_user_from_token(token)
        serializer = UserSerializer(user)
        watchlists = Watchlist.objects.filter(user=user)
        serialized_watchlists = []

        # Tickers are saved in comma seperated way.
        for watchlist in watchlists:
            serialized_watchlists.append({
                'id': watchlist.id,
                'name': watchlist.name,
                'tickers': watchlist.tickers.split(',')
            })
        response_data = {
            'user': serializer.data,
            'watchlists': serialized_watchlists
        }
        return Response(response_data)

class WatchListView(APIView):
    # Returns all the watchlists of the current user, User details is obtained from the jwt sent in body.
    def get_user_from_token(self, token):
        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
            user = User.objects.get(id=payload['id'])
            return user
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired, please login again')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

    def post(self, request):
        token = request.data.get('token')
        if not token:
            raise AuthenticationFailed('Unauthenticated')
        
        user = self.get_user_from_token(token)
        watchlists = Watchlist.objects.filter(user=user)
        serialized_watchlists = []

        # create Response for frontend, JSON of watchlists with ticker and price data
        for watchlist in watchlists:
            ticker_prices = []
            for ticker in watchlist.tickers.split(','):
                if ticker.strip()=='':
                    continue
                close_price = get_close_price(ticker) 
                ticker_prices.append({'ticker': ticker, 'close_price': close_price})
            
            serialized_watchlists.append({
                'id': watchlist.id,
                'name': watchlist.name,
                'tickers': ticker_prices  # Include ticker prices in serialized watchlist
            })
        
        response_data = {'watchlists': serialized_watchlists}
        return Response(response_data)

# A ticker could be added to existing watchlist or new watchlist will be created and a ticker will be added.
class AddTickerView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            raise AuthenticationFailed('Unauthenticated')
        
        user = UserView().get_user_from_token(token)

        watchlist_name = request.data.get('name')
        ticker = request.data.get('ticker')

        if not ticker:
            return Response({'error': 'Ticker not provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not watchlist_name:
            watchlist_name = f"{user.username}'s Watchlist"

        watchlist, created = Watchlist.objects.get_or_create(user=user, name=watchlist_name)
        
        if created:
            watchlist.save()
        
        print(get_close_price(ticker))
        watchlist.tickers += f",{ticker.strip().upper()}"
        watchlist.save()
        
        return Response({'message': 'Tickers added to watchlist.', 'watchlist_id': watchlist.id})

# Dummy data to avoid hitting Polygon's Stock data API again and again turing development mode.
class DummyWatchlistAPIView(APIView):
    def post(self, request):
        # Dummy data for watchlists with close prices
        watchlists = [
            {
                "id": 3,
                "name": "Tech Watchlist",
                "tickers": [
                    {"ticker": "AAPL", "close_price": 189.72},
                    {"ticker": "TSLA", "close_price": 173.99},
                    {"ticker": "MSFT", "close_price": 423.08},
                    {"ticker": "TSLA", "close_price": 173.99},
                    {"ticker": "MSFT", "close_price": 423.08}
                ]
            },
            {
                "id": 4,
                "name": "Rohan's Watchlist",
                "tickers": [
                    {"ticker": "IBM", "close_price": 168.26},
                    {"ticker": "TSLA", "close_price": 173.99},
                    {"ticker": "MSFT", "close_price": 423.08}
                ]
            },
           
        ]

        return Response({"watchlists": watchlists})
    
# this Would be used with adding the ticker on the frontend. add ticker button. without reload. data would be shown.
class GiveTickerPrice(APIView):
    def post(self, req):
        ticker = req.data.get("ticker")
        price = get_close_price(ticker)
        return Response({"price": price})