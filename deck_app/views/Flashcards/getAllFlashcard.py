from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_flashcard import FlashCardGetallSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserFlashCard, DeckFlashCard
from ...models import FlashCard, FlashCardPriority
from django.db.models import OuterRef, Subquery, F
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

            # Parâmetros de filtragem da query
            search = request.GET.get('search', None)
            order_by = request.GET.get('orderBy', None)

            filters = []
            if request.GET.get('New') == 'true':
                filters.append('New')
            if request.GET.get('Learning') == 'true':
                filters.append('Learning')
            if request.GET.get('Reviewing') == 'true':
                filters.append('Reviewing')

            # Buscar todos os flashcards associados ao deckId
            deck_flashcard_ids = DeckFlashCard.objects.filter(
                deck_id=deck_id).values_list('flashcard_id', flat=True)

            flashcards = FlashCard.objects.filter(id__in=deck_flashcard_ids)

            # Filtro de pesquisa no campo main_phrase
            if search:
                flashcards = flashcards.filter(main_phrase__icontains=search)

            # Buscar flashcards do usuário
            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id, deck_flashcard__deck_id=deck_id)

            if filters:
                user_flashcards_qs = user_flashcards_qs.filter(situation__in=filters)

            # Filtrando flashcards do usuário
            flashcards = flashcards.filter(
                id__in=user_flashcards_qs.values_list('deck_flashcard__flashcard_id', flat=True)
            )

            # Subconsulta para obter o campo updated_at da tabela FlashCardPriority
            priority_subquery = FlashCardPriority.objects.filter(
                deck_flashcard_id=OuterRef('id')  # Relacionando com o flashcard
            ).values('updated_at')

            # Anotando flashcards com o campo updated_at da FlashCardPriority
            flashcards = flashcards.annotate(
                priority_updated_at=Subquery(priority_subquery[:1])  # Subconsulta para pegar o updated_at
            )

            # Ordenação
            if order_by == 'newer':
                flashcards = flashcards.order_by('-created_at')
            elif order_by == 'older':
                flashcards = flashcards.order_by('created_at')
            elif order_by == 'lastModifications':
                flashcards = flashcards.order_by('-updated_at')
            elif order_by == 'lastStudied':
                # Ordenação pela data de atualização de prioridade
                flashcards = flashcards.order_by('-priority_updated_at', '-created_at')
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

            # Paginação
            paginator = Paginator(flashcards, 10)
            page_obj = paginator.get_page(page_number)

            # Serialização dos flashcards
            flashcards_serializer = FlashCardGetallSerializer(page_obj, many=True)

            # Obtendo o status de cada flashcard (New, Learning, Reviewing)
            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id,
                deck_flashcard__deck_id=deck_id
            ).select_related('deck_flashcard').only(
                'situation', 'deck_flashcard__flashcard_id')

            # Criando um dicionário para mapear flashcard_id -> situação do usuário
            user_flashcards_dict = {
                uf.deck_flashcard.flashcard_id: uf for uf in user_flashcards_qs
            }

            response_data = []
            for index, flashcard in enumerate(page_obj):
                serialized_flashcard = flashcards_serializer.data[index]
                user_flash = user_flashcards_dict.get(flashcard.id)

                # Construindo a resposta com os dados do flashcard e sua situação
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
                'deck': deck_name.title if deck_name else "Deck não encontrado",
                'flashcards': response_data,
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'pageNumber': page_number,
                'totalPages': paginator.num_pages,
            })

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
