from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck


@csrf_exempt
@api_view(['GET'])
def get_deck_type(request, deckId):
    if request.method == 'GET':
        deck_id = deckId
        try:
            deck = Deck.objects.get(id=deck_id)
            deck_type = deck.type_deck

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'deckType': deck_type
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
