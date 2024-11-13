from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ...serializers_deck import PersonDeckGetSerializer
from ...serializers_deck import PersonDeckUpdateSerializer
from ...serializers_deck import PersonDeckGetStandardSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, DeckFlashCard, UserFlashCard
from ...models import UserDeckPreferences
from django.db.models import Q, Max
from django.core.paginator import Paginator
from ...validation.validation_jwt import validate_jwt
from django.db.models import Count
from ...validation.validation_session import validate_session
from ..Flashcards.flashcard_management import delete_flashcard


@csrf_exempt
@api_view(['GET'])
def get_all_decks(request, page_number):
    if request.method == 'GET':
        try:

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            order_by = request.GET.get('orderBy', None)
            min_flashcards = request.GET.get('minFlashcards', None)
            max_flashcards = request.GET.get('maxFlashcards', None)
            favorite_filter = request.GET.get('favorites', None)
            learning_filter = request.GET.get('learning', None)
            reviewing_filter = request.GET.get('finished', None)

            # Busca UserStandardDeck para o usuário
            user_decks = UserDeck.objects.filter(user_id=user_id).values_list(
                'deck_id', flat=True)
            deck_ids = list(user_decks)

            # Busca os decks associados
            decks = Deck.objects.filter(id__in=deck_ids)

            if favorite_filter == 'true':
                decks = decks.filter(
                    userdeck__user_id=user_id, userdeck__favorite=True)
            if learning_filter == 'true':
                decks = decks.filter(
                    userdeck__user_id=user_id, userdeck__learning=True)

            if reviewing_filter == 'true':
                decks = decks.filter(
                    userdeck__user_id=user_id, userdeck__reviewing=True)
            # Conta os flashcards em cada deck
            flashcard_counts = DeckFlashCard.objects.values(
                'deck_id').annotate(
                flashcard_count=Count('flashcard_id')
            )

            # Dicionário para contar flashcards de cada deck
            flashcard_counts_dict = {
                entry['deck_id']: entry[
                    'flashcard_count'] for entry in flashcard_counts}

            flashcard_counts_list = []

            filtered_deck_ids = []
            for deck in decks:
                flashcard_count = flashcard_counts_dict.get(deck.id, 0)
                if ((min_flashcards is None or flashcard_count >= int(
                    min_flashcards)) and
                        (max_flashcards is None or flashcard_count <= int(
                            max_flashcards))):
                    filtered_deck_ids.append(deck.id)
                    flashcard_counts_list.append(flashcard_count)

            decks = decks.filter(id__in=filtered_deck_ids)

            decks = decks.annotate(
                flashcard_count=Count('deckflashcard'))

            # Adicionar a ordenação por flashcards aqui
            if order_by == 'newer':
                decks = decks.order_by('-created_at')
            elif order_by == 'older':
                decks = decks.order_by('created_at')
            elif order_by == 'lastModifications':
                decks = decks.order_by('-updated_at')
            elif order_by == 'lastStudied':
                user_flashcards = UserFlashCard.objects.filter(
                    user_id=user_id).values(
                        'deck_flashcard__deck_id').annotate(
                            last_time=Max('last_time'))
                recent_deck_ids = [
                    uf['deck_flashcard__deck_id'] for uf in user_flashcards]
                decks = decks.filter(id__in=recent_deck_ids)
            elif order_by == 'flashcards':
                # Ordenação pela contagem de flashcards (decks com mais flashcards)
                decks = decks.order_by('-flashcard_count')

            paginator = Paginator(decks, 10)
            page_obj = paginator.get_page(page_number)

            # Formatação da resposta
            response_data = []
            for deck in page_obj:
                serializer = PersonDeckGetSerializer(deck)
                serialized_deck = serializer.data
                user_flashcard = None

                # Busca o UserDeck associado ao deck atual
                user_deck = UserDeck.objects.filter(
                    deck_id=deck.id, user_id=user_id).first()

                deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck.id)

                flashcard_count = deck_flashcards.count()

                user_preferences = UserDeckPreferences.objects.filter(
                    deck_id=deck.id, user_id=user_id).first()

                user_flashcard = UserFlashCard.objects.filter(
                    deck_flashcard_id__in=deck_flashcards.values_list(
                        'id', flat=True), user_id=user_id
                ).first()

                response_data.append({
                    **serialized_deck,
                    'situation': user_flashcard.situation if user_flashcard else None,
                    'flashcards': flashcard_count,
                    'new': user_preferences.new_per_day if user_preferences else 0,
                    'learning': user_preferences.learning_per_day if user_preferences else 0,
                    'reviewing': user_preferences.review_per_day if user_preferences else 0,
                    'favorite': user_deck.favorite if user_deck else 0,
                    'stars': (
                        (user_flashcard.one_star or 0) |
                        (user_flashcard.two_stars or 0) |
                        (user_flashcard.three_stars or 0) |
                        (user_flashcard.four_stars or 0) |
                        (user_flashcard.five_stars or 0)
                    ) if user_flashcard else 0
                })

            flashcard_min = min(
                flashcard_counts_list) if flashcard_counts_list else 0
            flashcard_max = max(
                flashcard_counts_list) if flashcard_counts_list else 0

            if response_data == []:
                return JsonResponse({"success": False,
                                    'message':
                                     ['Não foi possível encontrar decks.']},
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
                                 'message': ['Usuários não encontrados']},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "message": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
    

