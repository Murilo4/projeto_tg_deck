from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
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
    if request.method == 'PUT':
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

            if not user_deck_exists:
                return JsonResponse({"success": False,
                                     "error": ["Não autorizado"]},
                                    status=status.HTTP_401_UNAUTHORIZED)

            if deck.type_deck == "Standard":
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
                        'error': ['Não foi possível validar os dados']
                    }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                new_deck_data = {field.name: getattr(
                    deck, field.name) for field in Deck._meta.fields
                                 if field.name not in ['id', 'public']}
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

                deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)
                for flashcard in deck_flashcards:
                    new_flashcard = DeckFlashCard.objects.create(
                        deck_id=new_deck.id,
                        flashcard_id=flashcard.id,
                    )

                    deck_flashcard_id = new_flashcard.id

                    for user_flashcard in UserFlashCard.objects.filter(
                            deck_flashcard_id=deck_flashcard_id):

                        UserFlashCard.objects.create(
                            user_id=user_flashcard.user_id,
                            deck_flashcard_id=new_flashcard.id,
                            new=user_flashcard.new,
                            learning=user_flashcard.learning,
                            review=user_flashcard.review,
                            favorite=user_flashcard.favorite
                        )
                        # Deleta o UserFlashCard antigo
                        user_flashcard.delete()

                    for deck_flashcard_ex in DeckFlashcardExample.objects.filter(
                            deck_flashcard_id=deck_flashcard_id):
                        DeckFlashcardExample.objects.create(
                            deck_flashcard_id=new_flashcard.id,
                            example_text=deck_flashcard_ex.example_text
                        )

                    for deck_flashcard_tr in DeckFlashcardTranslation.objects.filter(
                            deck_flashcard_id=deck_flashcard_id):
                        DeckFlashcardTranslation.objects.create(
                            deck_flashcard_id=new_flashcard.id,
                            translation_text=deck_flashcard_tr.translation_text
                        )

                    for deck_flashcard_pr in DeckFlashcardPronunciation.objects.filter(
                            deck_flashcard_id=deck_flashcard_id):
                        DeckFlashcardPronunciation.objects.create(
                            deck_flashcard_id=new_flashcard.id,
                            pronunciation_url=deck_flashcard_pr.pronunciation_url
                        )

                serializer = PersonDeckUpdateSerializer(
                    new_deck, data=request.data, partial=True
                )

                # Valida e salva o serializer
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({
                        'success': True,
                        'message': 'Deck atualizado'
                    }, status=status.HTTP_200_OK)
                else:
                    return JsonResponse({
                        'success': False,
                        'error': ['Não foi possível validar os dados']
                    }, status=status.HTTP_400_BAD_REQUEST)

        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuário não localizado']},
                                status=status.HTTP_400_BAD_REQUEST)

    else:
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
