from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_deck import PersonDeckGetSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, UserFlashCard
from django.db.models import Max, Case, When, Value, DateTimeField, Min
from django.core.paginator import Paginator
from ...validation.validation_jwt import validate_jwt
from django.db.models import Count, Prefetch


@csrf_exempt
@api_view(['GET'])
def get_all_decks(request, page_number):
    if request.method == 'GET':
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message': ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Parâmetros adicionais para filtros e ordenação
            order_by = request.GET.get('orderBy', None)
            min_fls = request.GET.get('minFlashcards', None)
            max_fls = request.GET.get('maxFlashcards', None)
            favorite_filter = request.GET.get('favorites', None)
            learning_filter = request.GET.get('learning', None)
            reviewing_filter = request.GET.get('finished', None)
            search_query = request.GET.get('search', None)
            deck_type_filter = request.GET.get('type', None)

            # IDs dos decks que o usuário já possui
            user_decks = UserDeck.objects.filter(user_id=user_id).values_list('deck_id', flat=True)
            deck_ids = list(user_decks)

            # Busca os decks associados
            decks = Deck.objects.filter(id__in=deck_ids)

            # Filtro de busca pelo título do deck (title)
            if search_query:
                decks = decks.filter(title__icontains=search_query)

            # Filtros adicionais de favoritos, learning e reviewing
            if favorite_filter == 'true':
                decks = decks.filter(userdeck__user_id=user_id, userdeck__favorite=True)
            if learning_filter == 'true':
                decks = decks.filter(userdeck__user_id=user_id, userdeck__learning=True)
            if reviewing_filter == 'true':
                decks = decks.filter(userdeck__user_id=user_id, userdeck__reviewing=True)

            # Filtro de tipo de deck (Custom ou Standard), padrão é ambos
            if deck_type_filter:
                if deck_type_filter not in ['Custom', 'Standard']:
                    return JsonResponse({
                        'success': False,
                        'message': ['Tipo de deck inválido.']
                    }, status=status.HTTP_400_BAD_REQUEST)
                decks = decks.filter(type_deck=deck_type_filter)

            # Contagem de flashcards agora baseada na tabela DeckFlashcard
            decks = decks.annotate(
                flashcard_count=Count('deckflashcard')
            )

            # Filtro de quantidade de flashcards
            if min_fls:
                decks = decks.filter(flashcard_count__gte=int(min_fls))
            if max_fls:
                decks = decks.filter(flashcard_count__lte=int(max_fls))

            # Calcular flashcard_min e flashcard_max antes da paginação
            flashcard_min = decks.aggregate(
                Min('flashcard_count'))['flashcard_count__min'] or 0
            flashcard_max = decks.aggregate(
                Max('flashcard_count'))['flashcard_count__max'] or 0

            # Pré-carregar dados adicionais relacionados aos decks do usuário
            user_decks = UserDeck.objects.filter(user_id=user_id, deck_id__in=deck_ids).only(
                'deck_id', 'favorite', 'learning', 'reviewing', 'new')

            decks = decks.prefetch_related(
                Prefetch('userdeck_set', queryset=user_decks)
            )

            # Ordenação dos decks com base nos parâmetros
            if order_by == 'newer':
                decks = decks.order_by('-created_at')
            elif order_by == 'older':
                decks = decks.order_by('created_at')
            elif order_by == 'lastModifications':
                decks = decks.order_by('-updated_at')
            elif order_by == 'lastStudied':
                user_flashcards = UserFlashCard.objects.filter(user_id=user_id).values(
                    'deck_flashcard__deck_id'
                ).annotate(
                    last_time=Max('last_time')
                )

                studied_decks = {uf['deck_flashcard__deck_id']: uf['last_time']
                                 for uf in user_flashcards}

                decks = decks.annotate(
                    last_time=Case(
                        *[When(id=deck_id, then=Value(last_time))
                          for deck_id, last_time in studied_decks.items()],
                        default=Value(None),
                        output_field=DateTimeField()
                    )
                ).order_by('-last_time', '-created_at')
            elif order_by == 'flashcards':
                decks = decks.order_by('-flashcard_count')

            paginator = Paginator(decks, 10)
            page_obj = paginator.get_page(page_number)

            # Formatação da resposta
            response_data = []
            for deck in page_obj:
                serializer = PersonDeckGetSerializer(deck)
                serialized_deck = serializer.data

                user_deck = next(
                    (ud for ud in deck.userdeck_set.all() if ud.user_id == user_id), None)

                response_data.append({
                    **serialized_deck,
                    'situation': None,
                    'flashcards': deck.flashcard_count,
                    'new': user_deck.new if user_deck else 0,
                    'learning': user_deck.learning if user_deck else 0,
                    'reviewing': user_deck.reviewing if user_deck else 0,
                    'favorite': user_deck.favorite if user_deck else 0,
                })

            if not response_data:
                return JsonResponse({
                    "success": False,
                    'error': ['Não foi possível encontrar decks.']},
                    status=status.HTTP_404_NOT_FOUND)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'decks': response_data,
                'flashcardMin': flashcard_min,
                'flashcardMax': flashcard_max,
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
            return JsonResponse({'success': False, 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)