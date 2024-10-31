from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..serializers_flashcard import CreateFlashCardSerializer
from ..models import UserFlashCard
from ..models import DeckFlashCard, DeckFlashcardTranslation
from ..models import Pronunciation, DeckFlashcardPronunciation
from ..validation.validation_jwt import validate_jwt
#from ..validation.validation_session import validate_session
from ..models import Example, Translation
from ..models import DeckFlashcardExample


@csrf_exempt
@api_view(['POST'])
def create_flashcard(request, deckId):
    if request.method == "POST":
        try:
            # Extrair dados da requisição
            keyword = request.data.get('keyword')
            main_phrase = request.data.get('mainPhrase')

            token = request.COOKIES.get('jwt_token')
            if not token:
                return JsonResponse({
                    'success': False,
                    'message':
                    'Token de autorização ausente. Faça login novamente.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            # Criar o flashcard
            flashcard_data = {
                "keyword": keyword,
                "main_phrase": main_phrase
            }
            flashcard_serializer = CreateFlashCardSerializer(
                data=flashcard_data)
            if flashcard_serializer.is_valid():
                flashcard = flashcard_serializer.save()

                # Criar relação com o deck
                deck_flashcard = DeckFlashCard.objects.create(
                    flashcard=flashcard,
                    deck_id=deckId
                )

                # Criar a relação entre o usuário e o flashcard
                UserFlashCard.objects.create(
                    deck_flashcard=deck_flashcard,
                    user_id=user_id
                )

                # Processar exemplos
                examples = request.data.get('examples', [])
                for example_data in examples:
                    text_example = example_data.get('textExample')
                    if not text_example:
                        return JsonResponse({"success": False,
                                             "message": "sem exemplos"})

                    # Verificar se o exemplo já existe
                    example, created = Example.objects.get_or_create(
                        text_example=text_example)

                    # Criar relação na tabela intermediária
                    DeckFlashcardExample.objects.create(
                        deck_flashcard=deck_flashcard,
                        example=example
                    )

                # Processar traduções
                translations = request.data.get('translations', [])
                for translation_data in translations:
                    text_translation = translation_data.get('textTranslation')
                    if not text_translation:
                        continue

                    # Verificar se a tradução já existe
                    translation, created = Translation.objects.get_or_create(
                        text_translation=text_translation)

                    # Criar relação na tabela intermediária
                    DeckFlashcardTranslation.objects.create(
                        deck_flashcard=deck_flashcard,
                        translation=translation
                    )

                # Processar pronúncias
                pronunciations = request.data.get('pronunciations', [])
                for pronunciation_data in pronunciations:
                    keyword = pronunciation_data.get('keyword')
                    audio_url = pronunciation_data.get('audioUrl')
                    if not keyword or not audio_url:
                        continue

                    # Verificar se a pronúncia já existe
                    pronunciation, created = Pronunciation.objects.get_or_create(
                        keyword=keyword, audio_url=audio_url)

                    # Criar relação na tabela intermediária
                    DeckFlashcardPronunciation.objects.create(
                        deck_flashcard=deck_flashcard,
                        pronunciation=pronunciation
                    )

                return JsonResponse({"success": True,
                                     "message": "Flashcard criado com sucesso"},
                                    status=status.HTTP_201_CREATED)

            return JsonResponse({"success": False,
                                 "message": flashcard_serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
