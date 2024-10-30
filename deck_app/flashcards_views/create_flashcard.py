from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions
from ..serializers_flashcard import CreateFlashCardSerializer
from ..serializers_flashcard import UserFlashCardSerializer
from ..serializers_flashcard import DeckFlashcardSerializer
from ..WordAudioSerializer import TranslationCreateSerializer
from ..validation.validation_jwt import validate_jwt
from ..validation.validation_session import validate_session
from ..models import Translation, DeckFlashcardTranslation
from ..models import DeckFlashcardExample


@csrf_exempt
@api_view(['POST'])
def create_flashcard(request):
    if request.method == 'POST':
        try:
            deck_id = request.data.get('deckId')
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
            word = request.data.get('keyWord')
            main_phrase = request.data.get('mainPhrase')
            translated_word = request.data.get('translatedWord', None)

            if not word:
                return JsonResponse({'success': False,
                                    'message': 'Palavra chave não encontrada'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not main_phrase:
                return JsonResponse({'success': False,
                                    'message':
                                     'Frase principal não encontrada'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'Usuario não encontrado'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not deck_id:
                return JsonResponse({'success': False,
                                    'message': 'Deck não encontrado'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if word.lower() not in main_phrase:
                return JsonResponse({'success': False,
                                    'message':
                                     'Palavra chave não encontrada na frase'},
                                    status=status.HTTP_400_BAD_REQUEST)

            new_flashcard = {
                'keyword': word,
                'main_phrase': main_phrase,
            }
            serializer = CreateFlashCardSerializer(data=new_flashcard)
            if serializer.is_valid(raise_exception=True):
                flashcard = serializer.save()  # Salva o flashcard

                flashcard_id = flashcard.id
                new_deck_flashcard = {
                    'flashcard_id': flashcard_id,
                    'deck_id': deck_id
                }
                deck_flashcard_serializer = DeckFlashcardSerializer(
                    data=new_deck_flashcard)
                if deck_flashcard_serializer.is_valid(raise_exception=True):
                    deck_flashcard = deck_flashcard_serializer.save()

                    deck_flashcard_id = deck_flashcard.id
                    new_user_flashcard = {
                        'user_id': user_id,
                        'deck_flashcard_id': deck_flashcard_id,
                        'situation': "New"
                    }
                    user_serializer = UserFlashCardSerializer(
                        data=new_user_flashcard)

                    if user_serializer.is_valid(raise_exception=True):
                        user_serializer.save()
                        if translated_word is not None:
                            new_translated_word = TranslationCreateSerializer(
                                data=translated_word)
                            if new_translated_word.is_valid(raise_exception=True):
                                new_translated_word.save()
                        DeckFlashcardTranslation.objects.create(
                                deck_flashcard_id=deck_flashcard_id,
                                translated_id=new_translated_word.id
                        )
                        examples_data = request.data.get(
                                    'examples', [])
                        if not examples_data:
                            return JsonResponse({'success': False,
                                                'message':
                                                 'Exemplos não encontrados'},
                                                status=status.HTTP_400_BAD_REQUEST)
                        for example_text in examples_data:
                            exemple = Translation.objects.create(
                                text_example=example_text)

                            DeckFlashcardExample.objects.create(
                                deck_flashcard_id=deck_flashcard_id,
                                exemple=exemple.id
                            )

                        return JsonResponse({'success': True,
                                            'message':
                                             'Flashcard criado com sucesso'},
                                            status=status.HTTP_201_CREATED)
                    else:
                        return JsonResponse({'success': False,
                                            'message':
                                             'Não foi possivel validar'},
                                            status=status.HTTP_400_BAD_REQUEST)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message':
                                 'não foi possivel validar os dados'},
                                status=status.HTTP_404_NOT_FOUND)
    else:
        return JsonResponse({'success': False,
                             'message': 'Método não suportado'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
