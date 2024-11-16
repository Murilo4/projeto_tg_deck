from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import Deck, UserDeck, DeckFlashCard, UserFlashCard
from ...models import DeckFlashcardExample, DeckFlashcardTranslation
from ...models import DeckFlashcardPronunciation, FlashCard, Example
from ...models import Translation, Pronunciation, FlashcardPhoto
from ...models import FlashCardPriority
from ...validation.validation_jwt import validate_jwt
from django.db import transaction


@csrf_exempt
@api_view(['DELETE'])
def delete_deck(request, deckId):
    if request.method == 'DELETE':
        try:
            deck_id = deckId

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Função de validação do JWT
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)
            # Verificar se o deck pertence ao usuário
            deck_user = UserDeck.objects.filter(
                deck_id=deck_id, user_id=user_id)
            if not deck_user.exists():
                return JsonResponse({
                    'success': False,
                    'error': ['Deck não encontrado para este usuário']},
                    status=status.HTTP_404_NOT_FOUND)

            deck = Deck.objects.filter(id=deck_id).first()
            if not deck:
                return JsonResponse({
                    'success': False,
                    'error': ['Deck não encontrado']},
                    status=status.HTTP_404_NOT_FOUND)

            # Inicia uma transação atômica
            with transaction.atomic():
                # Obter todos os flashcards do deck
                deck_flashcards = DeckFlashCard.objects.filter(deck_id=deck_id)

                if deck.type_deck == 'Custom' and deck.public == 0:

                    for deck_flashcard in deck_flashcards:
                        print(deck_flashcard.flashcard_id)
                        # Excluir o flashcard associado ao deck
                        delete_flashcard(deck_flashcard.flashcard_id,
                                         deck_flashcard.id, user_id)

                    # Excluir o relacionamento UserDeck e o deck
                    deck_user.delete()
                    deck.delete()

                elif deck.type_deck == 'Custom' and deck.public == 1:
                    user_deck_count = UserDeck.objects.filter(
                        deck_id=deck_id).count()
                    if user_deck_count > 1:
                        deck_user.delete()
                    else:
                        # Excluir flashcards associados ao deck, um por vez
                        for deck_flashcard in deck_flashcards:
                            # Excluir o flashcard associado ao deck
                            delete_flashcard(deck_flashcard.flashcard_id, 
                                             deck_flashcard.id, user_id)
                        deck_user.delete()
                        deck.delete()

                elif deck.type_deck == 'Standard':
                    deck_user.delete()

                    # Excluir flashcards associados ao deck para o usuário
                    deck_flashcard_ids = [deck_flashcard.id for deck_flashcard in deck_flashcards]
                    user_flashcards = UserFlashCard.objects.filter(
                        user_id=user_id,
                        deck_flashcard_id__in=deck_flashcard_ids
                    )
                    user_flashcards.delete()

                # Se chegamos até aqui, tudo ocorreu bem e a transação é confirmada automaticamente
                return JsonResponse({
                    'success': True,
                    'message': ['Deck removido com sucesso.'],
                })

        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'error': ['Usuário não encontrado']},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


def delete_flashcard(flashcardId, deckflashcard_id, user_id):
    print(flashcardId, deckflashcard_id, user_id)
    flashcard = FlashCard.objects.filter(id=flashcardId).first()
    print(flashcard)
    deck_flashcard = DeckFlashCard.objects.filter(
        id=deckflashcard_id, flashcard_id=flashcardId).first()

    print("alo", deck_flashcard)
    delete_images(deck_flashcard)

    delete_translation(deck_flashcard)

    delete_pronunciation(deck_flashcard)

    delete_examples(deck_flashcard)

    delete_user_flashcard(deck_flashcard, user_id)

    deck_flashcard.delete()

    flashcard.delete()


def delete_examples(deck_flashcard):
    try:
        examples = DeckFlashcardExample.objects.filter(
            deck_flashcard_id=deck_flashcard.id)
        for example in examples:
            more_one_example = DeckFlashcardExample.objects.filter(
                example_id=example.example_id).count() > 1
            if more_one_example:
                dlt_deck_flashcard_example = DeckFlashcardExample.objects.get(
                    example_id=example.example_id)
                dlt_deck_flashcard_example.delete()
            else:
                dlt_deck_flashcard_example = DeckFlashcardExample.objects.get(
                    example_id=example.example_id)
                delete_example = Example.objects.get(
                    id=example.example_id)
                dlt_deck_flashcard_example.delete()
                delete_example.delete()
    except exceptions.NotFound:
        return False
    deleted_examples = True
    return deleted_examples


def delete_translation(deck_flashcard):
    try:
        translations = DeckFlashcardTranslation.objects.filter(
            deck_flashcard_id=deck_flashcard.id)
        for translation in translations:
            more_one_translation = DeckFlashcardTranslation.objects.filter(
                translation_id=translation.translation_id).count() > 1
            if more_one_translation:
                dlt_deck_flashcard_tr = DeckFlashcardTranslation.objects.get(
                    translation_id=translation.translation_id,
                    deck_flashcard_id=deck_flashcard.id)
                dlt_deck_flashcard_tr.delete()
            else:
                dlt_deck_flashcard_tr = DeckFlashcardTranslation.objects.get(
                    translation_id=translation.translation_id,
                    deck_flashcard_id=deck_flashcard.id)
                delete_tr = Translation.objects.get(
                    id=translation.translation_id)
                dlt_deck_flashcard_tr.delete()
                delete_tr.delete()
        deleted_translation = True
        return deleted_translation
    except exceptions.NotFound:
        return False


def delete_pronunciation(deck_flashcard):
    try:
        audios = DeckFlashcardPronunciation.objects.filter(
            deck_flashcard_id=deck_flashcard.id
        )
        for audio in audios:
            more_one_audio = DeckFlashcardPronunciation.objects.filter(
                pronunciation_id=audio.pronunciation_id).count() > 1
            if more_one_audio:
                delete_deck_pr = DeckFlashcardPronunciation.objects.get(
                    pronunciation_id=audio.id)
                delete_deck_pr.delete()
            else:
                delete_deck_pr = DeckFlashcardPronunciation.objects.get(
                    pronunciation_id=audio.pronunciation_id)
                delete_deck_pr.delete()
                delete_pr = Pronunciation.objects.get(
                    id=audio.pronunciation_id)
                delete_pr.delete()
        deleted_translation = True
        return deleted_translation
    except exceptions.NotFound:
        return False


def delete_images(deck_flashcard):
    try:
        images = FlashcardPhoto.objects.filter(
            deck_flashcard_id=deck_flashcard.id
        )
        for image in images:
            image.delete()
        deleted_images = True
        return deleted_images
    except exceptions.NotFound:
        return False


def delete_user_flashcard(deck_flashcard, user_id):
    try:
        user_flashcard = UserFlashCard.objects.filter(
            deck_flashcard_id=deck_flashcard.id,
            user_id=user_id)
        if user_flashcard:
            user_flashcard.delete()
            deleted_user_flashcard = True
        else:
            deleted_user_flashcard = False

        user_priority = FlashCardPriority.objects.filter(
            deck_flashcard_id=deck_flashcard.id,
            user_id=user_id)
        if user_priority:
            user_priority.delete()
            deleted_user_priority = True
        else:
            deleted_user_priority = False

        return deleted_user_flashcard, deleted_user_priority
    except exceptions.NotFound:
        return False
