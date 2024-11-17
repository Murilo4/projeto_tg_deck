from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ...serializers_flashcard import CreateFlashCardSerializer
from ...serializers_flashcard import DeckFlashcardExampleSerializer
from ...serializers_flashcard import DeckFlashcardTranslationSerializer
from ...WordAudioSerializer import ExampleCreateSerializer
from ...WordAudioSerializer import TranslationCreateSerializer
from ...models import UserFlashCard, FlashcardPhoto
from ...models import DeckFlashCard, UserDeck, Deck
from ...models import Pronunciation, DeckFlashcardPronunciation
from ...validation.validation_jwt import validate_jwt
from ...models import Example, Translation
import requests
from firebase_admin import storage
import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import io
import threading
from django.db import transaction


def update_flashcard_data(deckId, user_id):
    try:
        # Buscar o Deck com o deckId
        user_flashcards = UserFlashCard.objects.filter(
            deck_flashcard__deck_id=deckId, user_id=user_id)

        # Contagem de flashcards por situação
        count_new = user_flashcards.filter(situation="New").count()
        count_learning = user_flashcards.filter(situation="Learning").count()
        count_reviewing = user_flashcards.filter(situation="Reviewing").count()

        # Buscar o UserDeck para o usuário e o deck em questão
        user_deck, created = UserDeck.objects.get_or_create(
            user_id=user_id, deck_id=deckId)

        user_deck.new = count_new
        user_deck.learning = count_learning
        user_deck.reviewing = count_reviewing

        # Salvar as alterações no UserDeck
        user_deck.save()

        # Retornar resposta de sucesso após a atualização
        return JsonResponse({"success": True,
                             "message": ["Flashcard data updated successfully."]},
                            status=200)

    except Deck.DoesNotExist:
        # Caso o Deck não seja encontrado
        return JsonResponse({"success": False, 
                             "message": ["Deck not found."]}, 
                            status=404)
    except Exception as e:
        # Caso ocorra algum erro inesperado
        return JsonResponse({"success": False,
                             "message": [f"An error occurred: {str(e)}"]},
                            status=500)


def initialize_firebase():
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not firebase_admin._apps:  # Verifica se já há algum app inicializado
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': "flashvibe-13cf5.appspot.com"
        })


initialize_firebase()


def generate_audio_filename(
        keyword, country, sex, voice_name):
    formatted_keyword = keyword.replace(" ", "_")
    formatted_country = country.upper().replace(" ", "_")
    formatted_sex = sex.lower()
    formatted_voice_name = voice_name.replace(
        " ", "_")

    filename = f"{formatted_keyword}_{formatted_country}_{formatted_sex}_{formatted_voice_name}.mp3"
    return filename


def upload_audio_from_url_to_firebase(
        audio_url, keyword, country, sex, voice_name):
    response = requests.get(audio_url)

    if response.status_code == 200:
        filename = generate_audio_filename(keyword, country, sex, voice_name)

        bucket = storage.bucket()

        folder_path = "pronunciations/"
        file_path = f"{folder_path}{filename}"
        print(f"Arquivo será salvo em: {file_path}")

        blob = bucket.blob(file_path)

        audio_data = io.BytesIO(response.content)

        try:
            blob.upload_from_file(audio_data, content_type="audio/mp3")
            audio_url = blob.public_url
            return audio_url
        except Exception:
            raise Exception("falha ao buscar os arquivos")
    else:
        raise Exception("Falha ao baixar o áudio da URL.")


