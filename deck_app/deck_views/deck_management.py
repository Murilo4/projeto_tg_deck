from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ..serializers_deck import PersonDeckGetSerializer
from ..serializers_deck import PersonDeckUpdateSerializer
from ..serializers_deck import PersonDeckGetStandardSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..models import Deck, UserDeck, DeckFlashCard, UserFlashCard
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator
from ..validation.validation_jwt import validate_jwt
from django.db.models import Count
from ..validation.validation_session import validate_session
from django.db.models.functions import Coalesce


@csrf_exempt
@api_view(['GET'])
def get_all_decks(request, page_number):
    if request.method == 'GET':
        try:
            validate_session()

            token = request.COOKIES.get('Authorization')
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Busca UserStandardDeck para o usuário
            user_decks = UserDeck.objects.filter(
                user_id=user_id).values_list('deck_id', flat=True)
            deck_ids = list(user_decks)

            # Busca os decks associados
            decks = Deck.objects.filter(id__in=deck_ids)

            paginator = Paginator(decks, 10)
            page_obj = paginator.get_page(page_number)

            # Formatação da resposta
            response_data = []
            flashcard_counts = []  # Para armazenar as contagens de flashcards

            for deck in page_obj:
                serializer = PersonDeckGetSerializer(deck)
                serialized_deck = serializer.data
                user_flashcard = None

                # Buscando dados do UserDeck para o deck atual
                user_deck = UserDeck.objects.filter(
                    deck_id=deck.id, user_id=user_id).first()

                deck_flashcards = DeckFlashCard.objects.filter(
                    deck_id=deck.id
                )
                flashcard_count = deck_flashcards.count()

                if flashcard_count >= 0:
                    flashcard_counts.append(flashcard_count)

                user_flashcard = UserFlashCard.objects.filter(
                    deck_flashcard_id__in=deck_flashcards.values_list(
                        'id', flat=True), user_id=user_id
                ).first()

                response_data.append({
                    **serialized_deck,
                    'situation': {
                        user_flashcard.situation if user_flashcard else None},
                    'flashcards': flashcard_count,
                    'learning': 0,
                    'reviewing': 0,
                    'new': 0,
                    'favorite': user_deck.favorite if user_deck else None,
                    'stars': (
                        (user_flashcard.one_star or 0) |
                        (user_flashcard.two_stars or 0) |
                        (user_flashcard.three_stars or 0) |
                        (user_flashcard.four_stars or 0) |
                        (user_flashcard.five_stars or 0)
                    ) if user_flashcard else 0
                })

            flashcard_min = min(flashcard_counts) if flashcard_counts else 0
            flashcard_max = max(flashcard_counts) if flashcard_counts else 0

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
                                 'message': 'Usuarios não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_standard_decks(request, page_number):
    if request.method == 'GET':
        try:
            validate_session()

            token = request.COOKIES.get('Authorization')
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            user_decks = UserDeck.objects.filter(
                user_id=user_id).values_list('deck_id', flat=True)

            # Filtros da query
            difficult = request.GET.get('difficult', None)
            min_flashcards = request.GET.get('min_flashcards', None)
            max_flashcards = request.GET.get('max_flashcards', None)
            order_by = request.GET.get('order_by', None)

            # Filtrar os decks padrão que não estão nos decks do usuário
            standard_decks = Deck.objects.filter(
                type_deck='Standard').exclude(id__in=user_decks)

            reviews_stats = Deck.objects.aggregate(
                min_reviews=Coalesce(Min('reviews'), 0),
                max_reviews=Max('reviews')
            )

            if difficult:
                standard_decks = standard_decks.filter(difficult=difficult)

            flashcard_counts = DeckFlashCard.objects.values(
                'deck_id').annotate(
                flashcard_count=Count('flashcard_id')
            )

            # Ajuste para incluir decks sem flashcards no filtro de contagem
            flashcard_counts_dict = {
                entry['deck_id']: entry['flashcard_count']
                for entry in flashcard_counts}

            filtered_deck_ids = []
            for deck in standard_decks:
                flashcard_count = flashcard_counts_dict.get(deck.id, 0)
                if ((min_flashcards is None or flashcard_count >= int(
                    min_flashcards)) and
                        (max_flashcards is None or flashcard_count <= int(
                            max_flashcards))):
                    filtered_deck_ids.append(deck.id)

            # Filtrar os decks com os IDs resultantes
            standard_decks = standard_decks.filter(id__in=filtered_deck_ids)

            # Ordenação
            if order_by == 'newest':
                standard_decks = standard_decks.order_by('-created_at')
            elif order_by == 'oldest':
                standard_decks = standard_decks.order_by('created_at')
            elif order_by == 'recently-modified':
                standard_decks = standard_decks.order_by('-updated_at')
            elif order_by == 'best-rating':
                standard_decks = standard_decks.order_by('-stars')

            paginator = Paginator(standard_decks, 10)
            page_obj = paginator.get_page(page_number)

            # Serializar os decks filtrados
            standard_decks_serializer = PersonDeckGetStandardSerializer(
                page_obj, many=True)

            response_data = []
            for index, deck in enumerate(page_obj):
                flashcard_count = flashcard_counts_dict.get(deck.id, 0)
                response_data.append({
                    **standard_decks_serializer.data[index],
                    'flashcards': flashcard_count
                })

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'standard_decks': response_data,
                'min_reviews': reviews_stats['min_reviews'],
                'max_reviews': reviews_stats['max_reviews'],
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'pageNumber': page_number,
                'totalPages': paginator.num_pages
            }, status=status.HTTP_200_OK)

        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuários não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
