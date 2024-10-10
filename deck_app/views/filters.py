from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ..serializers import DeckGetSerializer
from ..models import Deck
from django.db.models import Min, Max


@csrf_exempt
@api_view(['GET'])
def verify_number_of_cards(request):
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            decks = Deck.objects.filter(user_id=user_id)

            serializer = DeckGetSerializer(decks, many=True)
            card_stats = serializer.decks.aggregate(
                min_cards=Min('cards'),    # Mínimo número de cartas em um deck
                max_cards=Max('cards')     # Máximo número de cartas em um deck
            )
            return JsonResponse({'success': True,
                                 'message':
                                 'Número de cartas verificado com sucesso',
                                 'data': card_stats},
                                status=status.HTTP_200_OK)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message':
                                 'não foi possivel localizar o usuário'},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse(
            {'success': False,
             'message': 'Método não suportado'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
