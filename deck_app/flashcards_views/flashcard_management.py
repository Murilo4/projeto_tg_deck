from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ..serializers_flashcard import FlashCardGetSerializer
from ..serializers_flashcard import UserFlashCardGetSerializer
from ..serializers_flashcard import FlashCardGetOneSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..models import Deck, DeckFlashCard, UserFlashCard
from ..models import FlashCard, DeckFlashcardExample
from ..models import DeckFlashcardTranslation, DeckFlashcardPronunciation
from ..models import Example, Translation, Pronunciation
from django.core.paginator import Paginator
from django.db.models import Max
from ..validation.validation_jwt import validate_jwt
from ..validation.validation_session import validate_session


@csrf_exempt
@api_view(['GET'])
def get_all_flashcard(request, page_number, deckId):
    if request.method == 'GET':
        deck_id = deckId
        try:
            validate_session()

            token = request.COOKIES.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    'Token de autorização ausente. Faça login novamente.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            order_by = request.GET.get('orderBy', None)
            new = request.GET.get('New', None)
            learning = request.GET.get('Learning', None)
            reviewing = request.GET.get('Reviewing', None)

            # Busca UserStandardDeck para o usuário
            deck_flashcard_ids = DeckFlashCard.objects.filter(
                deck_id=deck_id).values_list('flashcard_id', flat=True)

            flashcards = FlashCard.objects.filter(id__in=deck_flashcard_ids)

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

            # Filtra os FlashCards que têm UserFlashCards correspondentes
            flashcards = flashcards.filter(id__in=user_flashcards_qs.values_list(
                'deck_flashcard__flashcard_id', flat=True))

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
                recent_deck_ids = [
                    uf['deck_flashcard__deck_id'] for uf in user_flashcards]
                flashcards = flashcards.filter(id__in=recent_deck_ids)

            paginator = Paginator(flashcards, 10)
            page_obj = paginator.get_page(page_number)

            # Formatação da resposta
            response_data = []
            for flashcard in page_obj:

                serializer = FlashCardGetSerializer(flashcard)
                serialized_flashcard = serializer.data
                user_flashcard = None

                # Buscando dados do UserDeck para o deck atual
                deck_flashcard = DeckFlashCard.objects.filter(
                    deck_id=deck_id, flashcard_id=flashcard.id).first()
                user_flashcard = UserFlashCard.objects.filter(
                    deck_flashcard_id=deck_flashcard.id, user_id=user_id
                ).first() if deck_flashcard else None
                user_flashcard_serializer = UserFlashCardGetSerializer(
                    user_flashcard)

                serialized_user_flashcard = user_flashcard_serializer.data if user_flashcard else None

                response_data.append({
                    **serialized_flashcard,
                    **serialized_user_flashcard,
                    'situation':
                    user_flashcard.situation if user_flashcard else None,
                })
            deck_name = Deck.objects.filter(id=deck_id).first()
            if response_data == []:
                return JsonResponse({"success": False,
                                    'message':
                                     'Não foi possível encontrar flashcards.'},
                                    status=status.HTTP_404_NOT_FOUND)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'deck':  deck_name.title,
                'flashcard': response_data,
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'pageNumber': page_number,
                'totalPages': paginator.num_pages,
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuarios não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def update_flashcard(request, flashcardId,  deckId):
    if request.method == "PUT":
        try:
            flashcard_id = flashcardId
            deck_id = deckId

            if flashcard_id is None:
                return JsonResponse({"success": False,
                                    "message":
                                     "Não foi possivel localizar o flashcard"},
                                    status=status.HTTP_404_NOT_FOUND)

            # validate_session()

            token = request.COOKIES.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    'Token de autorização ausente. Faça login novamente.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            deck = Deck.objects.get(id=deck_id)

            if deck.type_deck == "Standard":
                return JsonResponse({"success": False,
                                     "message":
                                     "Você não tem permissão para alterar este flashcard"},
                                    status=status.HTTP_403_FORBIDDEN)
            deck_flashcard = DeckFlashCard.objects.get(
                flashcard_id=flashcard_id, deck_id=deck_id)

            user_flashcards = UserFlashCard.objects.filter(
                deck_flashcard_id=deck_flashcard.id).count() > 1

            flashcard = FlashCard.objects.get(id=flashcard_id)
            if user_flashcards:
                # Criando um novo flashcard com os dados do flashcard original
                new_flashcard_data = {field.name: getattr(flashcard, field.name)
                                    for field in FlashCard._meta.fields if field.name != 'id'}
                new_flashcard = FlashCard.objects.create(**new_flashcard_data)

                # Criando o deck_flashcard com a relação entre o novo flashcard e o deck
                serializer_deck_flashcard = DeckFlashCard.objects.create(
                    flashcard_id=new_flashcard.id, deck_id=deck_id
                )

                # Filtrando os dados do UserFlashCard e convertendo para um dicionário
                user_flashcard_data = UserFlashCard.objects.filter(
                    deck_flashcard_id=deck_flashcard.id, user_id=user_id
                ).values().first()

                # Atualizando com um novo dicionário contendo deck_flashcard_id e user_id
                new_user_flashcard = {
                    'deck_flashcard_id': serializer_deck_flashcard.id,
                    'user_id': user_id
                }
                # Criando o UserFlashCard usando os dados como dicionário
                UserFlashCard.objects.create(**new_user_flashcard)

                # Validando e salvando o novo flashcard criado
                serializer_flashcard = FlashCardGetSerializer(
                    new_flashcard, data=request.data, partial=True)

                if serializer_flashcard.is_valid():
                    serializer_flashcard.save()

                    if serializer_deck_flashcard:
                        user_flashcard_data = UserFlashCard.objects.filter(
                            deck_flashcard_id=deck_flashcard.id, user_id=user_id
                        ).delete()

                        serializer_deck_flashcard.save()
                    else:
                        return JsonResponse({"success": False,
                                            "message": "Erro ao atualizar flashcard"},
                                            status=status.HTTP_400_BAD_REQUEST)

            if 'examples' in request.data:
                examples_data = request.data['examples']
                existing_examples = {ex.id: ex for ex in Deck.objects.filter(
                    deck_flashcard_id=deck_flashcard.id)}

                for example_data in examples_data:
                    example_id = example_data.get('id')
                    if example_id:
                        # Atualizar ou criar exemplo existente
                        example_instance = Example.objects.update_or_create(
                            defaults=example_data,  # Atualizar ou criar o exemplo
                            id=example_id
                        )[0]
                        # Adicionar ou atualizar na tabela intermediária
                        DeckFlashcardExample.objects.update_or_create(
                            deck_flashcard_id=deck_flashcard.id,
                            example_id=example_instance.id,
                        )
                    else:
                        # Se o ID não for fornecido, criar um novo exemplo
                        example_instance = Example.objects.create(**example_data)
                        DeckFlashcardExample.objects.create(
                            deck_flashcard_id=deck_flashcard.id,
                            example_id=example_instance.id)

                # Remover exemplos que não estão mais na requisição
                existing_example_ids = set(existing_examples.keys())
                new_example_ids = {ex.get('id') for ex in examples_data if 'id' in ex}
                ids_to_delete_examples = existing_example_ids - new_example_ids
                DeckFlashcardExample.objects.filter(
                    example_id__in=ids_to_delete_examples,
                    deck_flashcard_id=deck_flashcard.id).delete()

            # Atualizar pronúncias
            if 'pronunciations' in request.data:
                pronunciations_data = request.data['pronunciations']
                existing_pronunciations = {pr.id: pr for pr in DeckFlashcardPronunciation.objects.filter(deck_flashcard_id=deck_flashcard.id)}

                for pronunciation_data in pronunciations_data:
                    pronunciation_id = pronunciation_data.get('id')
                    if pronunciation_id:
                        pronunciation_instance = Pronunciation.objects.update_or_create(
                            defaults=pronunciation_data,
                            id=pronunciation_id
                        )[0]
                        DeckFlashcardPronunciation.objects.update_or_create(
                            deck_flashcard_id=deck_flashcard.id,
                            pronunciation_id=pronunciation_instance.id,
                        )
                    else:
                        pronunciation_instance = Pronunciation.objects.create(**pronunciation_data)
                        DeckFlashcardPronunciation.objects.create(
                            deck_flashcard_id=deck_flashcard.id,
                            pronunciation_id=pronunciation_instance.id)

                existing_pronunciation_ids = set(existing_pronunciations.keys())
                new_pronunciation_ids = {pr.get('id') for pr in pronunciations_data if 'id' in pr}
                ids_to_delete_pronunciations = existing_pronunciation_ids - new_pronunciation_ids
                DeckFlashcardPronunciation.objects.filter(pronunciation_id__in=ids_to_delete_pronunciations, deck_flashcard_id=deck_flashcard.id).delete()

            # Atualizar traduções
            if 'translations' in request.data:
                translations_data = request.data['translations']
                existing_translations = {tr.id: tr for tr in DeckFlashcardTranslation.objects.filter(deck_flashcard_id=deck_flashcard.id)}

                for translation_data in translations_data:
                    translation_id = translation_data.get('id')
                    if translation_id:
                        translation_instance = Translation.objects.update_or_create(
                            defaults=translation_data,
                            id=translation_id
                        )[0]
                        DeckFlashcardTranslation.objects.update_or_create(
                            deck_flashcard_id=deck_flashcard.id,
                            translation_id=translation_instance.id,
                        )
                    else:
                        translation_instance = Translation.objects.create(**translation_data)
                        DeckFlashcardTranslation.objects.create(
                            deck_flashcard_id=deck_flashcard.id, 
                            translation_id=translation_instance.id)

                existing_translation_ids = set(existing_translations.keys())
                new_translation_ids = {tr.get('id') for tr in translations_data if 'id' in tr}
                ids_to_delete_translations = existing_translation_ids - new_translation_ids
                DeckFlashcardTranslation.objects.filter(
                    translation_id__in=ids_to_delete_translations,
                    deck_flashcard_id=deck_flashcard.id).delete()

                return JsonResponse({"success": True,
                                    "message":
                                    "Atualização realizada com sucesso"},
                                    status=status.HTTP_201_CREATED)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                'message': 'Usuario não localizado'},
                                status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_one_flashcard(request, flashcardId, deckId):
    if request.method == "GET":
        try:
            # Obtendo o flashcard específico
            flashcard = FlashCard.objects.get(id=flashcardId)

            # Serializando os dados do flashcard
            flashcard_serializer = FlashCardGetOneSerializer(flashcard)

            # Buscando dados relacionados (exemplos, pronúncias, traduções)
            deck_flashcard = DeckFlashCard.objects.get(flashcard=flashcard,
                                                       deck=deckId)
            # Usando prefetch_related
            examples = DeckFlashcardExample.objects.filter(
                deck_flashcard=deck_flashcard).select_related('example')
            for ex in examples:
                print(ex.example.id, ex.example.text_example)
            example_data = [{'id': ex.example.id, 'text_example': ex.example.text_example} for ex in examples] if examples.exists() else []
            

            pronunciations = DeckFlashcardPronunciation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('pronunciation')
            pronunciation_data = [{'id': pr.pronunciation.id, 'keyword': pr.pronunciation.keyword, 
                                   'audio_url': pr.pronunciation.audio_url} for pr in pronunciations] if pronunciations.exists() else []

            translations = DeckFlashcardTranslation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('translation')
            translations_data = [{'id': tr.translation.id,
                                  'text': tr.translation.text}
                                for tr in translations] if translations.exists() else []

            response_data = {
                'flashcard': flashcard_serializer.data,
                'examples': example_data,
                'pronunciations': pronunciation_data,
                'translations': translations_data,
            }

            return JsonResponse({
                'success': True,
                'data': response_data
            }, status=status.HTTP_200_OK)

        except FlashCard.DoesNotExist:
            return JsonResponse({"success": False, "message": "FlashCard não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except DeckFlashCard.DoesNotExist:
            return JsonResponse({"success": False, "message": "DeckFlashCard não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@api_view(['DELETE'])
def delete_flashcard(request, flashcardId):
    if request.method == 'DELETE':
        try:
            flashcard_id = request.data.get('flascardId')

            if not flashcard_id:
                return JsonResponse({"success"})

            token = request.COOKIES.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    'Token de autorização ausente. Faça login novamente.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')
        except:
            ...