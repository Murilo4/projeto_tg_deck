from django.utils import timezone
from ...models import UserFlashCard, UserDeckPreferences
from ...models import DeckFlashcardPronunciation
from ...models import DeckFlashcardExample, DeckFlashCard
from ...models import FlashCardPriority, FlashCard, FlashcardPhoto
from ...models import DeckFlashcardTranslation, Deck
from rest_framework import status
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from ...validation.validation_jwt import validate_jwt
from ...serializers_flashcard import FlashCardGetallSerializer
from datetime import timedelta


@csrf_exempt
@api_view(["POST"])
def study_flashcard(request, flashcardId, deckId, star_rating):
    try:
        # Verificação do token de autorização
        token = request.headers.get('Authorization')
        if not token:
            return JsonResponse({
                'success': False,
                'error': ['Token de autorização ausente.']
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Validação do JWT
        jwt_data = validate_jwt(token)
        user_id = jwt_data.get('id')

        if not user_id:
            return JsonResponse({'success': False,
                                'error': ['userId é necessário']},
                                status=status.HTTP_400_BAD_REQUEST)

        # Obter deck_flashcard e user_flashcard
        deck_flashcard = DeckFlashCard.objects.get(
            flashcard_id=flashcardId,
            deck_id=deckId)

        user_flashcard = UserFlashCard.objects.get(
            deck_flashcard_id=deck_flashcard,
            user_id=user_id
        )

        # Garantir que contadores não sejam None
        user_flashcard.one_star = user_flashcard.one_star or 0
        user_flashcard.two_stars = user_flashcard.two_stars or 0
        user_flashcard.three_stars = user_flashcard.three_stars or 0
        user_flashcard.four_stars = user_flashcard.four_stars or 0
        user_flashcard.five_stars = user_flashcard.five_stars or 0

        # Atualizar contadores com base na avaliação
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

        # Atualizar feedback e última data de estudo
        user_flashcard.last_feedback = star_rating
        user_flashcard.last_time = timezone.now()

        # Total de exibições
        total_exhibitions = (
            user_flashcard.one_star +
            user_flashcard.two_stars +
            user_flashcard.three_stars +
            user_flashcard.four_stars +
            user_flashcard.five_stars
        )

        # Atualizar situação do flashcard
        if user_flashcard.situation == "New" and total_exhibitions >= 1:
            user_flashcard.situation = "Learning"
        elif user_flashcard.situation == "Learning" and total_exhibitions >= 5:
            user_flashcard.situation = "Reviewing"

        user_flashcard.save()

        # Pesos e cálculo de prioridade
        weights = {
            1: 5,
            2: 4,
            3: 3,
            4: 2,
            5: 1
        }

        try:
            last_feedback_weight = weights.get(user_flashcard.last_feedback, 0)
            total_weighted_score = (
                user_flashcard.one_star * weights[1] +
                user_flashcard.two_stars * weights[2] +
                user_flashcard.three_stars * weights[3] +
                user_flashcard.four_stars * weights[4] +
                user_flashcard.five_stars * weights[5] +
                last_feedback_weight * 2
            )

            total_counts = total_exhibitions + 2
            new_priority = total_weighted_score / total_counts if total_counts > 0 else 3.0
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao calcular a prioridade: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Atualizar FlashCardPriority
        flashcard_priority, created = FlashCardPriority.objects.get_or_create(
            deck_flashcard_id=deck_flashcard.id,
            user_id=user_id
        )
        flashcard_priority.priority = new_priority

        base_days = star_rating
        max_days = 15  # Máximo espaçamento
        adjustment_factor = 0.2  # Fator de ajuste para reduzir espaçamento geral
        next_study_days = base_days + \
            int((max_days - base_days) * (5 - new_priority) / 5 * adjustment_factor)

        # Tempo desde a última revisão
        reviewing_time = (timezone.now() - user_flashcard.last_time).days
        # Aumento gradual com o tempo (5% a cada 30 dias)
        dynamic_factor = 1 + (reviewing_time / 30) * 0.05

        # Aplicar fator dinâmico de aumento de espaçamento
        next_study_days = int(next_study_days * dynamic_factor)

        next_study_days = min(next_study_days, max_days)

        last_time = user_flashcard.last_time if user_flashcard.last_time else None
        date_to_study = flashcard_priority.date_to_study if flashcard_priority.date_to_study else None

        if last_time and date_to_study and last_time > date_to_study:
            next_study_days = max(next_study_days, base_days)

        user_flashcard.next_time = timezone.now() + timezone.timedelta(
            days=next_study_days)

        user_flashcard.save()
        flashcard_priority.date_to_study = timezone.now(
        ) + timezone.timedelta(days=next_study_days)
        flashcard_priority.save()

        if user_flashcard.situation == "Reviewing":
            if total_exhibitions >= 10 or (total_exhibitions >= 7 and next_study_days >= max_days):
                user_flashcard.situation = "Finished"
                user_flashcard.save()

        return JsonResponse({
            'success': True,
            'message': 'Estado do flashcard e prioridade atualizados com sucesso.',
        }, status=status.HTTP_200_OK)

    except DeckFlashCard.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'DeckFlashCard não encontrado.'
        }, status=status.HTTP_404_NOT_FOUND)

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