@csrf_exempt
@api_view(['GET'])
def get_all_decks_to_user(request, userId):
    if request.method == 'GET':
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')
            if not user_id:
                return JsonResponse({
                    "success": False,
                    "error": ["Token inválido"]
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Buscar todos os decks relacionados ao usuário
            decks = Deck.objects.filter(user_id=user_id)

            # Se não encontrar nenhum deck
            if not decks.exists():
                return JsonResponse({
                    "success": False,
                    "error": ["Nenhum deck encontrado para este usuário."]
                }, status=status.HTTP_404_NOT_FOUND)

            # Serializa os decks encontrados
            serializer = PersonDeckGetSerializer(decks, many=True)

            # Retorna a lista de decks
            return JsonResponse({
                "success": True,
                "decks": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
def get_standard_decks(request, page_number):
    if request.method == 'GET':
        try:

            token = request.headers.get('Authorization')

            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            user_decks = UserDeck.objects.filter(
                user_id=user_id).values_list('deck_id', flat=True)

            # Filtros da query
            difficult = request.GET.get('difficult', None)
            order_by = request.GET.get('orderBy', None)
            min_reviews = request.GET.get('minReviews', None)
            max_reviews = request.GET.get('maxReviews', None)

            # Filtrar os decks padrão que não estão nos decks do usuário
            standard_decks = Deck.objects.filter(
                type_deck='Standard').exclude(id__in=user_decks)

            # Filtragem de reviews
            if min_reviews is not None:
                standard_decks = standard_decks.filter(
                    reviews__gte=int(min_reviews))
            if max_reviews is not None:
                standard_decks = standard_decks.filter(
                    reviews__lte=int(max_reviews))

            if difficult:
                standard_decks = standard_decks.filter(difficult=difficult)

            # Anotação de contagem de flashcards
            standard_decks = standard_decks.annotate(
                flashcard_count=Count('deckflashcard'))

            # Ordenação conforme especificado
            if order_by == 'newest':
                standard_decks = standard_decks.order_by('-created_at')
            elif order_by == 'oldest':
                standard_decks = standard_decks.order_by('created_at')
            elif order_by == 'recentlyModified':
                standard_decks = standard_decks.order_by('-updated_at')
            elif order_by == 'bestRating':
                standard_decks = standard_decks.order_by('-stars')
            elif order_by == 'flashcard':
                standard_decks = standard_decks.order_by('-flashcard_count')

            # Paginando os resultados
            paginator = Paginator(standard_decks, 10)
            page_obj = paginator.get_page(page_number)

            # Serialização
            standard_decks_serializer = PersonDeckGetStandardSerializer(
                page_obj, many=True)

            # Resposta
            response_data = []
            reviews_counts_list = []

            for index, deck in enumerate(page_obj):
                reviews_counts_list.append(deck.reviews)
                flashcard_count = deck.flashcard_count if hasattr(
                    deck, 'flashcard_count') else 0
                response_data.append({
                    **standard_decks_serializer.data[index],
                    'flashcards': flashcard_count
                })

            # Calcular mínimo e máximo de reviews
            reviews_min = min(
                reviews_counts_list) if reviews_counts_list else 0
            reviews_max = max(
                reviews_counts_list) if reviews_counts_list else 0
            if not response_data:
                return JsonResponse({"success": False,
                                     'message':
                                    ['Não foi possível encontrar decks.']},
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
                                 'message': ['Usuários não encontrados']},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "message": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['GET'])
def get_deck(request, deckId):
    if request.method == 'GET':
        deck_id = deckId
        try:
            validate_session()

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            custom_decks = Deck.objects.get(id=deck_id)
            custom_decks_serializer = PersonDeckGetSerializer(custom_decks)
            # deck_data = {
            #     'type': custom_decks_serializer.data.get("type_deck"),
            #     'colorPredefinition': custom_decks_serializer.data.get(
            #         "color_predefinition"),
            #     'title': custom_decks_serializer.data.get("title"),
            #     'image': custom_decks_serializer.data.get("image"),
            #     'lastModification': custom_decks_serializer.data.get(
            #         "lastModification"), 
            #     'createdData': custom_decks_serializer.data.get("createdData"),
            #     'description': custom_decks_serializer.data.get(
            #         "description_deck"),
            #     'public': custom_decks_serializer.data.get("public"),
            #     'difficult': custom_decks_serializer.data.get("difficult"),
            #     'stars': custom_decks_serializer.data.get("stars"),
            #     'reviews': custom_decks_serializer.data.get("reviews"),
            #     'favorite': custom_decks_serializer.data.get("favorite"),
            #     'flashcards': custom_decks_serializer.data.get("flashcards"),
            #     'last_time': custom_decks_serializer.data.get("last_time")
            # }
            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'custom_decks': [custom_decks_serializer.data]
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


@csrf_exempt
@api_view(['PUT'])
def deck_update(request, deckId):
    if request.method == 'PUT':
        try:
            deck_id = deckId
            validate_session()

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            user_deck_exists = UserDeck.objects.filter(
                user_id=user_id, deck_id=deck_id).exists()
            try:
                deck = Deck.objects.get(id=deck_id)
            except Deck.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': ['Deck não localizado']
                }, status=status.HTTP_404_NOT_FOUND)

            if not user_deck_exists:
                return JsonResponse({"sucess": False,
                                     "error":
                                    ["Não autorizado"]},
                                    status=status.HTTP_401_UNAUTHORIZED)

            if deck.type_deck == "Standard":
                return JsonResponse({"sucess": False,
                                    "error":
                                    ["Não autorizado"]},
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
                user_deck_serializer = UserDeck.objects.create(
                    user_id=user_id, deck_id=new_deck.id)

                if user_deck_serializer.is_valid():
                    user_deck_serializer.save()

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
                                     'error':
                                     ['Não foi possivel validar os dados']},
                                    status=status.HTTP_400_BAD_REQUEST)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                'error': ['Usuario não localizado']},
                                status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['DELETE'])
