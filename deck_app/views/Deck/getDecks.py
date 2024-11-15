from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_deck import PersonDeckGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck
from ...validation.validation_jwt import validate_jwt
from ...validation.validation_session import validate_session


@csrf_exempt
@api_view(['GET'])
def get_deck(request, deckId):
    if request.method == 'GET':
        deck_id = deckId
        try:
            validate_session()

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            custom_decks = Deck.objects.get(id=deck_id)
            custom_decks_serializer = PersonDeckGetSerializer(custom_decks)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'deck': [custom_decks_serializer.data]
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
