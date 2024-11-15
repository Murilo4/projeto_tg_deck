from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_deck import PersonDeckGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeckPreferences
from ...validation.validation_jwt import validate_jwt
from ...validation.validation_session import validate_session


@csrf_exempt
@api_view(['GET'])
def get_deck(request, deckId):
    if request.method == 'GET':
        deck_id = deckId
        try:

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            deck = Deck.objects.get(id=deck_id)
            deck_serializer = PersonDeckGetSerializer(deck)

            user_deck_pref = UserDeckPreferences.objects.get(deck_id=deck.id)
            user_deck_info = {
                'new_per_day': user_deck_pref.new_per_day,
                'learning_per_day': user_deck_pref.learning_per_day,
                'reviewing_per_day': user_deck_pref.review_per_day
            }
            combined_data = {
                **deck_serializer.data,  # Dados do deck
                **user_deck_info         # Dados das preferências do usuário
            }

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'deck': [combined_data]
            },
                status=status.HTTP_200_OK)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuarios não encontrados']},
                                status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