@csrf_exempt
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

            # Obtendo a data atual
            now = timezone.now()

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
                'deckflashcard_set__userflashcards'
            ).filter(
                deckflashcard__userflashcards__situation='Learning',
                deckflashcard__userflashcards__next_time__lte=now
            ).order_by(
                'deckflashcard__userflashcards__next_time'
            )[:learning_per_day]

            flashcards_to_study['learning_flashcards'] = learning_flashcards

            # Flashcards "Reviewing" - Usando next_time da tabela UserFlashCard
            review_flashcards = FlashCard.objects.filter(
                id__in=deck_flashcard_ids
            ).prefetch_related(
                'deckflashcard_set__userflashcards'
            ).filter(
                deckflashcard__userflashcards__situation='Reviewing',
                deckflashcard__userflashcards__next_time__lte=now
            ).order_by(
                'deckflashcard__userflashcards__next_time'
            )[:reviewing_per_day]

            flashcards_to_study['review_flashcards'] = review_flashcards

            if len(flashcards_to_study['new_flashcards']) < new_per_day:
                # Buscando flashcards atrasados "New"
                additional_new_flashcards = FlashCard.objects.filter(
                    id__in=deck_flashcard_ids
                ).prefetch_related(
                    'deckflashcard_set__userflashcards'
                ).filter(
                    deckflashcard__userflashcards__situation='New',
                    deckflashcard__userflashcards__next_time__lt=now
                )[:new_per_day - len(flashcards_to_study['new_flashcards'])]
                flashcards_to_study['new_flashcards'] = list(
                    flashcards_to_study['new_flashcards']) + list(additional_new_flashcards)

            if len(flashcards_to_study['learning_flashcards']) < learning_per_day:
                # Buscando flashcards atrasados "Learning" (até 5 dias de atraso)
                additional_learning_flashcards = FlashCard.objects.filter(
                    id__in=deck_flashcard_ids
                ).prefetch_related(
                    'deckflashcard_set__userflashcards'
                ).filter(
                    deckflashcard__userflashcards__situation='Learning',
                    deckflashcard__userflashcards__next_time__lt=now,
                    deckflashcard__userflashcards__next_time__gte=now -
                    timedelta(days=5)
                )[:learning_per_day - len(flashcards_to_study['learning_flashcards'])]
                flashcards_to_study['learning_flashcards'] = list(
                    flashcards_to_study['learning_flashcards']) + list(additional_learning_flashcards)

            if len(flashcards_to_study['review_flashcards']) < reviewing_per_day:
                # Buscando flashcards atrasados "Reviewing" (até 3 dias de atraso)
                additional_review_flashcards = FlashCard.objects.filter(
                    id__in=deck_flashcard_ids
                ).prefetch_related(
                    'deckflashcard_set__userflashcards'
                ).filter(
                    deckflashcard__userflashcards__situation='Reviewing',
                    deckflashcard__userflashcards__next_time__lt=now,
                    deckflashcard__userflashcards__next_time__gte=now -
                    timedelta(days=3)
                )[:reviewing_per_day - len(flashcards_to_study['review_flashcards'])]
                flashcards_to_study['review_flashcards'] = list(
                    flashcards_to_study['review_flashcards']) + list(additional_review_flashcards)

            # Se ainda não tiver flashcards suficientes, buscamos os próximos dias
            if len(flashcards_to_study['learning_flashcards']) < learning_per_day:
                # Buscando flashcards para o próximo dia "Learning" (até 5 dias à frente)
                additional_learning_flashcards = FlashCard.objects.filter(
                    id__in=deck_flashcard_ids
                ).prefetch_related(
                    'deckflashcard_set__userflashcards'
                ).filter(
                    deckflashcard__userflashcards__situation='Learning',
                    deckflashcard__userflashcards__next_time__gte=now,
                    deckflashcard__userflashcards__next_time__lte=now +
                    timedelta(days=5)
                )[:learning_per_day - len(flashcards_to_study['learning_flashcards'])]
                flashcards_to_study['learning_flashcards'].extend(
                    additional_learning_flashcards)

            if len(flashcards_to_study['review_flashcards']) < reviewing_per_day:
                # Buscando flashcards para o próximo dia "Reviewing" (até 3 dias à frente)
                additional_review_flashcards = FlashCard.objects.filter(
                    id__in=deck_flashcard_ids
                ).prefetch_related(
                    'deckflashcard_set__userflashcards'
                ).filter(
                    deckflashcard__userflashcards__situation='Reviewing',
                    deckflashcard__userflashcards__next_time__gte=now,
                    deckflashcard__userflashcards__next_time__lte=now +
                    timedelta(days=3)
                )[:reviewing_per_day - len(flashcards_to_study['review_flashcards'])]
                flashcards_to_study['review_flashcards'].extend(
                    additional_review_flashcards)

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
                        } for pronunciation in pronunciations
                    ]

                    flashcard_data.update({
                        'examples': [example.example.text_example for example in examples],
                        'translations': [translation.translation.text_translation for translation in translations],
                        'pronunciations': pronunciation_data,
                        'images': [image.file_url for image in images]
                    })

                    response_data.append(flashcard_data)
            deck_name = Deck.objects.filter(id=deckId).first()
            return JsonResponse({
                'success': True,
                'message': ['Flashcards para estudo retornados.'],
                'deckName': deck_name.title,
                'flashcards': response_data,
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': ['Erro ao buscar flashcards para estudo: ' + str(e)],
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
