from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..serializers_flashcard import CreateFlashCardSerializer
from ..serializers_flashcard import DeckFlashcardExampleSerializer
from ..serializers_flashcard import DeckFlashcardTranslationSerializer
from ..WordAudioSerializer import ExampleCreateSerializer
from ..WordAudioSerializer import TranslationCreateSerializer
from ..models import UserFlashCard, FlashcardPhoto
from ..models import DeckFlashCard
from ..models import Pronunciation, DeckFlashcardPronunciation
from ..validation.validation_jwt import validate_jwt
# from ..validation.validation_session import validate_session
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
                    'message': 'Token de autorização ausente. Faça login novamente.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            # Criar o flashcard
            flashcard_data = {
                "keyword": keyword,
                "main_phrase": main_phrase
            }
            flashcard_serializer = CreateFlashCardSerializer(data=flashcard_data)
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
                        return JsonResponse({"success": False, "message": "Exemplo inválido"})

                    # Tentar buscar o exemplo existente
                    example = Example.objects.filter(text_example=text_example).first()

                    if example:
                        print(f"Exemplo encontrado: {example.id} - {example.text_example}")
                    else:
                        # Criar novo exemplo
                        example_data = {'text_example': text_example}
                        example_serializer = ExampleCreateSerializer(data=example_data)
                        
                        if example_serializer.is_valid(raise_exception=True):
                            example = example_serializer.save()  # Salva o novo exemplo
                            example = Example.objects.get(text_example=text_example)
                            print(f"Novo exemplo criado: {example.id} - {example.text_example}")

                    # Criar relação entre o exemplo e o flashcard do deck
                    new_deck_flashcard_example = {
                        "example": example.id,  # Aqui usamos o exemplo encontrado ou criado
                        "deck_flashcard": deck_flashcard.id
                    }

                    deck_flashcard_example_serializer = DeckFlashcardExampleSerializer(data=new_deck_flashcard_example)
                    if deck_flashcard_example_serializer.is_valid(raise_exception=True):
                        deck_flashcard_example_serializer.save()
                        print("Relação de exemplo salva com sucesso.")
                    

                # Processar traduções
                translations = request.data.get('translations', [])
                for translation_data in translations:
                    text_translation = translation_data.get('textTranslation')
                    if not text_translation:
                        return JsonResponse({"success": False, "message": "Tradução inválida"})

                    # Tentar buscar a tradução existente
                    translation = Translation.objects.filter(
                        text_translation=text_translation).first()
                    if translation:
                        print(f"Tradução encontrada: {translation.id} - {translation.text_translation}")
                    else:
                        # Criar nova tradução
                        translation_data = {'text_translation': text_translation}
                        translation_serializer = TranslationCreateSerializer(
                            data=translation_data)
                        
                        if translation_serializer.is_valid(raise_exception=True):
                            translation = translation_serializer.save()  # Salva a nova tradução
                            translation = Translation.objects.get(
                                text_translation=text_translation)
                            print(f"Nova tradução criada: {translation.id} - {translation.text_translation}")

                    new_deck_flashcard_translation = {
                        "translation": translation.id,  # Aqui usamos o exemplo encontrado ou criado
                        "deck_flashcard": deck_flashcard.id
                    }
                    # Criar relação entre a tradução e o flashcard do deck
                    new = DeckFlashcardTranslationSerializer(data=new_deck_flashcard_translation)
                    if new.is_valid():
                        new.save()

                # Processar pronúncias
                pronunciations = request.data.get('pronunciations', [])
                for pronunciation_data in pronunciations:
                    keyword = pronunciation_data.get('keyword')
                    audio_url = pronunciation_data.get('audioUrl')
                    if not keyword or not audio_url:
                        return JsonResponse({"success": False, 
                                             "message": "Áudio inválido"})

                    pronunciation = Pronunciation.objects.filter(keyword=keyword, audio_url=audio_url).first()
                    if pronunciation:
                        print(f"Pronúncia encontrada: {pronunciation.id} - {pronunciation.keyword}")
                    else:
                        pronunciation = Pronunciation(keyword=keyword, audio_url=audio_url)
                        pronunciation.save()
                        pronunciation = Pronunciation.objects.get(keyword=keyword, audio_url=audio_url)
                        print(f"Nova pronúncia criada: {pronunciation.id} - {pronunciation.keyword}")

                    DeckFlashcardPronunciation.objects.create(
                        pronunciation=pronunciation,
                        deck_flashcard=deck_flashcard
                    )

                img = request.data.get('images', [])
                for image_data in img:
                    image_url = image_data.get('imageUrl')
                    file_description = image_data.get('description')

                    if not image_url or not file_description:
                        return JsonResponse({"success": False,
                                             "message": "Áudio inválido"})

                    image = FlashcardPhoto.objects.filter(deck_flashcard_id=deck_flashcard,
                                                          image_url=image_url,
                                                          file_description=file_description)
                    if not image:
                        image = FlashcardPhoto.objects.create(deck_flashcard_id=deck_flashcard,
                                                              image_url=image_url,
                                                              file_description=file_description)
                        image.save()

                return JsonResponse({"success": True,
                                     "message":
                                    "Flashcard criado com sucesso"},
                                    status=status.HTTP_201_CREATED)

            return JsonResponse({"success": False,
                                 "message": flashcard_serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


# from firebase_config import bucket
# from werkzeug.utils import secure_filename

# @api_view(['POST'])
# def upload_audio(request):
#     if 'file' not in request.FILES:
#         return Response({'success': False, 'message': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

#     audio_file = request.FILES['file']
#     filename = secure_filename(audio_file.name)

#     # Fazer o upload para o Firebase Storage
#     blob = bucket.blob(f'temp_audios/{filename}')
#     blob.upload_from_file(audio_file, content_type=audio_file.content_type)

#     # Obter a URL do arquivo
#     audio_url = blob.public_url

#     return Response({'success': True, 'url': audio_url}, status=status.HTTP_201_CREATED)