@csrf_exempt
@api_view(['POST'])
def create_flashcard(request, deckId):
    if request.method == "POST":
        try:
            # Extrair dados da requisição
            keyword = request.data.get('keyword')
            main_phrase = request.data.get('mainPhrase')
            if not keyword:
                return JsonResponse({"success": False,
                                     "error": "Palavra chave não encontrada"},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not main_phrase:
                return JsonResponse({"success": False,
                                     "error": "Frase não encontrada"},
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
            with transaction.atomic():
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
                        user_id=user_id,
                        situation="New"
                    )

                    # Processar exemplos
                    examples = request.data.get('examples', [])
                    for example_data in examples:
                        text_example = example_data.get('textExample')

                        if not text_example:
                            return JsonResponse({"success": False,
                                                "error": ["Exemplo inválido"]},
                                                status=status.HTTP_400_BAD_REQUEST)

                        # Tentar buscar o exemplo existente
                        example = Example.objects.filter(
                            text_example=text_example).first()

                        if not example:
                            example_data = {'text_example': text_example}
                            example_serializer = ExampleCreateSerializer(
                                data=example_data)

                            if example_serializer.is_valid(raise_exception=True):
                                example = example_serializer.save()
                                example = Example.objects.get(
                                    text_example=text_example)

                        # Criar relação entre o exemplo e o flashcard do deck
                        new_deck_flashcard_example = {
                            "example": example.id,
                            "deck_flashcard": deck_flashcard.id
                        }

                        flashcard_ex_serializer = DeckFlashcardExampleSerializer(
                            data=new_deck_flashcard_example)
                        if flashcard_ex_serializer.is_valid(
                                raise_exception=True):
                            flashcard_ex_serializer.save()

                    translations = request.data.get('translations', [])
                    for translation_data in translations:
                        text_translation = translation_data.get('textTranslation')
                        if not text_translation:
                            return JsonResponse({"success": False,
                                                "error": ["Tradução inválida"]},
                                                status=status.HTTP_400_BAD_REQUEST)

                        translation = Translation.objects.filter(
                            text_translation=text_translation).first()
                        if not translation:
                            translation_data = {
                                'text_translation': text_translation}
                            translation_serializer = TranslationCreateSerializer(
                                data=translation_data)

                            if translation_serializer.is_valid(
                                    raise_exception=True):
                                translation = translation_serializer.save()
                                translation = Translation.objects.get(
                                    text_translation=text_translation)

                        new_deck_flashcard_translation = {
                            "translation": translation.id,
                            "deck_flashcard": deck_flashcard.id
                        }
                        new = DeckFlashcardTranslationSerializer(
                            data=new_deck_flashcard_translation)
                        if new.is_valid():
                            new.save()

                    # Processar pronúncias
                    pronunciations = request.data.get('pronunciations', [])
                    for pronunciation_data in pronunciations:
                        audio_url = pronunciation_data.get('audioUrl')
                        country = pronunciation_data.get(
                            'country')  # País de origem
                        sex = pronunciation_data.get('sex')  # Sexo da voz
                        voice_name = pronunciation_data.get(
                            'voiceName')  # Nome da voz

                        if not audio_url or not country or not sex or not voice_name:
                            return JsonResponse({
                                "success": False,
                                "error": "Informações da pronúncia inválidas"},
                                status=status.HTTP_404_NOT_FOUND)

                        # Fazer o upload do áudio para o Firebase
                        try:
                            firebase_audio_url = upload_audio_from_url_to_firebase(
                                audio_url, keyword, country, sex, voice_name)
                        except Exception as e:
                            return JsonResponse({
                                "success": False,
                                "error": str(e)},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                        # Salvar a pronúncia no banco de dados
                        pronunciation = Pronunciation.objects.filter(
                            keyword=keyword, audio_url=firebase_audio_url).first()
                        if not pronunciation:
                            pronunciation = Pronunciation(
                                keyword=keyword,
                                audio_url=firebase_audio_url)
                            pronunciation.save()
                            pronunciation = Pronunciation.objects.filter(
                                keyword=keyword,
                                audio_url=firebase_audio_url).first()

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
                                                "error": ["Imagem inválida"]})

                        # Verifica se já existe uma foto com os mesmos dados
                        photo = FlashcardPhoto.objects.filter(
                            deck_flashcard_id=deck_flashcard.id,
                            file_url=image_url,
                            file_description=file_description
                        ).first()

                        # Se não encontrar, cria uma nova
                        if not photo:
                            image = FlashcardPhoto(
                                deck_flashcard_id=deck_flashcard.id,
                                file_url=image_url,
                                file_description=file_description
                            )
                            image.save()

                    threading.Thread(
                        target=update_flashcard_data, args=(
                            deckId, user_id,)).start()
                    return JsonResponse({"success": True,
                                        "message":
                                        ["Flashcard criado com sucesso"]},
                                        status=status.HTTP_201_CREATED)

                return JsonResponse({"success": False,
                                    "error": [flashcard_serializer.errors]},
                                    status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
    

@csrf_exempt
@api_view(['POST'])
def create_multiple_flashcard(request, deckId):
    if request.method == "POST":
        try:
            flashcards_data = request.data.get('flashcards', [])
            if not flashcards_data:
                return JsonResponse({"success": False, "error": "Nenhum flashcard fornecido."},
                                     status=status.HTTP_400_BAD_REQUEST)

            for flashcard_data in flashcards_data:
                # Extrair dados da requisição
                keyword = request.data.get('keyword')
                main_phrase = request.data.get('mainPhrase')
                if not keyword:
                    return JsonResponse({"success": False,
                                        "error": "Palavra chave não encontrada"},
                                        status=status.HTTP_400_BAD_REQUEST)
                if not main_phrase:
                    return JsonResponse({"success": False,
                                        "error": "Frase não encontrada"},
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

                    # Processar exemplos
                    examples = request.data.get('examples', [])
                    for example_data in examples:
                        text_example = example_data.get('textExample')

                        if not text_example:
                            return JsonResponse({"success": False,
                                                "error": ["Exemplo inválido"]},
                                                status=status.HTTP_400_BAD_REQUEST)

                        # Tentar buscar o exemplo existente
                        example = Example.objects.filter(
                            text_example=text_example).first()

                        if not example:
                            example_data = {'text_example': text_example}
                            example_serializer = ExampleCreateSerializer(
                                data=example_data)

                            if example_serializer.is_valid(raise_exception=True):
                                example = example_serializer.save()
                                example = Example.objects.get(
                                    text_example=text_example)

                        # Criar relação entre o exemplo e o flashcard do deck
                        new_deck_flashcard_example = {
                            "example": example.id,
                            "deck_flashcard": deck_flashcard.id
                        }

                        flashcard_ex_serializer = DeckFlashcardExampleSerializer(
                            data=new_deck_flashcard_example)
                        if flashcard_ex_serializer.is_valid(
                                raise_exception=True):
                            flashcard_ex_serializer.save()

                    translations = request.data.get('translations', [])
                    for translation_data in translations:
                        text_translation = translation_data.get('textTranslation')
                        if not text_translation:
                            return JsonResponse({"success": False,
                                                "error": ["Tradução inválida"]},
                                                status=status.HTTP_400_BAD_REQUEST)

                        translation = Translation.objects.filter(
                            text_translation=text_translation).first()
                        if not translation:
                            translation_data = {
                                'text_translation': text_translation}
                            translation_serializer = TranslationCreateSerializer(
                                data=translation_data)

                            if translation_serializer.is_valid(
                                    raise_exception=True):
                                translation = translation_serializer.save()
                                translation = Translation.objects.get(
                                    text_translation=text_translation)

                        new_deck_flashcard_translation = {
                            "translation": translation.id,
                            "deck_flashcard": deck_flashcard.id
                        }
                        new = DeckFlashcardTranslationSerializer(
                            data=new_deck_flashcard_translation)
                        if new.is_valid():
                            new.save()

                    # Processar pronúncias
                    pronunciations = request.data.get('pronunciations', [])
                    for pronunciation_data in pronunciations:
                        audio_url = pronunciation_data.get('audioUrl')
                        country = pronunciation_data.get(
                            'country')  # País de origem
                        sex = pronunciation_data.get('sex')  # Sexo da voz
                        voice_name = pronunciation_data.get(
                            'voiceName')  # Nome da voz

                        if not audio_url or not country or not sex or not voice_name:
                            return JsonResponse({
                                "success": False,
                                "error": "Informações da pronúncia inválidas"},
                                status=status.HTTP_404_NOT_FOUND)

                        # Fazer o upload do áudio para o Firebase
                        try:
                            firebase_audio_url = upload_audio_from_url_to_firebase(
                                audio_url, keyword, country, sex, voice_name)
                        except Exception as e:
                            return JsonResponse({
                                "success": False,
                                "error": str(e)},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                        # Salvar a pronúncia no banco de dados
                        pronunciation = Pronunciation.objects.filter(
                            keyword=keyword, audio_url=firebase_audio_url).first()
                        if not pronunciation:
                            pronunciation = Pronunciation(
                                keyword=keyword,
                                audio_url=firebase_audio_url)
                            pronunciation.save()
                            pronunciation = Pronunciation.objects.filter(
                                keyword=keyword,
                                audio_url=firebase_audio_url).first()

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
                                                "error": ["Imagem inválida"]})

                        # Verifica se já existe uma foto com os mesmos dados
                        photo = FlashcardPhoto.objects.filter(
                            deck_flashcard_id=deck_flashcard.id,
                            file_url=image_url,
                            file_description=file_description
                        ).first()

                        # Se não encontrar, cria uma nova
                        if not photo:
                            image = FlashcardPhoto(
                                deck_flashcard_id=deck_flashcard.id,
                                file_url=image_url,
                                file_description=file_description
                            )
                            image.save()

                    threading.Thread(
                        target=update_flashcard_data, args=(
                            deckId, user_id,)).start()
                    return JsonResponse({"success": True,
                                        "message":
                                         ["Flashcard criado com sucesso"]},
                                        status=status.HTTP_201_CREATED)

                return JsonResponse({"success": False,
                                    "error": [flashcard_serializer.errors]},
                                    status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"success": False,
                             "error": ["Metodo não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

