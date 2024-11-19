from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_deck import PersonDeckGetStandardSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck
from django.core.paginator import Paginator
from ...validation.validation_jwt import validate_jwt
from django.db.models import Count
from django.db.models import Max, Min


@csrf_exempt
@api_view(['GET'])
def get_standard_decks(request, page_number):
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

            # IDs dos decks que o usuário já possui
            user_decks = UserDeck.objects.filter(
                user_id=user_id).values_list('deck_id', flat=True)

            # Filtros da query
            difficulty = request.GET.getlist('difficulty', None)
            order_by = request.GET.get('orderBy', None)
            min_reviews = request.GET.get('minReviews', None)
            max_reviews = request.GET.get('maxReviews', None)
            search_term = request.GET.get('search', None)  # Novo filtro de pesquisa

            # Filtrar os decks padrão que não estão nos decks do usuário
            standard_decks = Deck.objects.filter(
                type_deck='Standard').exclude(id__in=user_decks)

            # Filtro por termo de pesquisa no título
            if search_term:
                standard_decks = standard_decks.filter(
                    title__icontains=search_term)

            # Filtros adicionais de reviews e dificuldade
            if min_reviews is not None:
                standard_decks = standard_decks.filter(
                    reviews__gte=int(min_reviews))
            if max_reviews is not None:
                standard_decks = standard_decks.filter(
                    reviews__lte=int(max_reviews))
            if difficulty:
                standard_decks = standard_decks.filter(
                    difficult__in=difficulty)

            # Anotação de contagem de flashcards e reviews
            standard_decks = standard_decks.annotate(
                flashcard_count=Count('deckflashcard'),
                min_reviews=Min('reviews'),
                max_reviews=Max('reviews')
            )

            # Obter min/max reviews de maneira eficiente
            reviews_min = standard_decks.aggregate(Min('reviews'))['reviews__min'] or 0
            reviews_max = standard_decks.aggregate(Max('reviews'))['reviews__max'] or 0

            # Ordenação conforme especificado
            if order_by == 'newer':
                standard_decks = standard_decks.order_by('-created_at')
            elif order_by == 'older':
                standard_decks = standard_decks.order_by('created_at')
            elif order_by == 'lastModifications':
                standard_decks = standard_decks.order_by('-updated_at')
            elif order_by == 'feedback':
                standard_decks = standard_decks.order_by('-stars')
            elif order_by == 'flashcards':
                standard_decks = standard_decks.order_by('-flashcard_count')

            # Paginação dos resultados
            paginator = Paginator(standard_decks, 10)
            page_obj = paginator.get_page(page_number)

            # Serialização
            standard_decks_serializer = PersonDeckGetStandardSerializer(
                page_obj, many=True)

            # Construção da resposta
            response_data = []
            for index, deck in enumerate(page_obj):
                flashcard_count = deck.flashcard_count if hasattr(deck, 'flashcard_count') else 0
                response_data.append({
                    **standard_decks_serializer.data[index],
                    'flashcards': flashcard_count
                })

            if not response_data:
                return JsonResponse({
                    "success": False,
                    'error': ['Não foi possível encontrar decks.'],
                    'hasAllDecks': not standard_decks.exists()},
                    status=status.HTTP_404_NOT_FOUND)

            return JsonResponse({
                'success': True,
                'message': ['dados retornados'],
                'standardDecks': response_data,
                'minReviews': reviews_min,
                'maxReviews': reviews_max,
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'pageNumber': page_number,
                'totalPages': paginator.num_pages
            }, status=status.HTTP_200_OK)

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