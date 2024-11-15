from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import DeckFlashCard, UserFlashCard
from ...models import FlashCard, DeckFlashcardExample
from ...models import DeckFlashcardTranslation, DeckFlashcardPronunciation
from ...models import Example, Translation, Pronunciation, FlashcardPhoto
from ...models import FlashCardPriority
from ...validation.validation_jwt import validate_jwt


@csrf_exempt
@api_view(['DELETE'])
def delete_flashcard(request, flashcardId, deckId):
    if request.method == 'DELETE':
        try:
            if not flashcardId:
                return JsonResponse({"success": False,
                                     "error":
                                    ["É necessario informar o flashcard id"]},
                                    status=status.HTTP_400_BAD_REQUEST)

            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error':
                    ['Token de autorização ausente. Faça login novamente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if user_id is None:
                return JsonResponse({"success": False,
                                     "error":
                                    ["Usuario não autenticado"]},
                                    status=status.HTTP_403_FORBIDDEN)
            try:
                flashcard = FlashCard.objects.filter(id=flashcardId).first()
                deck_flashcard = DeckFlashCard.objects.filter(
                    deck_id=deckId, flashcard_id=flashcardId).first()
                if not flashcard:
                    return JsonResponse({"success": False,
                                         "error":
                                         ["Nenhum flashcard localizado"]},
                                        status=status.HTTP_403_FORBIDDEN)

                delete_images(deck_flashcard)

                # Deletar traduções
                delete_translation(deck_flashcard)

                # Deletar pronúncias
                delete_pronunciation(deck_flashcard)

                # Deletar exemplos
                delete_examples(deck_flashcard)

                # Deletar user_flashcard
                delete_user_flashcard(deck_flashcard, user_id)

                # Deletar o relacionamento no deck_flashcard
                deck_flashcard.delete()

                # Finalmente, deletar o flashcard
                flashcard.delete()

                return JsonResponse({"success": True,
                                     "error":
                                     ["Flashcard deletado com sucesso"]},
                                    status=status.HTTP_200_OK)
            except exceptions.NotFound:
                return JsonResponse({"success": False,
                                     "error":  ["Flashcard não encontrado"]},
                                    status=status.HTTP_404_NOT_FOUND)
        except exceptions.ValidationError:
            return JsonResponse({"success": False,
                                 "error": ["Flashcard não encontrado"]},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
