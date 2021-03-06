from rest_framework import generics, permissions, status
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.authtoken.models import Token
from django.contrib.auth import (
    login as django_login,
    logout as django_logout
)
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt

from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from .models import User, ValidationKey
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    AbstractUserRegisterSerializer,
    AbstractUserLoginSerializer,
)


'''
-------------------- Email Varification --------------------
'''

# Verify email and send validation key
class VerifyEmailAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        raw_email = request.data.get('email')

        if raw_email:
            email = str(raw_email)
            user = User.objects.filter(email__iexact = email)

            if user.exists():
                return Response({
                    'status': False,
                    'details': 'This eamil already exists.'
                })
            else:
                new_key = create_key(email)
                if new_key:
                    sendValidationKey(request, email, new_key)
                    key = ValidationKey.objects.filter(email__iexact=email)

                    if key.exists():
                        key = key.first()
                        count = key.count

                        if count > 6:
                            return Response({
                                'status': False,
                                'details': 'Reached limitation.'
                            })
                        key.count = count + 1
                        key.save()
                        return Response({
                            'status': True,
                            'details': 'Validation key successfully sent.'
                        })
                    else:
                        ValidationKey.objects.create(email=email, key=new_key) 
                        return Response({
                            'status': True,
                            'details': 'Validation key successfully sent.'
                        })
                else:
                    return Response({
                        'status': False,
                        'details': 'Failed to send validation key.'
                    })
        else:
            return Response({
                'status': False,
                'details': 'This eamil already exists.'
            })

# Create validation key
def create_key(email):
    import random
    if email:
        key = random.randint(999, 9999)
        print(key)
        return key
    else:
        return False

# Send validation key through email 
def sendValidationKey(request, email, new_key):
    if email:
        subject = 'Welcome to Speagle'
        message = ' This is your validation key -> ' + str(new_key) + ' '
        email_from = settings.EMAIL_HOST_USER

        recipient_list = [email,]
        send_mail( subject, message, email_from, recipient_list )

# Verify validation key
class VerifyValidationKeyAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', False)
        raw_key = request.data.get('key', False)

        if email and raw_key:
            old_key = ValidationKey.objects.filter(email__iexact = email)
            
            if old_key.exists():
                old_key = old_key.first()
                key = old_key.key

                if str(raw_key) == str(key):
                    old_key.validated = True
                    old_key.save() # Why save the old one.
                    return Response({
                        'status': True,
                        'details': 'Correct validation key.'
                    })
                else:
                    return Response({
                        'status': False,
                        'details': 'Incorrect validation key.'
                    })
            else:
                return Response({
                    'status': False,
                    'details': 'Request validation key first.'
                })
        else:
            return Response({
                'status': False,
                'details': 'Email & validation key must be set.'
            })


'''
-------------------- Registration API --------------------
'''

class RegisterAPI(generics.GenericAPIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny, )
    serializer_class = AbstractUserRegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
        })


'''
-------------------- Token Resgistration --------------------
'''

class TokenRegistrationAPI(CreateAPIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)
    serializer_class = AbstractUserRegisterSerializer

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', False)
        password = request.data.get('password', False)

        if email and password:
            old = ValidationKey.objects.filter(email__iexact = email)
            
            if old.exists():
                old = old.first()
                validated = old.validated
                
                if validated:
                    serializer = self.get_serializer(data=request.data)
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    user = serializer.instance
                    token, created = Token.objects.get_or_create(user=user)

                    data = serializer.data
                    data["token"] = token.key
                    headers = self.get_success_headers(serializer.data)
                    old.delete()
                    # return Response(data, status=status.HTTP_201_CREATED, headers=headers)
                    return Response({
                        'status': True,
                        'details': 'Account created'
                    })
                else:
                    return Response({
                        'status': False,
                        'details': 'Verification of validation key is needed.'
                    })
            else:
                return Response({
                    'status': False,
                    'details': 'Email validation is needed.'
                })
        else:
            return Response({
                'status': False,
                'details': 'Email & password must be set.'
            })


class TokenLoginAPI(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny, )
    serializer_class = AbstractUserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        ''' If the user is authenticated, below method will create or retrieve
        token for the existing user. Token authentication will need token
        in every API calls that needs authentication. '''
        token, created = Token.objects.get_or_create(user=user)
        # django_login(self.request, user) # Used for session login

        return Response({
            'status': True,
            'details': token.key
        })


class TokenLogoutAPI(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    # permission_classes = (permissions.AllowAny, )

    def get(self, request, format=None):
        user = request.user
        if user.exists():
            ''' Request should include Authorization in headers.
            For example -> key would be Authorization and value would be
            Token cc5ff8720ded0009b40ccc2fb25c6f3d725658a0 '''
            user.auth_token.delete()
            # django_logout(self.request) # Used for session logout
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({
                'status': False,
                'details': 'AnonymousUser.'
            })


'''
-------------------- JWT Resgistration --------------------
'''

class JWTLoginAPI(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny, )
    serializer_class = AbstractUserLoginSerializer

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        token = self.get_tokens_for_user(user)
        refresh_token = token.get('refresh')
        access_token = token.get('access')

        # Needs argument weather if it's expired or not.

        return Response({
            'status': True,
            'details': refresh_token
        })


'''
-------------------- Session Login & Logout --------------------
'''

class SessionLoginAPI(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny, )
    serializer_class = AbstractUserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        django_login(request, user)

        return Response({
            'status': True,
            'details': 'Login successful'
        })


class SessionLogoutAPI(APIView):
    # permission_classes = (permissions.IsAuthenticated,)
    permission_classes = (permissions.AllowAny, )

    def get(self, request, format=None):
        user = request.user
        if user.exists():
            django_logout(request)
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({
                'status': False,
                'details': 'AnonymousUser.'
            })