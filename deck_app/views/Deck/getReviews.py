from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck
from ...validation.validation_jwt import validate_jwt


@csrf_exempt
@api_view(['GET'])
def get_reviews(request):
    if request.method == 'GET':
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')
            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            user_decks = UserDeck.objects.filter(
                user_id=user_id).values_list('deck_id', flat=True)

            standard_decks = Deck.objects.filter(
                type_deck='Standard').exclude(id__in=user_decks)

            if not standard_decks:
                return JsonResponse({
                    "success": False,
                    'error': ['Não foi possível encontrar decks.'],
                    'hasAllDecks': True},
                    status=status.HTTP_404_NOT_FOUND)

            reviews_counts_list = []
            for deck in standard_decks:
                reviews_counts_list.append(deck.reviews)

            reviews_min = min(
                reviews_counts_list) if reviews_counts_list else 0
            reviews_max = max(
                reviews_counts_list) if reviews_counts_list else 0

            return JsonResponse({"success": True,
                                 "message": "Valores retornados",
                                'minReviews': reviews_min,
                                 'maxReviews': reviews_max},
                                status=status.HTTP_200_OK)

        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuários não encontrados']},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
