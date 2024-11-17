from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...serializers_flashcard import FlashCardGetOneSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...models import DeckFlashCard
from ...models import FlashCard, DeckFlashcardExample, FlashcardPhoto
from ...models import DeckFlashcardTranslation, DeckFlashcardPronunciation
from django.core.cache import cache
import re

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

            pronunciation_data = []
            for pr in pronunciations:
                # Extrair dados da URL da pronúncia usando regex
                pronunciation_url = pr.pronunciation.audio_url
                
                # Expressão regular ajustada para capturar a URL
                match = re.search(r'pronunciations/([a-zA-Z]+)_([a-zA-Z_]+)_(f|m)_(\w+).mp3', pronunciation_url)

                if match:
                    keyword = match.group(1)
                    country = match.group(2)
                    sex = match.group(3)
                    voice_name = match.group(4)

                    # Validação de valores de 'sex'
                    if sex not in ['f', 'm']:
                        return JsonResponse({'success': False, 
                                             'error': 'Valor de sex inválido. Deve ser "f" ou "m".'},
                                             status=status.HTTP_400_BAD_REQUEST)

                    pronunciation_data.append({
                        'id': pr.pronunciation.id,
                        'keyword': keyword,
                        'country': country.replace('_', ' '),  # Substituir _ por espaço se necessário
                        'sex': sex,
                        'voiceName': voice_name,
                        'audioUrl': pronunciation_url
                    })
                else:
                    pronunciation_data.append({
                        'id': pr.pronunciation.id,
                        'audioUrl': pronunciation_url
                    })

            translations = DeckFlashcardTranslation.objects.filter(
                deck_flashcard=deck_flashcard).select_related('translation')
            translations_data = [{'id': tr.translation.id,
                                  'textTranslation': tr.translation.text_translation} for tr in translations] if translations.exists() else []
            
            images = FlashcardPhoto.objects.filter(
                deck_flashcard=deck_flashcard)
            image_data = [{'id': img.id,
                    'fileUrl': img.file_url,
                    'fileDescription': img.file_description} for img in images] if images.exists() else []

            response_data = {
                'keyword': flashcard_serializer.data.get('keyword'),
                'mainPhrase': flashcard_serializer.data.get('main_phrase'),
                'examples': example_data,
                'translations': translations_data,
                'pronunciations': pronunciation_data,
                'images': image_data
            }

            return JsonResponse({
                'success': True,
                "message": "flashcard retornado com sucesso",
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