def delete_deck(request, deckId):
    if request.method == 'DELETE':
        try:
            deck_id = deckId
            validate_session()

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Função de validação do JWT
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)
            deck_user = UserDeck.objects.filter(
                deck_id=deck_id, user_id=user_id)
            if not deck_user:
                return JsonResponse({'success': False,
                                     'error': ['Deck não encontrado para este usuário']},
                                    status=status.HTTP_404_NOT_FOUND)
            # Busca o Deck completo usando o ID
            deck = Deck.objects.filter(id=deck_id).first()
            if not deck:
                return JsonResponse({'success': False,
                                     'error': ['Deck não encontrado para este usuário']},
                                    status=status.HTTP_404_NOT_FOUND)
            
            # Agora, antes de deletar o deck, deletar todos os flashcards associados ao deck
            deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)
            
            for deck_flashcard in deck_flashcards:
                flashcard_id = deck_flashcard.flashcard_id
                # Chama a função de delete_flashcard passando os parâmetros necessários
                delete_flashcard(request, flashcard_id, deck_id)

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
                'message': ['Deck removido com sucesso.'],
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuário não encontrado']},
                                status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['POST'])
def add_deck_to_user(request, deckId):
    if request.method == 'POST':
        deck_id = deckId
        try:
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not deck_id:
                return JsonResponse({'success': False,
                                    'error': ['Deck não encontrado.']},
                                    status=status.HTTP_404_NOT_FOUND)

            if UserDeck.objects.filter(user_id=user_id, deck_id=deck_id).exists():
                return JsonResponse({"success": False,
                                    "error": ["Deck já pertence ao usuário."]},
                                    status=status.HTTP_409_CONFLICT)

            standard_deck = Deck.objects.get(Q(id=deck_id) & (
                Q(type_deck="Standard") | Q(type_deck="Custom")) & Q(public=1))

            user_standard_deck = UserDeck.objects.create(
                user_id=user_id, deck_id=standard_deck.id)

            if user_standard_deck is None:
                return JsonResponse({"success": False,
                                    "error": ["Erro ao adicionar deck"]},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Adicionando flashcards do deck para o usuário
            deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)
            for deck_flashcard in deck_flashcards:
                UserFlashCard.objects.create(
                    user_id=user_id,
                    deck_flashcard_id=deck_flashcard.id,
                    situation="new"
                )

            return JsonResponse({'success': True,
                                'message': ['Deck adicionados com sucesso']},
                                status=status.HTTP_201_CREATED)

        except Deck.DoesNotExist:
            return JsonResponse({'success': False,
                                'error': ['Deck não encontrado.']},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['GET'])
def cron_job(request):
    return JsonResponse({'message': ['Cron job executed successfully']},
                        status=status.HTTP_200_OK)
