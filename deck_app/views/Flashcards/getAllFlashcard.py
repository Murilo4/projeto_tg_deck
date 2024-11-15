from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_flashcard import FlashCardGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserFlashCard, DeckFlashCard
from ...models import FlashCard
from django.db.models import F, Max
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

            # Obter o parâmetro de pesquisa
            search = request.GET.get('search', None)

            # Outros parâmetros de filtragem e ordenação
            order_by = request.GET.get('orderBy', None)
            new = request.GET.get('New', None)
            learning = request.GET.get('Learning', None)
            reviewing = request.GET.get('Reviewing', None)
            most_reviewed = request.GET.get('MostReviewed', None)
            least_reviewed = request.GET.get('LeastReviewed', None)

            # Obter IDs de flashcards do deck específico
            deck_flashcard_ids = DeckFlashCard.objects.filter(
                deck_id=deck_id).values_list('flashcard_id', flat=True)

            flashcards = FlashCard.objects.filter(id__in=deck_flashcard_ids)

            # Filtrar com base no parâmetro `search` para `main_phrase`
            if search:
                flashcards = flashcards.filter(main_phrase__icontains=search)

            # Filtragem adicional com base na situação
            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id, deck_flashcard__deck_id=deck_id)

            if new == 'true':
                user_flashcards_qs = user_flashcards_qs.filter(
                    situation='New')
            if learning == 'true':
                user_flashcards_qs = user_flashcards_qs.filter(
                    situation='Learning')
            if reviewing == 'true':
                user_flashcards_qs = user_flashcards_qs.filter(
                    situation='Reviewing')

            flashcards = flashcards.filter(
                id__in=user_flashcards_qs.values_list(
                    'deck_flashcard__flashcard_id', flat=True))

            # Filtragem por número de revisões (mais ou menos revisado)
            if most_reviewed == 'true' or least_reviewed == 'true':
                flashcards = flashcards.annotate(
                    total_reviews=F('userflashcard__one_star') +
                    F('userflashcard__two_stars') +
                    F('userflashcard__three_stars') +
                    F('userflashcard__four_stars') +
                    F('userflashcard__five_stars')
                )
                if most_reviewed == 'true':
                    flashcards = flashcards.order_by('-total_reviews')
                elif least_reviewed == 'true':
                    flashcards = flashcards.order_by('total_reviews')

            # Ordenação conforme os parâmetros
            if order_by == 'newest':
                flashcards = flashcards.order_by('-created_at')
            elif order_by == 'oldest':
                flashcards = flashcards.order_by('created_at')
            elif order_by == 'recentlyModified':
                flashcards = flashcards.order_by('-updated_at')
            elif order_by == 'lastTime':
                user_flashcards = UserFlashCard.objects.filter(
                    user_id=user_id).values(
                    'deck_flashcard__deck_id').annotate(
                        last_time=Max('last_time'))
                recent_deck_ids = [uf['deck_flashcard__deck_id']
                                   for uf in user_flashcards]
                flashcards = flashcards.filter(id__in=recent_deck_ids)

            # Paginação dos resultados
            paginator = Paginator(flashcards, 10)
            page_obj = paginator.get_page(page_number)

            # Serialização
            flashcards_serializer = FlashCardGetSerializer(page_obj, many=True)

            # Obtenção de dados de UserFlashCard em bulk usando Prefetch
            user_flashcards_qs = UserFlashCard.objects.filter(
                user_id=user_id,
                deck_flashcard__deck_id=deck_id
            ).select_related('deck_flashcard').only(
                'situation', 'deck_flashcard__flashcard_id')

            user_flashcards_dict = {
                uf.deck_flashcard.flashcard_id: uf for uf in user_flashcards_qs}

            # Formatação da resposta
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