def get_deck(request):
    if request.method == 'GET':
        deck_id = request.data.get('deckId')
        try:
            validate_session()

            token = request.COOKIES.get('Authorization')

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            custom_decks = Deck.objects.get(id=deck_id)
            custom_decks_serializer = PersonDeckGetSerializer(custom_decks)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'custom_decks': custom_decks_serializer.data
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuarios não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['PUT'])
def deck_update(request):
    if request.method == 'PUT':
        try:
            deck_id = request.COOKIES.get('deckId')
            validate_session()

            token = request.headers.get('Authorization')

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            user_deck_exists = UserDeck.objects.filter(
                user_id=user_id, deck_id=deck_id).exists()
            try:
                deck = Deck.objects.get(id=deck_id)
            except Deck.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Deck não localizado'
                }, status=status.HTTP_404_NOT_FOUND)

            if not user_deck_exists:
                return JsonResponse({"sucess": False,
                                     "message":
                                    "Não autorizado"},
                                    status=status.HTTP_401_UNAUTHORIZED)

            if deck.type_deck == "Standard":
                return JsonResponse({"sucess": False,
                                    "message":
                                     "Não autorizado"},
                                    status=status.HTTP_401_UNAUTHORIZED)
            user_deck = UserDeck.objects.filter(deck_id=deck_id).count() > 1
            if user_deck:
                new_deck_data = {field.name: getattr(
                    deck, field.name) for field in Deck._meta.fields
                    if field.name not in ['id', 'public']}

                # Altera o campo 'public'
                new_deck_data['public'] = 0
                new_deck = Deck.objects.create(**new_deck_data)

                # Desvincular o usuário do deck antigo
                UserDeck.objects.filter(
                    deck_id=deck_id, user_id=user_id).delete()

                # Associar o novo deck ao usuário
                UserDeck.objects.create(user_id=user_id, deck_id=new_deck.id)

                # Atualizar o novo deck com os dados recebidos
                serializer = PersonDeckUpdateSerializer(
                    new_deck, data=request.data, partial=True)
            else:
                # Se existir apenas um registro, atualize-o
                serializer = PersonDeckUpdateSerializer(
                    deck, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({
                    'success': True,
                    'message': 'deck atualizado'},
                    status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': False,
                                     'message':
                                     'Não foi possivel validar os dados'},
                                    status=status.HTTP_400_BAD_REQUEST)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                'message': 'Usuario não localizado'},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
def delete_deck(request):
    if request.method == 'DELETE':
        try:
            deck_id = request.data.get('deckId')
            validate_session()

            token = request.COOKIES.get('Authorization')

            # Função de validação do JWT
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)
            deck_user = UserDeck.objects.filter(
                deck_id=deck_id, user_id=user_id)
            if deck_user is None:
                return JsonResponse({'success': False,
                                     'message':
                                     'Deck não encontrado para este usuário'},
                                    status=status.HTTP_404_NOT_FOUND)
            # Busca o Deck completo usando o ID
            deck = Deck.objects.filter(id=deck_id).first()
            if deck is None:
                return JsonResponse({'success': False,
                                     'message':
                                     'Deck não encontrado para este usuário'},
                                    status=status.HTTP_404_NOT_FOUND)
            # Verificação do tipo de deck e remoção conforme necessário
            if deck.type_deck == 'Custom' and deck.public == 0:
                deck_user.delete()
                deck.delete()

            elif deck.type_deck == 'Custom' and deck.public == 1:
                user_deck = UserDeck.objects.filter(
                    deck_id=deck_id).count() > 1

                if user_deck:
                    deck_user.delete()
            elif deck.type_deck == 'Standard':
                # Remove apenas da tabela UserDeck
                deck_user.delete()

            # Retorna a resposta de sucesso
            return JsonResponse({
                'success': True,
                'message': 'Deck removido com sucesso.',
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuário não encontrado'},
                                status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def add_deck_to_user(request):
    deck_id = request.data.get('deckId')
    try:
        token = request.COOKIES.get('Authorization')

        jwt_data = validate_jwt(token)
        user_id = jwt_data.get('id')

        if not deck_id:
            return JsonResponse({'success': False,
                                 'message': 'Deck não encontrado.'},
                                status=status.HTTP_404_NOT_FOUND)

        if UserDeck.objects.filter(user_id=user_id, deck_id=deck_id).exists():
            return JsonResponse({"success": False,
                                 "message": "Deck já pertence ao usuário."},
                                status=status.HTTP_409_CONFLICT)

        standard_deck = Deck.objects.get(Q(id=deck_id) & (
            Q(type_deck="Standard") | Q(type_deck="Custom")) & Q(public=1))

        user_standard_deck = UserDeck.objects.create(
            user_id=user_id, deck_id=standard_deck.id)

        if user_standard_deck is None:
            return JsonResponse({"success": False,
                                 "message": "Erro ao adicionar deck"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Adicionando flashcards do deck para o usuário
        deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)
        for deck_flashcard in deck_flashcards:
            UserFlashCard.objects.create(
                user_id=user_id,
                deck_flashcard_id=deck_flashcard.id,
                situation="new"  # ou o valor padrão desejado
            )

        return JsonResponse({'success': True,
                             'message': 'Deck adicionados com sucesso'},
                            status=status.HTTP_201_CREATED)

    except Deck.DoesNotExist:
        return JsonResponse({'success': False,
                             'message': 'Deck não encontrado.'},
                            status=status.HTTP_404_NOT_FOUND)
