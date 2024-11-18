from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_flashcard import FlashCardGetallSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserFlashCard, DeckFlashCard
from ...models import FlashCard
from django.db.models import OuterRef, Case, When, Value, DateTimeField, Max, Subquery, F
from ...validation.validation_jwt import validate_jwt
from django.core.paginator import Paginator


@csrf_exempt
@api_view(['GET'])
def get_all_flashcard(request, page_number, deckId):
    if request.method == 'GET':
        try:
            deck_id = deckId
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

            search = request.GET.get('search', None)

            order_by = request.GET.get('orderBy', None)

            filters = []
            if request.GET.get('New') == 'true':
                filters.append('New')
            if request.GET.get('Learning') == 'true':
                filters.append('Learning')
            if request.GET.get('Reviewing') == 'true':
                filters.append('Reviewing')

            deck_flashcard_ids = DeckFlashCard.objects.filter(
                deck_id=deck_id).values_list('flashcard_id', flat=True)

            flashcards = FlashCard.objects.filter(id__in=deck_flashcard_ids)

            if search:
                flashcards = flashcards.filter(main_phrase__icontains=search)

            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id, deck_flashcard__deck_id=deck_id)

            if filters:
                user_flashcards_qs = user_flashcards_qs.filter(situation__in=filters)

            flashcards = flashcards.filter(
                id__in=user_flashcards_qs.values_list(
                    'deck_flashcard__flashcard_id', flat=True))

            if order_by == 'newer':
                flashcards = flashcards.order_by('-created_at')
            elif order_by == 'older':
                flashcards = flashcards.order_by('created_at')
            elif order_by == 'lastModifications':
                flashcards = flashcards.order_by('-updated_at')
            elif order_by == 'lastStudied':
                user_flashcards_last_studied = UserFlashCard.objects.filter(
                    user_id=user_id
                ).values('deck_flashcard__flashcard_id').annotate(
                    last_time=Max('last_time')
                )
                last_studied_dict = {
                    uf['deck_flashcard__flashcard_id']: uf['last_time']
                    for uf in user_flashcards_last_studied
                }
                flashcards = flashcards.annotate(
                    last_time=Case(
                        *[
                            When(id=flashcard_id, then=Value(last_time))
                            for flashcard_id, last_time in last_studied_dict.items()
                        ],
                        default=None,
                        output_field=DateTimeField()
                    )
                ).order_by('-last_time')

            elif order_by == 'mostReviewed':
                user_flashcards_subquery = UserFlashCard.objects.filter(
                    deck_flashcard__flashcard_id=OuterRef('id'),
                    user_id=user_id
                ).annotate(
                    total_reviews=(
                        F('one_star') + F('two_stars') +
                        F('three_stars') + F('four_stars') + F('five_stars')
                    )
                ).values('total_reviews')

                flashcards = flashcards.annotate(
                    total_reviews=Subquery(user_flashcards_subquery[:1])
                ).order_by('-total_reviews')

            # Para `lessReviewed`
            elif order_by == 'lessReviewed':
                user_flashcards_subquery = UserFlashCard.objects.filter(
                    deck_flashcard__flashcard_id=OuterRef('id'),
                    user_id=user_id
                ).annotate(
                    total_reviews=(
                        F('one_star') + F('two_stars') +
                        F('three_stars') + F('four_stars') + F('five_stars')
                    )
                ).values('total_reviews')

                flashcards = flashcards.annotate(
                    total_reviews=Subquery(user_flashcards_subquery[:1])
                ).order_by('total_reviews')

            paginator = Paginator(flashcards, 10)
            page_obj = paginator.get_page(page_number)

            flashcards_serializer = FlashCardGetallSerializer(page_obj, many=True)

            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id,
                deck_flashcard__deck_id=deck_id
            ).select_related('deck_flashcard').only(
                'situation', 'deck_flashcard__flashcard_id')

            user_flashcards_dict = {
                uf.deck_flashcard.flashcard_id: uf for uf in user_flashcards_qs
                }

            response_data = []
            for index, flashcard in enumerate(page_obj):
                serialized_flashcard = flashcards_serializer.data[index]
                user_flash = user_flashcards_dict.get(flashcard.id)

                response_data.append({
                    **serialized_flashcard,
                    'situation': user_flash.situation if user_flash else None,
                })

            # Obtenção do nome do deck
            deck_name = Deck.objects.filter(id=deck_id).first()
            if not response_data:
                return JsonResponse({
                    "success": False,
                    'error': ['Não foi possível encontrar flashcards.']},
                    status=status.HTTP_404_NOT_FOUND)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'deck': deck_name.title,
                'flashcard': response_data,
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'pageNumber': page_number,
                'totalPages': paginator.num_pages,
            })

        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuarios não encontrados']},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
