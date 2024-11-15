from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...serializers_flashcard import FlashCardGetOneSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import DeckFlashCard
from ...models import FlashCard, DeckFlashcardExample
from ...models import DeckFlashcardTranslation, DeckFlashcardPronunciation


@csrf_exempt
@api_view(['GET'])
def get_one_flashcard(request, flashcardId, deckId):
    if request.method == "GET":
        try:
            flashcard = FlashCard.objects.get(id=flashcardId)

            flashcard_serializer = FlashCardGetOneSerializer(flashcard)

            deck_flashcard = DeckFlashCard.objects.get(
                flashcard=flashcard, deck=deckId)

            examples = DeckFlashcardExample.objects.filter(
                deck_flashcard=deck_flashcard).select_related('example')
            example_data = [{'id': ex.example.id,
                             'textExample': ex.example.text_example} for ex in examples] if examples.exists() else []

            pronunciations = DeckFlashcardPronunciation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('pronunciation')
            pronunciation_data = [{'id': pr.pronunciation.id,
                                   'keyword': pr.pronunciation.keyword,
                                   'audioUrl': pr.pronunciation.audio_url} for pr in pronunciations] if pronunciations.exists() else []

            translations = DeckFlashcardTranslation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('translation')
            translations_data = [{'id': tr.translation.id,
                                  'textTranslation': tr.translation.text_translation} for tr in translations] if translations.exists() else []

            response_data = {
                'keyword': flashcard_serializer.data.get('keyword'),
                'mainPhrase': flashcard_serializer.data.get('mainPhrase'),
                'examples': example_data,
                'translations': translations_data,
                'pronunciations': pronunciation_data,
            }

            return JsonResponse({
                'success': True,
                'flashcard': [response_data]
            }, status=status.HTTP_200_OK)

        except FlashCard.DoesNotExist:
            return JsonResponse({"success": False,
                                 "error": ["FlashCard não encontrado"]},
                                status=status.HTTP_404_NOT_FOUND)
        except DeckFlashCard.DoesNotExist:
            return JsonResponse({"success": False,
                                 "error": ["DeckFlashCard não encontrado"]},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)