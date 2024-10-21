from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ..serializers import PersonDeckSerializer
from ..serializers import UserDeckSerializer, CreateStandardDecks
import requests
from ..models import Deck
from django.core.exceptions import ValidationError
from ..validate import validate_jwt


@csrf_exempt
@api_view(['POST'])
def create_deck(request):
    if request.method == 'POST':
        try:
            response = requests.post(
                f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
            if response.status_code == 404:
                raise ValidationError(f'Não foi possivel validar o token.')

            token = request.headers.get('Authorization')
            if token.startswith("Bearer "):
                token = token[7:]
            jwt_data = validate_jwt(token)

            user_id = jwt_data.get('id')
            deck_name = request.data.get('deckName')
            description = request.data.get('description')
            img_url = request.data.get('img')
            color = request.data.get('color')
            type_deck = request.data.get('typedeck')
            difficult = request.data.get('difficult')

            if not difficult:
                difficult = None

            if not type_deck:
                type_deck = "Custom"

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'Usuario não encontrado'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not deck_name:
                return JsonResponse({'success': False,
                                    'message': 'Deck name is required'},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not description:
                description = ' '

            if not img_url:
                return JsonResponse({'success': False,
                                    'message': 'Image URL is required'},
                                    status=status.HTTP_400_BAD_REQUEST
                                    )
            if type_deck == "Custom":
                new_deck = {
                    'title': deck_name,
                    'description_deck': description,
                    'image': img_url,
                    'color_predefinition': color,
                }
                serializer = PersonDeckSerializer(data=new_deck)
                if serializer.is_valid(raise_exception=True):
                    deck = serializer.save()
                    deck_id = deck.id
                    new_user_deck = {
                        'user_id': user_id,
                        'deck_id': deck_id
                    }
                    serializer_user_deck = UserDeckSerializer(
                        data=new_user_deck)

                    if serializer_user_deck.is_valid(raise_exception=True):
                        serializer_user_deck.save()
                        return JsonResponse({'success': True,
                                            'message': 'Deck criado com sucesso'},
                                            status=status.HTTP_201_CREATED)
                else:
                    return JsonResponse({'success': False,
                                        'message':
                                         'Não foi possivel validar os dados'},
                                        status=status.HTTP_400_BAD_REQUEST)
            else:
                new_deck_default = {
                    'title': deck_name,
                    'description_deck': description,
                    'image': img_url,
                    'color_predefinition': color,
                    'difficult': difficult,
                    "type_deck": "Standard",
                    'public': True
                }
                serializer = CreateStandardDecks(data=new_deck_default)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    return JsonResponse({'success': True,
                                        'message': 'Deck criado com sucesso'},
                                        status=status.HTTP_201_CREATED)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message':
                                'não foi possivel validar os dados inseridos'},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({'success': False,
                            'message':  'Método não suportado'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
