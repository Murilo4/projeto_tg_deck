from django.utils import timezone
from ...models import UserFlashCard, UserDeckPreferences
from ...models import DeckFlashcardPronunciation
from ...models import DeckFlashcardExample, DeckFlashCard
from ...models import FlashCardPriority, FlashCard
from ...models import DeckFlashcardTranslation
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import JsonResponse
from ...validation.validation_jwt import validate_jwt
from ...validation.validation_session import validate_session
from ...serializers_flashcard import FlashCardGetSerializer


@api_view(["POST"])
def rate_flashcard(user_flashcard, rating):
    # Atualiza o feedback_score e chama a função para atualizar a prioridade
    user_flashcard.feedback_score = rating
    user_flashcard.save()  # Salva o feedback

    # Atualiza a prioridade com base no novo feedback
    update_flashcard_priority(user_flashcard)


def update_flashcard_priority(deck_flashcard_id, user_id):
    # Busca o UserFlashCard correspondente
    user_flashcard = UserFlashCard.objects.get(
        deck_flashcard_id=deck_flashcard_id,
        user_id=user_id
    )

    # Coleta todos os feedbacks (estrelas) do usuário para o flashcard
    feedbacks = UserFlashCard.objects.filter(
        deck_flashcard_id=deck_flashcard_id,
        user_id=user_id
    ).order_by('-last_time')

    total_weight = 0
    total_score = 0

    if feedbacks.exists():
        # Adiciona o feedback mais recente com peso maior
        recent_feedback = feedbacks.first()
        if recent_feedback.last_feedback is not None:
            total_weight += 2  # Peso maior para o feedback mais recente
            total_score += recent_feedback.last_feedback * 2

        # Adiciona os feedbacks anteriores
        for feedback in feedbacks[1:]:  # Ignora o feedback mais recente
            if feedback.last_feedback is not None:
                total_weight += 1  # Peso normal
                total_score += feedback.last_feedback

    # Calcula a nova média ponderada
    if total_weight > 0:
        new_average = total_score / total_weight
    else:
        new_average = 3.0  # Valor padrão se não houver feedbacks

    # Atualiza ou cria a prioridade no FlashCardPriority
    flashcard_priority, created = FlashCardPriority.objects.get_or_create(
        deck_flashcard_id=deck_flashcard_id,
        user_id=user_id
    )
    flashcard_priority.priority = new_average
    flashcard_priority.save()


@api_view(['GET'])
def get_flashcards_for_study(request, deckId):
    if request.method == 'GET':
        try:
            # Recuperando o token de autenticação
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({
                    'success': False,
                    'error': ['Token de autorização ausente. Faça login novamente.']
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
                    'deckflashcard__userflashcards__next_time')[:reviewing_per_day]

            flashcards_to_study['review_flashcards'] = review_flashcards

            response_data = []
            for situation, flashcards in flashcards_to_study.items():
                for flashcard in flashcards:
                    examples = DeckFlashcardExample.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id).select_related('example')[:2]
                    translations = DeckFlashcardTranslation.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id).select_related('translation')[:2]
                    pronunciations = DeckFlashcardPronunciation.objects.filter(
                        deck_flashcard__flashcard_id=flashcard.id).select_related('pronunciation')[:2]

                    # Formatação dos dados do flashcard
                    flashcard_data = FlashCardGetSerializer(flashcard).data

                    # Obtendo os campos 'audio_url' e 'keyword' das pronúncias
                    pronunciation_data = [
                        {
                            'audio_url': pronunciation.pronunciation.audio_url,
                            'keyword': pronunciation.pronunciation.keyword
                        }
                        for pronunciation in pronunciations
                    ]

                    # Organizando a resposta
                    flashcard_info = {
                        **flashcard_data,
                        'examples': [example.example.text_example for example in examples],
                        'translations': [translation.translation.text_translation for translation in translations],
                        'pronunciations': pronunciation_data
                    }

                    response_data.append(flashcard_info)

            # Se não encontrar flashcards, retorna erro
            if not response_data:
                return JsonResponse({
                    'success': False,
                    'error': ['Nenhum flashcard encontrado para estudo.']
                }, status=status.HTTP_404_NOT_FOUND)

            # Retornando os dados dos flashcards para estudo
            return JsonResponse({
                'success': True,
                'message': ['Flashcards para estudo retornados.'],
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
