from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

from django.contrib.auth import get_user_model
User = get_user_model()
import json

from .models import MessageThread, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        if self._is_authenticated():
            # print('consumer scope -> ' + str(self.scope))

            self.room_object = await self.get_thread()
            print('Room -> ' + str(self.room_object))

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

            dataList = await self.get_messages()
            for d in reversed(dataList):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'sender': d['sender'],
                        'message': d['text']
                    }
            )


    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        if self._is_authenticated():
            text_data_json = json.loads(text_data)
            
            sender = text_data_json.get('sender')
            message = text_data_json.get('message')
            print('sender -> ' + str(sender) + '  message -> ' + str(message))

            await self.save_message(sender, message)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender': sender,
                    'message': message
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        sender = event['sender']
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'sender': sender,
            'message': message
        }))


    def _is_authenticated(self):
        print(self.scope['user'])
        if hasattr(self.scope, 'auth_error'):
            return False
        if not self.scope['user'] or self.scope['user'] is 'AnonymousUser':
            return False
        return True

    @database_sync_to_async
    def get_thread(self):
        thread, created = MessageThread.objects.get_or_create(title=self.room_name)
        return thread

    @database_sync_to_async
    def get_messages(self):
        thread = MessageThread.objects.get(title=self.room_name)
        dataList = []

        for m in Message.objects.filter(thread=thread).order_by('-timestamp')[:10]:
            messages = {
                'sender': m.sender.email,
                'text': m.text
            }
            dataList.append(messages)
        return dataList

    @database_sync_to_async
    def save_message(self, email, message):
        sender = User.objects.get(email=email)
        m = Message(thread=self.room_object, sender=sender, text=message)
        return m.save()
    
