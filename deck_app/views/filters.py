from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ..serializers import PersonDeckGetSerializer
from ..models import Deck
from django.db.models import Min, Max
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
import requests



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

            serializer = PersonDeckGetSerializer(decks, many=True)
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


@api_view(['GET'])
def get_decks_by_page(request, page_number):
    response = requests.post(
        f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
    if response.status_code == 404:
        raise ValidationError(f'Não foi possivel validar o token.')

    token = request.headers.get('Authorization')

    user_id = token.get('id')

    # Filtra os decks do usuário
    decks = Deck.objects.filter(user_id=user_id)

    # Paginação
    paginator = Paginator(decks, 10)  # Mostra 10 decks por página
    page_obj = paginator.get_page(page_number)

    # Serializa os decks da página atual
    serializer = PersonDeckGetSerializer(page_obj, many=True)

    return JsonResponse({
        'decks': serializer.data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'page_number': page_number,
        'total_pages': paginator.num_pages,
    })
