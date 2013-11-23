# Python Imports

# Django Imports
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect

# Models
from accounts.models import Subscriber
from core.models import Location
from sms.models import Message

# Utils
from sms.utils import send_sms, post_to_twitter, post_to_facebook, invalid_city_message, realtime_post


# KEYWORDS *note: value should be unicode
KEYWORD = {
    'subscribe'  : u'SUB',
    'unsubscribe': u'UNSUB',
    'message'    : u'MSG',
    'info'       : u'INFO',
}


def inbound_sms(request):
    """
    This view will catch the user's sms through a GET request from youphoric server.
    """
    if request.method == "GET" and 'text' in request.GET and 'from' in request.GET:
        # TO-DO PAT: check GET if 'smsc' is 'strikerS6800in1ngin' 
        # (and add that to source smsc in settings)?
        content = {
            'text': request.GET['text'].split(),
            'num': request.GET['from']
        }
        if KEYWORD['subscribe'] == content['text'][0]:
            subscribe(content)
        elif KEYWORD['unsubscribe'] == content['text'][0]:
            unsubscribe(content)
        elif KEYWORD['message'] == content['text'][0]:
            post_message(content)
        elif KEYWORD['info'] == content['text'][0]:
            info(content)
        else:
            pass
            # TO-DO: Send sms to user that their sms format is invalid
        return HttpResponse()
    else:
        return redirect('index')


def location_list(city_string):
    location = Location.objects.filter(Q(code__iexact=city_string) | Q(name__iexact=city_string))
    return location

def subscribe(data):
    """
    This function will check and save the user's data
    """
    # Get location
    city = data['text'][1]
    location = location_list(city)

    if location.exists():
        # Check if the number already exist in the database
        subscriber, created = Subscriber.objects.get_or_create(phone=data['num'])
        if created:
            # Save name (optional)
            name = ' '.join(data['text'][2:])
            if name:
                subscriber.name = name
        subscriber.location.add(location[0])
        subscriber.save()
    else:
        # Send SMS to the user that the CITY is not valid
        message = invalid_city_message(city)
        # send_sms(data['num'], message)
        pass


def unsubscribe(data):
    """
    This function will check and unscubscribe the user's data
    """
    # Slice the text format: TYPE<space>CITY<space>NAME
    city = data['text'][1]
    location = location_list(city)
    subscriber = Subscriber.objects.filter(phone=data['num'])

    if subscriber.exists() and data['text'][1] == 'ALL':
        subscriber = subscriber[0]
        subscriber.location.clear()
        # TO-DO: confirmation reply that user is not subscribed
        # to any cities anymore
    if location.exists() and subscriber.exists():
        subscriber = subscriber[0]
        if location[0] in subscriber.location.all():
            subscriber.location.remove(location[0])
            subscriber.save()
        else:
            # user is not subscribed to the city
            pass
    else:
        # location and user does not exist: do something
        pass


def post_message(data):
    """
    This function will save the message and post on:
    - ShoutOut Board
    - Facebook
    - Twitter
    """
    # Slice the text format: TYPE<space>CITY<space>NAME
    try:
        message = data['text']
        subscriber = Subscriber.objects.get(phone=str(data['num']))
    except IndexError, e:
        # Error: Send error message
        pass
    except Subscriber.DoesNotExist, e:
        # Error: Send error message
        pass
    else:
        # Save Message
        message = Message.objects.create(content=message,
                                         subscriber=subscriber)
        message.save()
        # Add Facebook and twitter post here
        post_to_twitter(data['text'])
        post_to_facebook(data['text'])
        realtime_post(data['text'])


def info(data):
    """
    Sends SMS message to subscriber regarding 
    weather info on their subscribed city/cities
    """
    city = data['text'][1]
    location = location_list(city)
    # http://api.wunderground.com/api/e8f40aeb79ff08f8/geolookup/conditions/q/ph/manila.json
    weather_query = "http://api.wunderground.com/api/e8f40aeb79ff08f8/currenthurricane/view.json"
