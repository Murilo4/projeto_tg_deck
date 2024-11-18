from django.utils import timezone
from ...models import UserFlashCard, UserDeckPreferences
from ...models import DeckFlashcardPronunciation
from ...models import DeckFlashcardExample, DeckFlashCard
from ...models import FlashCardPriority, FlashCard, FlashcardPhoto
from ...models import DeckFlashcardTranslation, Deck
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...validation.validation_jwt import validate_jwt
from ...serializers_flashcard import FlashCardGetallSerializer


@api_view(["POST"])
def study_flashcard(request, flashcardId, deckId, star_rating):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return JsonResponse({
                'success': False,
                'error': ['Token de autorização ausente.']
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Validando o JWT e recuperando o user_id
        jwt_data = validate_jwt(token)
        user_id = jwt_data.get('id')

        if not user_id:
            return JsonResponse({'success': False,
                                'error': ['userId é necessário']},
                                status=status.HTTP_400_BAD_REQUEST)

        deck_flashcard = DeckFlashCard.objects.filter(flashcard_id=flashcardId,
                                                      deck_id=deckId)
        user_flashcard = UserFlashCard.objects.get(
                deck_flashcard_id=deck_flashcard.id,
                user_id=user_id
            )

        # Atualiza o campo de estrela com base no feedback do usuário
        if star_rating == 1:
            user_flashcard.one_star += 1
        elif star_rating == 2:
            user_flashcard.two_stars += 1
        elif star_rating == 3:
            user_flashcard.three_stars += 1
        elif star_rating == 4:
            user_flashcard.four_stars += 1
        elif star_rating == 5:
            user_flashcard.five_stars += 1

        # Atualiza o último feedback e a última vez estudado
        user_flashcard.last_feedback = star_rating
        user_flashcard.last_time = timezone.now()

        # Calcula o número total de exibições somando as avaliações
        total_exhibitions = (
            user_flashcard.one_star +
            user_flashcard.two_stars +
            user_flashcard.three_stars +
            user_flashcard.four_stars +
            user_flashcard.five_stars
        )

        if user_flashcard.situation == "New" and total_exhibitions >= 1:
            user_flashcard.situation = "Learning"
        elif user_flashcard.situation == "Learning" and total_exhibitions >= 5:
            user_flashcard.situation = "Reviewing"
        
        # Salva as alterações no banco de dados
        user_flashcard.save()

        weights = {
            1: 5,
            2: 4,
            3: 3,
            4: 2,
            5: 1
        }

        # Calcula a pontuação ponderada
        total_weighted_score = (
            user_flashcard.one_star * weights[1] +
            user_flashcard.two_stars * weights[2] +
            user_flashcard.three_stars * weights[3] +
            user_flashcard.four_stars * weights[4] +
            user_flashcard.five_stars * weights[5]
        )

        last_feedback_weight = weights.get(user_flashcard.last_feedback, 0)
        total_weighted_score += last_feedback_weight * 2

        # Calcula a média ponderada da prioridade
        total_counts = total_exhibitions + 2
        if total_counts > 0:
            new_priority = total_weighted_score / total_counts
        else:
            new_priority = 3.0  # Valor padrão se não houver feedbacks

        # Atualiza ou cria a prioridade no FlashCardPriority
        flashcard_priority, created = FlashCardPriority.objects.get_or_create(
            deck_flashcard_id=deck_flashcard.id,
            user_id=user_id
        )
        flashcard_priority.priority = new_priority
        flashcard_priority.save()

        return JsonResponse({
            'success': True,
            'message':
            'Estado do flashcard e prioridade atualizados com sucesso.',
        }, status=status.HTTP_200_OK)

    except UserFlashCard.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Flashcard do usuário não encontrado.'
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_flashcards_for_study(request, deckId):
    if request.method == 'GET':
        try:
            # Recuperando o token de autenticação
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente.']
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Validando o JWT e recuperando o user_id
            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'error': ['userId é necessário']},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Buscando as preferências do usuário para o deck específico
            try:
                user_deck_preferences = UserDeckPreferences.objects.get(
                    user_id=user_id, deck_id=deckId)
            except UserDeckPreferences.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': ['Preferências de deck não encontradas.']
                }, status=status.HTTP_404_NOT_FOUND)

            # Quantidade de flashcards por dia
            new_per_day = user_deck_preferences.new_per_day
            learning_per_day = user_deck_preferences.learning_per_day
            reviewing_per_day = user_deck_preferences.review_per_day

            # Buscando os flashcards do deck
            deck_flashcard_ids = DeckFlashCard.objects.filter(
                deck_id=deckId).values_list('flashcard_id', flat=True)
            flashcards = FlashCard.objects.filter(
                id__in=deck_flashcard_ids)

            # Flashcards para estudo
            flashcards_to_study = {
                'new_flashcards': [],
                'learning_flashcards': [],
                'review_flashcards': []
            }

            # Flashcards "New"
            new_flashcards = FlashCard.objects.filter(
                id__in=deck_flashcard_ids
            ).prefetch_related(
                'deckflashcard_set__userflashcards'  # Usando a relação reversa
            ).filter(
                deckflashcard__userflashcards__situation='New'
            )[:new_per_day]

            flashcards_to_study['new_flashcards'] = new_flashcards

            # Flashcards "Learning"
            learning_flashcards = FlashCard.objects.filter(
                id__in=deck_flashcard_ids
            ).prefetch_related(
                'deckflashcard_set__userflashcards'  # Usando a relação reversa
            ).filter(
                deckflashcard__userflashcards__situation='Learning'
            )[:learning_per_day]

            flashcards_to_study['learning_flashcards'] = learning_flashcards

            # Flashcards "Reviewing" - Usando next_time da tabela UserFlashCard
            now = timezone.now()  # Obtém o horário atual
            review_flashcards = FlashCard.objects.filter(
                id__in=deck_flashcard_ids
            ).prefetch_related(
                'deckflashcard_set__userflashcards'  # Usando a relação reversa
            ).filter(
                deckflashcard__userflashcards__situation='Reviewing',
                deckflashcard__userflashcards__next_time__lte=now
            )[:reviewing_per_day]

            if not review_flashcards:
                # Buscar os flashcards com a data `next_time` mais próxima
                review_flashcards = FlashCard.objects.filter(
                    id__in=deck_flashcard_ids
                ).prefetch_related(
                    'deckflashcard_set__userflashcards'
                ).filter(
                    deckflashcard__userflashcards__situation='Reviewing',
                    deckflashcard__userflashcards__next_time__gt=now
                ).order_by(
                    'deckflashcard__userflashcards__next_time'
                    )[:reviewing_per_day]

            flashcards_to_study['review_flashcards'] = review_flashcards

            response_data = []
            for situation, flashcards in flashcards_to_study.items():
                for flashcard in flashcards:
                    examples = DeckFlashcardExample.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id
                        ).select_related('example')
                    translations = DeckFlashcardTranslation.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id
                        ).select_related('translation')
                    pronunciations = DeckFlashcardPronunciation.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id
                        ).select_related('pronunciation')
                    images = FlashcardPhoto.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id)

                    flashcard_data = FlashCardGetallSerializer(flashcard).data

                    pronunciation_data = [
                        {
                            'audioUrl': pronunciation.pronunciation.audio_url,
                            'keyword': pronunciation.pronunciation.keyword
                        }
                        for pronunciation in pronunciations
                    ]

                    flashcard_info = {
                        **flashcard_data,
                        'examples': [example.example.text_example for example in examples],
                        'translations': [translation.translation.text_translation for translation in translations],
                        'pronunciations': pronunciation_data,
                        'images': [image.file_url for image in images]
                    }

                    response_data.append(flashcard_info)

            if not response_data:
                return JsonResponse({
                    'success': False,
                    'error': ['Nenhum flashcard encontrado para estudo.']
                }, status=status.HTTP_404_NOT_FOUND)

            deck_name = Deck.objects.filter(id=deckId).first()
            # Retornando os dados dos flashcards para estudo
            return JsonResponse({
                'success': True,
                'message': ['Flashcards para estudo retornados.'],
                'deckName': deck_name.title,
                'flashcards': response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse({"success": False,
                                 "error": str(e)},
                                status=status.HTTP_400_BAD_REQUEST)

    else:
        return JsonResponse({"success": False,
                             "error": ["Método não autorizado"]},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
