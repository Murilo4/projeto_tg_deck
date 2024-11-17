from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...serializers_deck import PersonDeckUpdateSerializer
from ...serializers_deck import UDPreferencesUpdateSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, DeckFlashCard, UserFlashCard
from ...models import UserDeckPreferences, DeckFlashcardExample
from ...models import DeckFlashcardPronunciation, DeckFlashcardTranslation
from ...validation.validation_jwt import validate_jwt
from django.db import transaction


@csrf_exempt
@api_view(['PUT'])
def deck_update(request, deckId):
    if request.method != 'PUT':
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
    try:
        deck_id = deckId

        # Verifica o token de autorização
        token = request.headers.get('Authorization')
        if not token:
            return JsonResponse({
                'success': False,
                'error': ['Token de autorização ausente.']
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Valida o token JWT e obtém o ID do usuário
        jwt_data = validate_jwt(token)
        user_id = jwt_data.get('id')

        # Verifica se o UserDeck existe
        user_deck_exists = UserDeck.objects.filter(
            user_id=user_id, deck_id=deck_id).exists()
        try:
            deck = Deck.objects.get(id=deck_id)
        except Deck.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': ['Deck não localizado']
            }, status=status.HTTP_404_NOT_FOUND)

        if not user_deck_exists or deck.type_deck == "Standard":
            return JsonResponse({"success": False,
                                 "error": ["Não autorizado"]},
                                status=status.HTTP_401_UNAUTHORIZED)

        user_deck_count = UserDeck.objects.filter(deck_id=deck_id).count()

        if user_deck_count == 1:
            serializer = PersonDeckUpdateSerializer(
                deck, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                preferences = UserDeckPreferences.objects.get(
                    user_id=user_id, deck_id=deck_id)

                user_deck = UDPreferencesUpdateSerializer(
                    preferences,
                    data=request.data,
                    partial=True)
                if user_deck.is_valid():
                    user_deck.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Deck atualizado'
                }, status=status.HTTP_200_OK)
            else:
                return JsonResponse({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        # Transação atômica para garantir consistência
        with transaction.atomic():
            field_mapping = {
                'deckName': 'title',
                'img': 'image',
                'description': 'description_deck',
                'color': 'color_predefinition'
            }
            translated_data = {
                field_mapping.get(key, key): value for key, value in request.data.items()
            }
            if 'description' in translated_data and not translated_data['description']:
                translated_data['description'] = None

            new_deck_data = {
                field.name: translated_data.get(
                    field.name,
                    getattr(deck, field.name)
                )
                for field in Deck._meta.fields if field.name not in ['id', 'public']
            }

            new_deck_data['public'] = 0
            new_deck = Deck.objects.create(**new_deck_data)

            old_user_deck = UserDeck.objects.filter(
                deck_id=deck_id, user_id=user_id).first()
            old_user_deck.delete()

            UserDeck.objects.create(
                user_id=user_id,
                deck_id=new_deck.id,
                new=old_user_deck.new,
                learning=old_user_deck.learning,
                reviewing=old_user_deck.reviewing,
                favorite=old_user_deck.favorite
            )

            old_preferences = UserDeckPreferences.objects.filter(
                deck_id=deck_id, user_id=user_id).first()
            old_preferences.delete()

            UserDeckPreferences.objects.create(
                deck_id=new_deck.id, user_id=user_id,
                new_per_day=old_preferences.new_per_day,
                learning_per_day=old_preferences.learning_per_day,
                review_per_day=old_preferences.review_per_day
            )
            user_flashcard_ids = set()
            deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)
            for flashcard in deck_flashcards:

                new_flashcard = DeckFlashCard.objects.create(
                    deck_id=new_deck.id,
                    flashcard_id=flashcard.flashcard_id
                )

                examples = DeckFlashcardExample.objects.filter(
                    deck_flashcard_id=flashcard.id)

                translations = DeckFlashcardTranslation.objects.filter(
                    deck_flashcard_id=flashcard.id)

                pronunciations = DeckFlashcardPronunciation.objects.filter(
                    deck_flashcard_id=flashcard.id)

                for example in examples:
                    DeckFlashcardExample.objects.create(
                        deck_flashcard_id=new_flashcard.id,
                        example_id=example.id)

                for translation in translations:
                    DeckFlashcardTranslation.objects.create(
                        deck_flashcard_id=flashcard.id,
                        translation_id=translation.id)

                for pr in pronunciations:
                    DeckFlashcardPronunciation.objects.create(
                        deck_flashcard_id=new_flashcard.id,
                        pronunciation_id=pr.id)

                user_flashcard = UserFlashCard.objects.filter(
                    deck_flashcard_id=flashcard.id,
                    user_id=user_id).first()

                user_flashcards = UserFlashCard.objects.filter(
                    deck_flashcard_id=flashcard.id,
                    user_id=user_id)

                for flashcard_user in user_flashcards:
                    user_flashcard_ids.add(flashcard_user.deck_flashcard.id)

                new_flashcard = UserFlashCard.objects.create(
                    user_id=user_flashcard.user_id,
                    deck_flashcard_id=new_flashcard.id,
                    situation=user_flashcard.situation,
                    one_star=user_flashcard.one_star,
                    two_stars=user_flashcard.two_stars,
                    three_stars=user_flashcard.three_stars,
                    four_stars=user_flashcard.four_stars,
                    five_stars=user_flashcard.five_stars,
                    last_feedback=user_flashcard.last_feedback,
                    last_time=user_flashcard.last_time
                )
            for ids in user_flashcard_ids:
                old_user_flashcard = UserFlashCard.objects.filter(
                    deck_flashcard_id=ids)
                old_user_flashcard.delete()

            serializer = PersonDeckUpdateSerializer(
                new_deck, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Deck atualizado'
                }, status=status.HTTP_200_OK)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Erro ao atualizar o deck',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({'success': False,
                             'error': [str(e)]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
